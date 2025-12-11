from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from pydantic import BaseModel, Field

from src.routers.auth import UserPublic, get_current_user
from src.services.project_files_service import FileRecord, VersionRecord, project_files_service

router = APIRouter(
    prefix="/projects/{project_id}/files",
    tags=["project-files"],
)


class ProjectFileBase(BaseModel):
    """Common file fields."""
    path: str = Field(..., description="File path within the project (e.g., src/app/page.tsx)")
    content: str = Field(..., description="File contents as text")
    is_binary: bool = Field(False, description="Whether the file content is binary")


class ProjectFileCreate(ProjectFileBase):
    """Payload for creating/upserting a file."""
    pass


class ProjectFileUpdate(BaseModel):
    """Payload for updating a file (partial)."""
    path: Optional[str] = Field(None, description="New file path")
    content: Optional[str] = Field(None, description="New file content")
    is_binary: Optional[bool] = Field(None, description="New binary flag")


class ProjectFileOut(BaseModel):
    """File resource returned by API."""
    id: str = Field(..., description="File ID")
    path: str = Field(..., description="Path")
    content: str = Field(..., description="Content")
    is_binary: bool = Field(False, description="Binary flag")


def _to_out(rec: FileRecord) -> ProjectFileOut:
    return ProjectFileOut(id=rec.id, path=rec.path, content=rec.content, is_binary=rec.is_binary)


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[ProjectFileOut],
    summary="List project files",
    description="List all current files for a project.",
)
async def list_project_files(
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> List[ProjectFileOut]:
    """Return all current files for the project."""
    files = project_files_service.list_files(current_user.email, project_id)
    return [_to_out(f) for f in files]


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=ProjectFileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update file by path",
    description="Create a new file or update existing file with the same path.",
)
async def create_or_update_file(
    payload: ProjectFileCreate,
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> ProjectFileOut:
    """Create or update a file by its path."""
    rec = project_files_service.upsert_file_by_path(
        current_user.email, project_id, payload.path, payload.content, payload.is_binary
    )
    return _to_out(rec)


# PUBLIC_INTERFACE
@router.get(
    "/{file_id}",
    response_model=ProjectFileOut,
    summary="Get file",
    description="Get a single file by ID.",
)
async def get_file(
    file_id: str = Path(..., description="File ID"),
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> ProjectFileOut:
    """Retrieve a single file by ID."""
    rec = project_files_service.get_file(current_user.email, project_id, file_id)
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    return _to_out(rec)


# PUBLIC_INTERFACE
@router.patch(
    "/{file_id}",
    response_model=ProjectFileOut,
    summary="Update file",
    description="Update file attributes by ID.",
)
async def update_file(
    payload: ProjectFileUpdate,
    file_id: str = Path(..., description="File ID"),
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> ProjectFileOut:
    """Update file attributes."""
    try:
        rec = project_files_service.update_file(
            current_user.email,
            project_id,
            file_id,
            path=payload.path,
            content=payload.content,
            is_binary=payload.is_binary,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    return _to_out(rec)


# PUBLIC_INTERFACE
@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete file",
    description="Delete a file by ID.",
)
async def delete_file(
    file_id: str = Path(..., description="File ID"),
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> None:
    """Delete a file."""
    ok = project_files_service.delete_file(current_user.email, project_id, file_id)
    if not ok:
        raise HTTPException(status_code=404, detail="File not found")
    return None


# Versions subrouter
versions_router = APIRouter(
    prefix="/projects/{project_id}/versions",
    tags=["project-versions"],
)


class VersionCreate(BaseModel):
    """Payload to create a snapshot version."""
    description: Optional[str] = Field(None, description="Description for the snapshot")


class VersionOut(BaseModel):
    """Version resource."""
    id: str = Field(..., description="Version ID")
    version_number: int = Field(..., description="Version number")
    description: Optional[str] = Field(None, description="Description")


def _to_version_out(v: VersionRecord) -> VersionOut:
    return VersionOut(id=v.id, version_number=v.version_number, description=v.description)


# PUBLIC_INTERFACE
@versions_router.post(
    "",
    response_model=VersionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create version snapshot",
    description="Snapshot current project files into a new version.",
)
async def create_version(
    payload: VersionCreate,
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> VersionOut:
    """Create a snapshot version of current files."""
    v = project_files_service.snapshot_version(current_user.email, project_id, payload.description)
    return _to_version_out(v)


# PUBLIC_INTERFACE
@versions_router.get(
    "",
    response_model=List[VersionOut],
    summary="List versions",
    description="List all versions for a project (newest first).",
)
async def list_versions(
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> List[VersionOut]:
    """List versions for the project."""
    versions = project_files_service.list_versions(current_user.email, project_id)
    return [_to_version_out(v) for v in versions]


# PUBLIC_INTERFACE
@versions_router.post(
    "/{version_number}/restore",
    response_model=List[ProjectFileOut],
    summary="Restore a version",
    description="Restore project files from a specific version number.",
)
async def restore_version(
    version_number: int = Path(..., description="Version number to restore"),
    project_id: str = Path(..., description="Project ID"),
    current_user: UserPublic = Depends(get_current_user),
) -> List[ProjectFileOut]:
    """Restore project files from a version snapshot."""
    try:
        files, _ = project_files_service.restore_version(current_user.email, project_id, version_number)
    except ValueError:
        raise HTTPException(status_code=404, detail="Version not found")
    return [_to_out(f) for f in files]


# Export subrouter
export_router = APIRouter(
    prefix="/projects/{project_id}/export",
    tags=["export"],
)


# PUBLIC_INTERFACE
@export_router.get(
    "",
    summary="Export project as ZIP",
    description="Stream a ZIP archive containing current project files.",
    responses={
        200: {
            "content": {"application/zip": {}},
            "description": "ZIP stream of project files",
        }
    },
)
async def export_project_zip(
    project_id: str = Path(..., description="Project ID"),
    download: Optional[bool] = Query(default=True, description="Whether to prompt download via Content-Disposition"),
    current_user: UserPublic = Depends(get_current_user),
):
    """Stream a ZIP archive of current project files."""
    data = project_files_service.export_zip_bytes(current_user.email, project_id)
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="project-{project_id}.zip"'
    return Response(content=data, media_type="application/zip", headers=headers)
