from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from src.routers.auth import UserPublic, get_current_user

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

# In-memory stores keyed by owner email
_SESSIONS: Dict[str, Dict[str, "ChatSession"]] = {}
_MESSAGES: Dict[str, List["ChatMessage"]] = {}  # key: session_id


class ChatSessionCreate(BaseModel):
    """Create chat session payload."""
    title: Optional[str] = Field(None, description="Optional session title")
    project_id: Optional[str] = Field(None, description="Associated project id")


class ChatSession(BaseModel):
    """Chat session resource."""
    id: str = Field(..., description="Session ID")
    title: Optional[str] = Field(None, description="Session title")
    project_id: Optional[str] = Field(None, description="Associated project id")
    status: str = Field("active", description="Session status")


class ChatMessageCreate(BaseModel):
    """Create chat message payload."""
    role: str = Field(..., description="Role: user|assistant|system")
    content: str = Field(..., description="Message content")


class ChatMessage(BaseModel):
    """Chat message resource."""
    id: str = Field(..., description="Message ID")
    chat_session_id: str = Field(..., description="Session ID")
    role: str = Field(..., description="Role")
    content: str = Field(..., description="Content")


def _get_sessions(email: str) -> Dict[str, ChatSession]:
    if email not in _SESSIONS:
        _SESSIONS[email] = {}
    return _SESSIONS[email]


def _get_session_or_404(email: str, session_id: str) -> ChatSession:
    sess = _get_sessions(email).get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return sess


def _get_messages(session_id: str) -> List[ChatMessage]:
    if session_id not in _MESSAGES:
        _MESSAGES[session_id] = []
    return _MESSAGES[session_id]


# PUBLIC_INTERFACE
@router.get(
    "/sessions",
    response_model=List[ChatSession],
    summary="List chat sessions",
    description="List chat sessions for current user.",
)
async def list_sessions(current_user: UserPublic = Depends(get_current_user)) -> List[ChatSession]:
    """Return all chat sessions for the authenticated user."""
    return list(_get_sessions(current_user.email).values())


# PUBLIC_INTERFACE
@router.post(
    "/sessions",
    response_model=ChatSession,
    status_code=status.HTTP_201_CREATED,
    summary="Create chat session",
    description="Create a new chat session linked optionally to a project.",
)
async def create_session(
    payload: ChatSessionCreate,
    current_user: UserPublic = Depends(get_current_user),
) -> ChatSession:
    """Create a chat session."""
    sid = str(uuid.uuid4())
    session = ChatSession(
        id=sid,
        title=payload.title,
        project_id=payload.project_id,
        status="active",
    )
    _get_sessions(current_user.email)[sid] = session
    return session


# PUBLIC_INTERFACE
@router.get(
    "/sessions/{session_id}",
    response_model=ChatSession,
    summary="Get chat session",
    description="Get chat session by ID.",
)
async def get_session(
    session_id: str = Path(..., description="Chat session ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> ChatSession:
    """Retrieve a single chat session."""
    return _get_session_or_404(current_user.email, session_id)


# PUBLIC_INTERFACE
@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete chat session",
    description="Delete chat session by ID.",
)
async def delete_session(
    session_id: str = Path(..., description="Chat session ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> None:
    """Delete a chat session and its messages."""
    _get_session_or_404(current_user.email, session_id)
    _SESSIONS[current_user.email].pop(session_id, None)
    _MESSAGES.pop(session_id, None)
    return None


# PUBLIC_INTERFACE
@router.get(
    "/sessions/{session_id}/messages",
    response_model=List[ChatMessage],
    summary="List messages",
    description="List messages for a chat session.",
)
async def list_messages(
    session_id: str = Path(..., description="Chat session ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> List[ChatMessage]:
    """List messages for a session."""
    _get_session_or_404(current_user.email, session_id)
    return _get_messages(session_id)


# PUBLIC_INTERFACE
@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessage,
    status_code=status.HTTP_201_CREATED,
    summary="Create message",
    description="Create a message in a chat session.",
)
async def create_message(
    session_id: str = Path(..., description="Chat session ID"),
    payload: ChatMessageCreate = ...,
    current_user: UserPublic = Depends(get_current_user),
) -> ChatMessage:
    """Create a chat message in the session."""
    _get_session_or_404(current_user.email, session_id)
    mid = str(uuid.uuid4())
    msg = ChatMessage(id=mid, chat_session_id=session_id, role=payload.role, content=payload.content)
    _get_messages(session_id).append(msg)
    return msg
