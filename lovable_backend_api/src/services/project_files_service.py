from __future__ import annotations

import io
import uuid
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class FileRecord:
    """In-memory representation of a project file."""
    id: str
    path: str
    content: str
    is_binary: bool = False


@dataclass
class VersionRecord:
    """Snapshot of a project's files."""
    id: str
    version_number: int
    description: Optional[str]
    files: List[FileRecord]  # Deep-copied list at snapshot time


@dataclass
class ProjectState:
    """All state for a single project (for a given owner)."""
    files: Dict[str, FileRecord] = field(default_factory=dict)  # key: file_id
    files_by_path: Dict[str, str] = field(default_factory=dict)  # path -> file_id
    versions: List[VersionRecord] = field(default_factory=list)


class ProjectFilesService:
    """In-memory service for managing project files, versions, and export.

    NOTE: This is an in-memory placeholder. Replace with database-backed
    implementations using SQLAlchemy models in production.
    """

    def __init__(self) -> None:
        # owner -> project_id -> ProjectState
        self._data: Dict[str, Dict[str, ProjectState]] = {}

    def _get_state(self, owner_email: str, project_id: str) -> ProjectState:
        if owner_email not in self._data:
            self._data[owner_email] = {}
        if project_id not in self._data[owner_email]:
            self._data[owner_email][project_id] = ProjectState()
        return self._data[owner_email][project_id]

    # PUBLIC_INTERFACE
    def list_files(self, owner_email: str, project_id: str) -> List[FileRecord]:
        """List all current files for a project."""
        state = self._get_state(owner_email, project_id)
        return list(state.files.values())

    # PUBLIC_INTERFACE
    def get_file(self, owner_email: str, project_id: str, file_id: str) -> Optional[FileRecord]:
        """Get a single file by id."""
        state = self._get_state(owner_email, project_id)
        return state.files.get(file_id)

    # PUBLIC_INTERFACE
    def upsert_file_by_path(
        self, owner_email: str, project_id: str, path: str, content: str, is_binary: bool = False
    ) -> FileRecord:
        """Create or update a file by its path."""
        state = self._get_state(owner_email, project_id)
        if path in state.files_by_path:
            fid = state.files_by_path[path]
            rec = state.files[fid]
            rec.content = content
            rec.is_binary = is_binary
            return rec
        fid = str(uuid.uuid4())
        rec = FileRecord(id=fid, path=path, content=content, is_binary=is_binary)
        state.files[fid] = rec
        state.files_by_path[path] = fid
        return rec

    # PUBLIC_INTERFACE
    def update_file(
        self, owner_email: str, project_id: str, file_id: str, *, path: Optional[str], content: Optional[str], is_binary: Optional[bool]
    ) -> Optional[FileRecord]:
        """Update a file's attributes (partial)."""
        state = self._get_state(owner_email, project_id)
        rec = state.files.get(file_id)
        if not rec:
            return None
        if path is not None and path != rec.path:
            # maintain path index
            if path in state.files_by_path and state.files_by_path[path] != file_id:
                # conflict
                raise ValueError("Path already exists")
            # remove old path mapping
            state.files_by_path.pop(rec.path, None)
            rec.path = path
            state.files_by_path[path] = file_id
        if content is not None:
            rec.content = content
        if is_binary is not None:
            rec.is_binary = is_binary
        return rec

    # PUBLIC_INTERFACE
    def delete_file(self, owner_email: str, project_id: str, file_id: str) -> bool:
        """Delete a file by id."""
        state = self._get_state(owner_email, project_id)
        rec = state.files.pop(file_id, None)
        if not rec:
            return False
        state.files_by_path.pop(rec.path, None)
        return True

    # PUBLIC_INTERFACE
    def snapshot_version(
        self, owner_email: str, project_id: str, description: Optional[str]
    ) -> VersionRecord:
        """Create a snapshot version of all current project files."""
        state = self._get_state(owner_email, project_id)
        next_version = len(state.versions) + 1
        # Deep copy files (by value)
        copied_files = [
            FileRecord(id=f.id, path=f.path, content=f.content, is_binary=f.is_binary)
            for f in state.files.values()
        ]
        ver = VersionRecord(
            id=str(uuid.uuid4()),
            version_number=next_version,
            description=description,
            files=copied_files,
        )
        state.versions.append(ver)
        return ver

    # PUBLIC_INTERFACE
    def list_versions(self, owner_email: str, project_id: str) -> List[VersionRecord]:
        """List versions for a project."""
        state = self._get_state(owner_email, project_id)
        # return newest first
        return list(sorted(state.versions, key=lambda v: v.version_number, reverse=True))

    # PUBLIC_INTERFACE
    def get_version(self, owner_email: str, project_id: str, version_number: int) -> Optional[VersionRecord]:
        """Get a single version by version number."""
        state = self._get_state(owner_email, project_id)
        for v in state.versions:
            if v.version_number == version_number:
                return v
        return None

    # PUBLIC_INTERFACE
    def restore_version(self, owner_email: str, project_id: str, version_number: int) -> Tuple[List[FileRecord], VersionRecord]:
        """Restore the project files from a specific version snapshot.

        Returns the new set of files after restore and the version used.
        """
        state = self._get_state(owner_email, project_id)
        ver = self.get_version(owner_email, project_id, version_number)
        if not ver:
            raise ValueError("Version not found")
        # Reset current files to version's snapshot
        state.files.clear()
        state.files_by_path.clear()
        for f in ver.files:
            # new ids for current files
            new_id = str(uuid.uuid4())
            rec = FileRecord(id=new_id, path=f.path, content=f.content, is_binary=f.is_binary)
            state.files[new_id] = rec
            state.files_by_path[rec.path] = new_id
        return list(state.files.values()), ver

    # PUBLIC_INTERFACE
    def export_zip_bytes(self, owner_email: str, project_id: str) -> bytes:
        """Create a ZIP archive of the current project's files and return bytes."""
        state = self._get_state(owner_email, project_id)
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in state.files.values():
                # Normalize path inside zip
                arcname = f.path.lstrip("/").replace("\\", "/")
                zf.writestr(arcname, f.content if not f.is_binary else f.content)
        mem.seek(0)
        return mem.read()


# Singleton instance
project_files_service = ProjectFilesService()
