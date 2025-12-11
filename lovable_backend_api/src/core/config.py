"""Application configuration loading via environment variables.

This module defines the AppSettings class, which reads configuration values
from environment variables (or a .env file if present) and exposes a singleton
settings instance for use across the application.

Environment variables loaded (defaults provided for development so the app can start):
- DATABASE_URL: SQLAlchemy database URL (supports async drivers) [default: sqlite+aiosqlite:///./dev.db]
- FRONTEND_ORIGIN: Allowed origin for CORS (frontend URL) [default: http://localhost:3000]
- BACKEND_PORT: Port the backend should run on (int) [default: 3001]
- STORAGE_DIR: Local filesystem directory for temporary or exported artifacts [default: /tmp/lovable_storage]
- PREVIEW_BASE_URL: Base URL used for building preview links [default: http://localhost:3001/preview]
- JWT_SECRET: Secret key for signing JWTs [default: dev-secret-not-for-prod]

Note: Do not commit real secrets for production; override via environment at runtime.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class _CorsConfig(BaseModel):
    """CORS related settings bundled for easier injection."""
    frontend_origin: str = Field(..., description="Allowed frontend origin for CORS")


class AppSettings(BaseSettings):
    """Strongly-typed application settings loaded from environment."""

    # Database
    database_url: str = Field(
        "sqlite+aiosqlite:///./dev.db",
        alias="DATABASE_URL",
        description="SQLAlchemy database URL",
    )

    # CORS and networking
    frontend_origin: str = Field(
        "http://localhost:3000",
        alias="FRONTEND_ORIGIN",
        description="Frontend origin for CORS",
    )
    backend_port: int = Field(3001, alias="BACKEND_PORT", description="Port the backend runs on")

    # Storage and preview
    storage_dir: Path = Field(
        Path("/tmp/lovable_storage"),
        alias="STORAGE_DIR",
        description="Directory for persistent artifacts",
    )
    preview_base_url: str = Field(
        "http://localhost:3001/preview",
        alias="PREVIEW_BASE_URL",
        description="Base URL to construct preview links",
    )

    # Auth
    jwt_secret: str = Field(
        "dev-secret-not-for-prod",
        alias="JWT_SECRET",
        description="Secret used to sign JWT tokens",
    )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # PUBLIC_INTERFACE
    def cors(self) -> _CorsConfig:
        """Return a convenience structure containing CORS settings."""
        return _CorsConfig(frontend_origin=self.frontend_origin)


# PUBLIC_INTERFACE
@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings, loading from environment on first call.

    This function ensures that required directories exist and returns
    defaults suitable for development if environment variables are not set.
    """
    settings = AppSettings()
    # Ensure storage directory exists
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
    return settings
