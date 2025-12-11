# Lovable Backend API

FastAPI backend for AI code generation, chat, preview, versioning, export and deploy flows. Uses SQLAlchemy 2.x with an async engine.

- Health: GET /
- API docs: generated into interfaces/openapi.json
- WebSocket streaming:
  - Generation: /ws/generate/{task_id}
  - Preview reload: /preview/ws/preview/{project_id}

Ports
- Backend: 3001
- Frontend (paired): 3000
- Database (paired): 5000 (logical), actual example dev DB is SQLite; in production use Postgres.

Setup
1) Create environment file (optional for dev; sensible defaults are built-in):
   cp .env.example .env
   # edit values as needed

2) Install dependencies:
   pip install -r requirements.txt

3) Run (recommended):
   python run.py
   # binds to 0.0.0.0 on BACKEND_PORT (default 3001)

   or with uvicorn directly:
   uvicorn src.api.main:app --host 0.0.0.0 --port ${BACKEND_PORT:-3001} --reload

Environment variables (see src/core/config.py)
Defaults are provided for development so the service can start without a .env:
- DATABASE_URL: async driver URL (default sqlite+aiosqlite:///./dev.db)
- FRONTEND_ORIGIN: allowed origin for CORS (default http://localhost:3000)
- BACKEND_PORT: backend port (default 3001)
- STORAGE_DIR: local directory for exports/artifacts (default /tmp/lovable_storage)
- PREVIEW_BASE_URL: e.g., http://localhost:3001/preview (default)
- JWT_SECRET: dev secret (default dev-secret-not-for-prod; do not use in prod)

Notes
- Use an async DB driver in DATABASE_URL (postgresql+asyncpg, sqlite+aiosqlite).
- For real Postgres in dev, provision the lovable_database container and point DATABASE_URL accordingly.
- Generate OpenAPI: python -m src.api.generate_openapi

End-to-end flow (dev)
1) Login: POST /auth/login with { "email": "you@example.com" } to receive a dummy token "token-<email>".
2) Create project: POST /projects with Bearer token.
3) Chat & generate: create chat session, then POST /generate and connect WS /ws/generate/{task_id} for stream.
4) Preview: GET /preview/{project_id} (or /preview/{project_id}/file?path=...), connect WS for reload at /preview/ws/preview/{project_id}.
5) Edit files: use /projects/{project_id}/files endpoints; preview clients get reloads.
6) Snapshot: POST /projects/{project_id}/versions to snapshot; list/restore as needed.
7) Export: GET /projects/{project_id}/export to download zip.
8) Deploy: POST /projects/{project_id}/deploy to simulate provider deployment; poll status.
