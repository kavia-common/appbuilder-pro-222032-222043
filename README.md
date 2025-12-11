# appbuilder-pro-222032-222043

Lovable: a web platform to generate, preview, and deploy fullstack apps from natural language.

Containers
- lovable_backend_api (FastAPI) – port 3001
- lovable_frontend_app (Next.js) – port 3000
- lovable_database (PostgreSQL) – logical port 5000 (provision per environment)

Quick start (dev)
- Backend:
  - cd lovable_backend_api
  - cp .env.example .env
  - pip install -r requirements.txt
  - uvicorn src.api.main:app --host 0.0.0.0 --port ${BACKEND_PORT:-3001} --reload
- Frontend:
  - cd lovable_frontend_app
  - cp .env.example .env
  - npm install
  - npm run dev (exposes :3000)
- Database:
  - Provision Postgres if needed. In dev you can start with SQLite via backend .env example. For Postgres, set DATABASE_URL accordingly.

Environment variables
Backend (.env in lovable_backend_api):
- DATABASE_URL, FRONTEND_ORIGIN, BACKEND_PORT, STORAGE_DIR, PREVIEW_BASE_URL, JWT_SECRET

Frontend (.env in lovable_frontend_app):
- NEXT_PUBLIC_BACKEND_URL (e.g., http://localhost:3001)
- Optionally: NEXT_PUBLIC_WS_URL if frontend needs explicit WS origin

Database (.env in lovable_database, if applicable):
- POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT

Ports
- Database: 5000 (logical); check your actual DB port if running locally or via cloud
- Backend: 3001
- Frontend: 3000

End-to-end flow
1) Login: POST /auth/login to receive dummy Bearer token (token-<email>).
2) Create project: POST /projects (Bearer token).
3) Chat & generate: create chat session and POST /generate; connect WS /ws/generate/{task_id}.
4) Preview: GET /preview/{project_id}; connect WS /preview/ws/preview/{project_id} for reloads.
5) Edit files: /projects/{project_id}/files APIs; preview auto-reloads.
6) Snapshot: /projects/{project_id}/versions (create/list/restore).
7) Export: /projects/{project_id}/export to download zip.
8) Deploy: /projects/{project_id}/deploy then GET status.

Notes
- For dev convenience, the backend supports SQLite via sqlite+aiosqlite. For production use Postgres via postgresql+asyncpg.
- Do not commit real secrets. Provide JWT_SECRET and DB credentials via environment.
