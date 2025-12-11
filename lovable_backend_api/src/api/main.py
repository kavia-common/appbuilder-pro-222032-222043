from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings

# Initialize settings (loads from .env if present)
settings = get_settings()

app = FastAPI(
    title="Lovable Backend API",
    description="Handles AI code generation, chat logic, preview, export, and deployment APIs.",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Health and diagnostics"},
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

# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check", description="Simple health check endpoint to verify the API is running.")
def health_check():
    """Health check endpoint returning a static JSON response."""
    return {"message": "Healthy"}
