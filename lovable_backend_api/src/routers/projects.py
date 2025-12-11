from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field

from src.routers.auth import UserPublic, get_current_user

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
)

# In-memory store keyed by owner email to a dict of project_id -> project
# This is a placeholder until DB wiring is added.
_PROJECTS: Dict[str, Dict[str, "Project"]] = {}


class ProjectBase(BaseModel):
    """Shared fields for project payloads."""
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")


class ProjectCreate(ProjectBase):
    """Payload for creating a project."""
    pass


class ProjectUpdate(BaseModel):
    """Payload for updating a project (partial)."""
    name: Optional[str] = Field(None, description="New project name")
    description: Optional[str] = Field(None, description="New project description")


class Project(ProjectBase):
    """Project resource returned by API."""
    id: str = Field(..., description="Project ID")
    owner_email: str = Field(..., description="Owner email")


def _get_user_projects(email: str) -> Dict[str, Project]:
    """Get or initialize the per-user project dict."""
    if email not in _PROJECTS:
        _PROJECTS[email] = {}
    return _PROJECTS[email]


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[Project],
    summary="List projects",
    description="List all projects for the current user.",
)
async def list_projects(
    current_user: UserPublic = Depends(get_current_user),
    q: Optional[str] = Query(default=None, description="Optional search in project name"),
) -> List[Project]:
    """Return all projects owned by the current user, optionally filtered by a query."""
    projects = list(_get_user_projects(current_user.email).values())
    if q:
        q_lower = q.lower()
        projects = [p for p in projects if q_lower in p.name.lower()]
    return projects


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=Project,
    status_code=status.HTTP_201_CREATED,
    summary="Create project",
    description="Create a new project for the current user.",
)
async def create_project(
    payload: ProjectCreate,
    current_user: UserPublic = Depends(get_current_user),
) -> Project:
    """Create a new project and return it."""
    pid = str(uuid.uuid4())
    project = Project(
        id=pid,
        name=payload.name,
        description=payload.description,
        owner_email=current_user.email,
    )
    store = _get_user_projects(current_user.email)
    store[pid] = project
    return project


# PUBLIC_INTERFACE
@router.get(
    "/{project_id}",
    response_model=Project,
    summary="Get project",
    description="Get a project by ID for the current user.",
)
async def get_project(
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> Project:
    """Retrieve a single project."""
    store = _get_user_projects(current_user.email)
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# PUBLIC_INTERFACE
@router.patch(
    "/{project_id}",
    response_model=Project,
    summary="Update project",
    description="Update an existing project for the current user.",
)
async def update_project(
    project_id: str = Path(..., description="Project ID"),
    payload: ProjectUpdate = ...,
    current_user: UserPublic = Depends(get_current_user),
) -> Project:
    """Update a project's details."""
    store = _get_user_projects(current_user.email)
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    update = project.model_copy(update=payload.model_dump(exclude_unset=True))
    store[project_id] = update
    return update


# PUBLIC_INTERFACE
@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Delete a project by ID for the current user.",
)
async def delete_project(
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> None:
    """Delete a project."""
    store = _get_user_projects(current_user.email)
    if project_id not in store:
        raise HTTPException(status_code=404, detail="Project not found")
    del store[project_id]
    return None
