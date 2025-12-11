from __future__ import annotations

from typing import Literal, List

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from src.routers.auth import UserPublic, get_current_user
from src.services.deploy_service import deploy_service, DeploymentRecord

router = APIRouter(
    prefix="/projects/{project_id}/deploy",
    tags=["deploy"],
)


class DeployStartRequest(BaseModel):
    """Start deployment request."""
    provider: Literal["vercel", "heroku", "fly", "railway", "none"] = Field(..., description="Deployment provider")


class DeployStartResponse(BaseModel):
    """Deployment created response."""
    deploy_id: str = Field(..., description="Deployment ID")


class DeployStatus(BaseModel):
    """Deployment status."""
    id: str = Field(..., description="Deployment ID")
    provider: str = Field(..., description="Provider")
    status: str = Field(..., description="Status")
    url: str | None = Field(None, description="Deployment URL")
    logs: List[str] = Field(default_factory=list, description="Logs")


def _to_status(rec: DeploymentRecord) -> DeployStatus:
    return DeployStatus(id=rec.id, provider=rec.provider, status=rec.status, url=rec.url, logs=list(rec.logs))


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=DeployStartResponse,
    summary="Start a deployment",
    description="Create a deployment record and simulate provider pipeline.",
)
async def start_deploy(
    payload: DeployStartRequest,
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> DeployStartResponse:
    """Start a provider deployment for a project."""
    did = deploy_service.start(current_user.email, project_id, payload.provider)  # type: ignore[arg-type]
    return DeployStartResponse(deploy_id=did)


# PUBLIC_INTERFACE
@router.get(
    "/{deploy_id}",
    response_model=DeployStatus,
    summary="Get deployment status",
    description="Return status for a specific deployment.",
)
async def get_deploy(
    deploy_id: str = Path(..., description="Deployment ID"),
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> DeployStatus:
    """Get status for a deployment."""
    rec = deploy_service.get(deploy_id)
    if not rec or rec.project_id != project_id or rec.owner != current_user.email:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return _to_status(rec)


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[DeployStatus],
    summary="List deployments for project",
    description="List all deployment records for a project.",
)
async def list_deploys(
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> List[DeployStatus]:
    """List deployments for a project."""
    items = deploy_service.list_for_project(current_user.email, project_id)
    return [_to_status(i) for i in items]
