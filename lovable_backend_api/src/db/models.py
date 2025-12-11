"""SQLAlchemy ORM models for the Lovable backend.

This module defines the database schema using SQLAlchemy 2.x Declarative ORM.
It includes core entities and their relationships:

- User
- Project
- Template
- ChatSession
- ChatMessage
- ProjectVersion
- ProjectFile
- Deployment
- PreviewSession
- AuditEvent

Conventions:
- UUID primary keys stored as PostgreSQL UUID if available; else CHAR(36).
- Timestamps are timezone-aware UTC where supported (server_default=now()).
- Soft delete flags are not included at this time.
- Text/json fields use appropriate SQLAlchemy types; for JSON, use JSONB on Postgres when available.

Note:
- This file only defines schema; migrations should be handled via Alembic.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.types import JSON


# Detect PostgreSQL dialect capabilities at runtime via dialect name checks
def _uuid_pk() -> mapped_column:
    """Return a dialect-appropriate UUID primary key column."""
    try:
        return mapped_column(
            PG_UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    except Exception:
        # Fallback for non-Postgres dialects (e.g., SQLite)
        return mapped_column(
            String(36),
            primary_key=True,
            default=lambda: str(uuid.uuid4()),
        )


def _json_type():
    """Return JSONB for Postgres, else generic JSON."""
    # We cannot access engine here; use a dialect-agnostic column type and let
    # Postgres map JSON to JSONB explicitly where desired. For indices, we can
    # add functional indexes in migrations. Default to JSON for compatibility.
    return JSON


class Base(DeclarativeBase):
    """Base declarative class with common helpers."""
    pass


# USERS
class User(Base):
    """Application user with auth identity and profile info."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    projects: Mapped[List["Project"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    chat_sessions: Mapped[List["ChatSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_events: Mapped[List["AuditEvent"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
    )


# TEMPLATES
class Template(Base):
    """Library of reusable templates/components for generation."""
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(200), index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(_json_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    projects: Mapped[List["Project"]] = relationship(back_populates="template")

    __table_args__ = (
        Index("ix_templates_slug", "slug", unique=True),
    )


# PROJECTS
class Project(Base):
    """A generated project owned by a user."""
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = _uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    settings: Mapped[Optional[dict]] = mapped_column(_json_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="projects")
    template: Mapped[Optional["Template"]] = relationship(back_populates="projects")
    versions: Mapped[List["ProjectVersion"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    files: Mapped[List["ProjectFile"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    deployments: Mapped[List["Deployment"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    preview_sessions: Mapped[List["PreviewSession"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_projects_slug", "slug", unique=True),
        Index("ix_projects_owner_id", "owner_id"),
    )


# CHAT
class ChatSession(Base):
    """A chat session for gathering requirements and generation context."""
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="chat_sessions")
    project: Mapped[Optional["Project"]] = relationship(back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship(
        back_populates="chat_session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_chat_sessions_user_id", "user_id"),
        Index("ix_chat_sessions_project_id", "project_id"),
        Index("ix_chat_sessions_status", "status"),
    )


class ChatMessage(Base):
    """Messages within a chat session."""
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = _uuid_pk()
    chat_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), index=True)  # 'user' | 'assistant' | 'system'
    content: Mapped[str] = mapped_column(Text)
    tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(_json_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    chat_session: Mapped["ChatSession"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_chat_session_id", "chat_session_id"),
        Index("ix_chat_messages_role", "role"),
    )


# VERSIONS AND FILES
class ProjectVersion(Base):
    """Immutable version snapshots of a project."""
    __tablename__ = "project_versions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(_json_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    project: Mapped["Project"] = relationship(back_populates="versions")
    files: Mapped[List["ProjectFile"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("project_id", "version_number", name="uq_project_version_number"),
        Index("ix_project_versions_project_id", "project_id"),
    )


class ProjectFile(Base):
    """File contents belonging to a project, optionally scoped to a version."""
    __tablename__ = "project_files"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("project_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    path: Mapped[str] = mapped_column(String(1024), index=True)
    content: Mapped[str] = mapped_column(Text)
    is_binary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="files")
    version: Mapped[Optional["ProjectVersion"]] = relationship(back_populates="files")

    __table_args__ = (
        UniqueConstraint("project_id", "version_id", "path", name="uq_project_file_path_per_version"),
        Index("ix_project_files_project_id", "project_id"),
        Index("ix_project_files_version_id", "version_id"),
    )


# DEPLOYMENTS
class Deployment(Base):
    """Deployment records for a project."""
    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(100), index=True)  # e.g., vercel, netlify, flyio
    status: Mapped[str] = mapped_column(String(50), index=True)  # pending, success, failed
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(_json_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="deployments")

    __table_args__ = (
        Index("ix_deployments_project_id", "project_id"),
        Index("ix_deployments_status", "status"),
        Index("ix_deployments_provider", "provider"),
    )


# PREVIEW SESSIONS
class PreviewSession(Base):
    """Live preview session associated with a project."""
    __tablename__ = "preview_sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(_json_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="preview_sessions")

    __table_args__ = (
        Index("ix_preview_sessions_project_id", "project_id"),
        Index("ix_preview_sessions_status", "status"),
        Index("ix_preview_sessions_token", "token", unique=True),
    )


# AUDIT
class AuditEvent(Base):
    """Immutable audit trail for user actions and system events."""
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(_json_type(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_events")
    project: Mapped[Optional["Project"]] = relationship()

    __table_args__ = (
        Index("ix_audit_events_user_id", "user_id"),
        Index("ix_audit_events_project_id", "project_id"),
        Index("ix_audit_events_event_type", "event_type"),
    )


# PUBLIC_INTERFACE
def get_all_mapped_classes() -> list[type[Base]]:
    """Return a list of all mapped ORM classes in this module."""
    return [
        User,
        Template,
        Project,
        ChatSession,
        ChatMessage,
        ProjectVersion,
        ProjectFile,
        Deployment,
        PreviewSession,
        AuditEvent,
    ]
