from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Dict, Set, Optional

from fastapi import WebSocket

from src.services.project_files_service import project_files_service, FileRecord


@dataclass
class ProjectPreviewState:
    """Holds websocket connections for a project's live preview."""
    sockets: Set[WebSocket] = field(default_factory=set)


class PreviewService:
    """Serve static content from project files and broadcast reload over WebSocket."""

    def __init__(self) -> None:
        # key: (owner_email, project_id)
        self._states: Dict[tuple[str, str], ProjectPreviewState] = {}
        # throttle reloads using a debounce per project
        self._reload_locks: Dict[tuple[str, str], asyncio.Lock] = {}

    def _key(self, owner_email: str, project_id: str) -> tuple[str, str]:
        return (owner_email, project_id)

    def _get_state(self, owner_email: str, project_id: str) -> ProjectPreviewState:
        key = self._key(owner_email, project_id)
        if key not in self._states:
            self._states[key] = ProjectPreviewState()
        if key not in self._reload_locks:
            self._reload_locks[key] = asyncio.Lock()
        return self._states[key]

    # PUBLIC_INTERFACE
    def read_file(self, owner_email: str, project_id: str, path: str) -> Optional[FileRecord]:
        """Return a file by 'web path' for preview (leading slash optional)."""
        normalized = path.lstrip("/")
        files = project_files_service.list_files(owner_email, project_id)
        for f in files:
            if f.path.lstrip("/") == normalized:
                return f
        return None

    # PUBLIC_INTERFACE
    async def register_ws(self, owner_email: str, project_id: str, ws: WebSocket) -> None:
        """Register a websocket connection for a project's preview reload channel."""
        state = self._get_state(owner_email, project_id)
        state.sockets.add(ws)

    # PUBLIC_INTERFACE
    async def unregister_ws(self, owner_email: str, project_id: str, ws: WebSocket) -> None:
        """Unregister a websocket connection."""
        key = self._key(owner_email, project_id)
        state = self._states.get(key)
        if not state:
            return
        if ws in state.sockets:
            try:
                state.sockets.remove(ws)
            except KeyError:
                pass

    # PUBLIC_INTERFACE
    async def broadcast_reload(self, owner_email: str, project_id: str, reason: str = "file_change") -> None:
        """Broadcast a reload event to all connected preview clients."""
        key = self._key(owner_email, project_id)
        state = self._states.get(key)
        if not state or not state.sockets:
            return
        # Debounce to avoid floods during quick successive edits
        lock = self._reload_locks[key]
        if lock.locked():
            return
        async with lock:
            message = json.dumps({"type": "reload", "data": {"reason": reason}})
            to_remove: Set[WebSocket] = set()
            for ws in list(state.sockets):
                try:
                    await ws.send_text(message)
                except Exception:
                    to_remove.add(ws)
            for ws in to_remove:
                try:
                    state.sockets.remove(ws)
                except Exception:
                    pass


# Singleton preview service
preview_service = PreviewService()
