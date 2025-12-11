from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional


@dataclass
class GenerationEvent:
    """Represents a generation stream event."""

    type: str
    data: dict


@dataclass
class _TaskState:
    """Internal state for a mock generation task."""
    task_id: str
    owner: str  # owner email for auth scoping
    project_id: Optional[str] = None
    chat_session_id: Optional[str] = None
    prompt: str = ""
    done: bool = False
    error: Optional[str] = None
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class GenerationService:
    """Mock generation service that simulates AI streaming tokens and file diffs.

    For production, replace the simulate_* methods with real model/tooling calls.
    """

    def __init__(self) -> None:
        # Map task_id -> _TaskState
        self._tasks: Dict[str, _TaskState] = {}

    # PUBLIC_INTERFACE
    def create_task(
        self, owner: str, prompt: str, project_id: Optional[str], chat_session_id: Optional[str]
    ) -> str:
        """Create a new generation task and return its ID."""
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = _TaskState(
            task_id=task_id,
            owner=owner,
            prompt=prompt,
            project_id=project_id,
            chat_session_id=chat_session_id,
        )
        return task_id

    # PUBLIC_INTERFACE
    def get_task_owner(self, task_id: str) -> Optional[str]:
        """Return the owner email for a task."""
        state = self._tasks.get(task_id)
        return state.owner if state else None

    # PUBLIC_INTERFACE
    async def run_task(self, task_id: str) -> None:
        """Run the mock generation task, emitting events into the queue."""
        state = self._tasks.get(task_id)
        if not state:
            return
        try:
            # Emit start event
            await state.queue.put(
                GenerationEvent(type="status", data={"phase": "started", "task_id": task_id})
            )

            # Token streaming simulation
            tokens = self._tokenize_prompt(state.prompt)
            for i, tok in enumerate(tokens, start=1):
                await asyncio.sleep(0.1)
                await state.queue.put(
                    GenerationEvent(
                        type="token",
                        data={"index": i, "token": tok, "task_id": task_id},
                    )
                )

            # Simulate file diffs
            for idx, diff in enumerate(self._mock_diffs(state.prompt), start=1):
                await asyncio.sleep(0.15)
                await state.queue.put(
                    GenerationEvent(
                        type="file_diff",
                        data={"index": idx, "diff": diff, "task_id": task_id},
                    )
                )

            # Complete
            await asyncio.sleep(0.1)
            await state.queue.put(
                GenerationEvent(
                    type="status",
                    data={"phase": "completed", "task_id": task_id},
                )
            )
            state.done = True
        except Exception as e:
            state.error = str(e)
            await state.queue.put(
                GenerationEvent(
                    type="error",
                    data={"message": state.error, "task_id": task_id},
                )
            )
            state.done = True
        finally:
            # Ensure the stream can terminate
            await state.queue.put(GenerationEvent(type="end", data={"task_id": task_id}))

    # PUBLIC_INTERFACE
    async def stream_events(self, task_id: str) -> AsyncIterator[str]:
        """Yield JSON lines for events of a task."""
        state = self._tasks.get(task_id)
        if not state:
            yield json.dumps({"type": "error", "data": {"message": "unknown task"}})
            return
        # Drain until end
        while True:
            event: GenerationEvent = await state.queue.get()
            yield json.dumps({"type": event.type, "data": event.data})
            if event.type == "end":
                break

    def _tokenize_prompt(self, prompt: str) -> List[str]:
        # Very naive tokenizer for demo
        if not prompt:
            return ["[no]", "prompt", "provided"]
        # split and keep small tokens
        return prompt.strip().split()

    def _mock_diffs(self, prompt: str) -> List[dict]:
        # Produce a couple of mock diffs related to the prompt
        safe_prompt = (prompt[:20] + "...") if len(prompt) > 20 else prompt
        return [
            {
                "path": "README.md",
                "change_type": "modify",
                "patch": f"+ Added section for: {safe_prompt}",
            },
            {
                "path": "src/app/page.tsx",
                "change_type": "add",
                "patch": f"+ Page created for: {safe_prompt}",
            },
        ]


# Singleton service for app-wide usage
generation_service = GenerationService()
