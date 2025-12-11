from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.routers.auth import router as auth_router
from src.routers.projects import router as projects_router
from src.routers.chat import router as chat_router
from src.routers.generate import router as generate_router

# Initialize settings (loads from .env if present)
settings = get_settings()

app = FastAPI(
    title="Lovable Backend API",
    description=(
        "Handles AI code generation, chat logic, preview, export, and deployment APIs. "
        "WebSocket streaming is available for generation at /ws/generate/{task_id} (send Authorization header)."
    ),
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Health and diagnostics"},
        {"name": "auth", "description": "Authentication (dummy)"},
        {"name": "projects", "description": "Project management"},
        {"name": "chat", "description": "Chat sessions and messages"},
        {"name": "generation", "description": "Start AI generation and stream results over WebSocket"},
    ],
)

# CORS setup: allow frontend origin injected via env
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(chat_router)
app.include_router(generate_router)

# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check", description="Simple health check endpoint to verify the API is running.")
def health_check():
    """Health check endpoint returning a static JSON response."""
    return {"message": "Healthy"}

# PUBLIC_INTERFACE
@app.get(
    "/docs/websocket",
    tags=["generation"],
    summary="WebSocket usage",
    description=(
        "Usage notes for WebSocket streaming:\n"
        "- Start a task with POST /generate to receive task_id and websocket_url.\n"
        "- Connect to /ws/generate/{task_id} and include 'Authorization: Bearer token-<email>' header.\n"
        "- Server streams JSON lines with fields: type and data.\n"
    ),
)
def websocket_usage():
    """Return a short usage guide for WebSocket streaming."""
    return {
        "websocket_endpoint": "/ws/generate/{task_id}",
        "auth": "Send Authorization: Bearer token-<email> header when connecting.",
        "flow": [
            "POST /generate with prompt",
            "Receive task_id and websocket_url",
            "Connect to WS and read events until end",
        ],
        "event_types": ["status", "token", "file_diff", "error", "end"],
    }
