from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional, Literal, List

Provider = Literal["vercel", "heroku", "fly", "railway", "none"]
Status = Literal["pending", "building", "success", "failed"]


@dataclass
class DeploymentRecord:
    """In-memory deployment record."""
    id: str
    owner: str
    project_id: str
    provider: Provider
    status: Status = "pending"
    url: Optional[str] = None
    logs: List[str] = field(default_factory=list)


class DeployService:
    """Simple in-memory deployment stubs for providers."""

    def __init__(self) -> None:
        # key: deploy_id
        self._deployments: Dict[str, DeploymentRecord] = {}
        # index by (owner, project_id)
        self._by_project: Dict[tuple[str, str], List[str]] = {}

    # PUBLIC_INTERFACE
    def start(self, owner: str, project_id: str, provider: Provider) -> str:
        """Create a deployment record and simulate a deploy pipeline."""
        did = str(uuid.uuid4())
        rec = DeploymentRecord(id=did, owner=owner, project_id=project_id, provider=provider)
        self._deployments[did] = rec
        key = (owner, project_id)
        if key not in self._by_project:
            self._by_project[key] = []
        self._by_project[key].append(did)
        # run background simulation
        asyncio.create_task(self._simulate(rec))
        return did

    # PUBLIC_INTERFACE
    def get(self, deploy_id: str) -> Optional[DeploymentRecord]:
        """Get a single deployment by id."""
        return self._deployments.get(deploy_id)

    # PUBLIC_INTERFACE
    def list_for_project(self, owner: str, project_id: str) -> List[DeploymentRecord]:
        """List deployments for a project."""
        ids = self._by_project.get((owner, project_id), [])
        return [self._deployments[i] for i in ids if i in self._deployments]

    async def _simulate(self, rec: DeploymentRecord) -> None:
        """Simulate a small deploy pipeline with status changes."""
        phases = [
            ("building", "Packaging project..."),
            ("building", f"Pushing to {rec.provider}..."),
        ]
        for status, log in phases:
            rec.status = status  # type: ignore[assignment]
            rec.logs.append(log)
            await asyncio.sleep(0.5)
        # finish
        # Construct a fake URL
        host = {
            "vercel": "vercel.app",
            "heroku": "herokuapp.com",
            "fly": "fly.dev",
            "railway": "railway.app",
            "none": "local.dev",
        }.get(rec.provider, "example.com")
        rec.url = f"https://{rec.project_id[:8]}.{host}"
        rec.status = "success"
        rec.logs.append(f"Deployed at {rec.url}")
        await asyncio.sleep(0)
        

# singleton
deploy_service = DeployService()
