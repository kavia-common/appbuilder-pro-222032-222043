from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from src.routers.auth import UserPublic, get_current_user
from src.services.preview_service import preview_service
from src.services.project_files_service import project_files_service

router = APIRouter(
    prefix="/preview",
    tags=["preview"],
)


class PreviewIndexInfo(BaseModel):
    """Information about what entry file was served."""
    path: str = Field(..., description="Resolved entry file path")
    note: Optional[str] = Field(None, description="Note about fallback behavior")


def _guess_content_type(path: str) -> str:
    lower = path.lower()
    if lower.endswith(".html"):
        return "text/html; charset=utf-8"
    if lower.endswith(".js"):
        return "application/javascript"
    if lower.endswith(".ts"):
        return "application/typescript"
    if lower.endswith(".tsx"):
        return "text/plain"
    if lower.endswith(".css"):
        return "text/css"
    if lower.endswith(".json"):
        return "application/json"
    if lower.endswith(".svg"):
        return "image/svg+xml"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".woff2"):
        return "font/woff2"
    return "text/plain; charset=utf-8"


def _find_default_entry(owner: str, project_id: str) -> Optional[str]:
    # Prefer typical web entry files
    candidates = [
        "index.html",
        "public/index.html",
        "app/index.html",
        "src/index.html",
        "src/app/page.html",
    ]
    files = project_files_service.list_files(owner, project_id)
    paths = {f.path.lstrip("/") for f in files}
    for c in candidates:
        if c in paths:
            return c
    # Next.js style
    for c in ["src/app/page.tsx", "app/page.tsx", "pages/index.tsx", "pages/index.js"]:
        if c in paths:
            return c
    return None


# PUBLIC_INTERFACE
@router.get(
    "/{project_id}",
    summary="Serve preview entry",
    description="Serve the project's preview entry file (best-effort).",
)
async def get_preview_entry(
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
):
    """Serve index-like entry content for a project's preview."""
    entry = _find_default_entry(current_user.email, project_id)
    if not entry:
        # Fallback to a minimal HTML page that instructs the client to use assets
        html = """
<!doctype html>
<html>
<head><meta charset="utf-8"><title>Preview</title></head>
<body>
<h1>Preview</h1>
<p>No typical entry file found. Use /preview/{project_id}/file?path=... to fetch files.</p>
<script>
  // connect to reload socket if needed by the client
</script>
</body>
</html>
""".strip()
        return HTMLResponse(content=html, status_code=200)
    f = preview_service.read_file(current_user.email, project_id, entry)
    if not f:
        raise HTTPException(status_code=404, detail="Entry not found")
    return Response(content=f.content, media_type=_guess_content_type(f.path))


# PUBLIC_INTERFACE
@router.get(
    "/{project_id}/file",
    summary="Serve a specific project file for preview",
    description="Serve static content directly from project files by path.",
)
async def get_preview_file(
    project_id: str = Path(..., description="Project ID"),
    path: str = "",  # query param
    current_user: UserPublic = Depends(get_current_user),
):
    """Serve a single file by path from the project's current files."""
    if not path:
        raise HTTPException(status_code=400, detail="path query param is required")
    f = preview_service.read_file(current_user.email, project_id, path)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=f.content, media_type=_guess_content_type(f.path))


# PUBLIC_INTERFACE
@router.websocket(
    "/ws/preview/{project_id}"
)
async def ws_preview_reload(websocket: WebSocket, project_id: str = Path(...)) -> None:
    """WebSocket endpoint for preview reload events.

    Clients should include Authorization header 'Bearer token-<email>' to authenticate.
    The server will push JSON messages like: {"type":"reload","data":{"reason":"file_change"}}.
    """
    auth_header = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        await websocket.close(code=4401)
        return
    token = auth_header.split(" ", 1)[1].strip()
    if not token.startswith("token-"):
        await websocket.close(code=4401)
        return
    owner_email = token[len("token-"):].strip()
    await websocket.accept(subprotocol=None)
    await preview_service.register_ws(owner_email, project_id, websocket)
    try:
        # Keep the socket open; we don't expect client messages but we can read pings
        while True:
            # Wait for any data to keep connection alive; timeouts handled by client
            data = await websocket.receive_text()
            # Allow a ping message
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        # Silently close on error
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        await preview_service.unregister_ws(owner_email, project_id, websocket)
