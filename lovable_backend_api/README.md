# appbuilder-pro-222032-222043

This backend uses FastAPI with SQLAlchemy 2.x async engine.

Key modules:
- src/db/session.py: async engine and session helpers (reads DATABASE_URL from env via src.core.config)
- src/db/models.py: ORM models for users, projects, chat sessions/messages, templates, versions/files, deployments, preview sessions, and audit events.

Environment variables required (see src/core/config.py):
- DATABASE_URL (e.g., postgresql+asyncpg://user:pass@host:5432/dbname)
- FRONTEND_ORIGIN
- BACKEND_PORT
- STORAGE_DIR
- PREVIEW_BASE_URL
- JWT_SECRET

Notes:
- Ensure DATABASE_URL uses an async driver (e.g., postgresql+asyncpg, sqlite+aiosqlite).
- Use Alembic to generate and run migrations for tables defined in src/db/models.py.
