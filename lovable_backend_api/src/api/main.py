from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.routers.auth import router as auth_router
from src.routers.projects import router as projects_router

# Initialize settings (loads from .env if present)
settings = get_settings()

app = FastAPI(
    title="Lovable Backend API",
    description="Handles AI code generation, chat logic, preview, export, and deployment APIs.",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Health and diagnostics"},
        {"name": "auth", "description": "Authentication (dummy)"},
        {"name": "projects", "description": "Project management"},
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

# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check", description="Simple health check endpoint to verify the API is running.")
def health_check():
    """Health check endpoint returning a static JSON response."""
    return {"message": "Healthy"}
