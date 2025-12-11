from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, Header, Path, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from src.routers.auth import UserPublic, get_current_user
from src.services.generation_service import generation_service

router = APIRouter(
    tags=["generation"],
)


class GenerateRequest(BaseModel):
    """Payload to start a generation task."""
    prompt: str = Field(..., description="Natural language requirement or change request")
    project_id: Optional[str] = Field(None, description="Target project ID")
    chat_session_id: Optional[str] = Field(None, description="Associated chat session ID")


class GenerateResponse(BaseModel):
    """Response acknowledging creation of a generation task."""
    task_id: str = Field(..., description="ID of the generation task; connect to WS to stream events")
    websocket_url: str = Field(..., description="WebSocket URL to stream generation events")


# PUBLIC_INTERFACE
@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Start generation",
    description="Start a mock generation task and receive a task_id. Connect to WS /ws/generate/{task_id} to stream events.",
    responses={
        201: {"description": "Task created"},
        401: {"description": "Unauthorized"},
    },
)
async def start_generation(
    payload: GenerateRequest,
    current_user: UserPublic = Depends(get_current_user),
    x_forwarded_proto: Optional[str] = Header(default=None),
    x_forwarded_host: Optional[str] = Header(default=None),
) -> GenerateResponse:
    """Start a generation job and return the task id and websocket URL."""
    task_id = generation_service.create_task(
        owner=current_user.email,
        prompt=payload.prompt,
        project_id=payload.project_id,
        chat_session_id=payload.chat_session_id,
    )
    # Fire and forget: run the task in background
    asyncio.create_task(generation_service.run_task(task_id))

    # Construct WS URL; prefer forwarded headers if behind proxy
    scheme = (x_forwarded_proto or "http").replace("https", "wss").replace("http", "ws")
    host = x_forwarded_host or "localhost"
    ws_url = f"{scheme}://{host}/ws/generate/{task_id}"

    return GenerateResponse(task_id=task_id, websocket_url=ws_url)


# PUBLIC_INTERFACE
@router.websocket(
    "/ws/generate/{task_id}"
)
async def ws_stream_generation(websocket: WebSocket, task_id: str = Path(...)) -> None:
    """WebSocket stream for generation events.

    Clients must provide an Authorization header as a query header via WebSocket subprotocol:
    - Send 'Authorization: Bearer token-<email>' in headers when connecting.

    The endpoint streams JSON lines, each with {type, data}.
    """
    # Validate Authorization header for WS (no dependency support on WebSocket)
    auth_header = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        await websocket.close(code=4401)  # unauthorized
        return
    token = auth_header.split(" ", 1)[1].strip()
    # Token format from dummy auth: token-<email>
    if not token.startswith("token-"):
        await websocket.close(code=4401)
        return
    email = token[len("token-") :].strip()
    # Ensure task belongs to this email
    owner = generation_service.get_task_owner(task_id)
    if not owner or owner != email:
        await websocket.close(code=4403)  # forbidden
        return

    await websocket.accept(subprotocol=None)
    try:
        async for line in generation_service.stream_events(task_id):
            await websocket.send_text(line)
    except WebSocketDisconnect:
        # Client disconnected; nothing else to do
        return
    except Exception as e:
        await websocket.send_json({"type": "error", "data": {"message": str(e)}})
        try:
            await websocket.close()
        except Exception:
            pass
