"""Application configuration loading via environment variables.

This module defines the AppSettings class, which reads configuration values
from environment variables (or a .env file if present) and exposes a singleton
settings instance for use across the application.

Environment variables loaded:
- DATABASE_URL: SQLAlchemy database URL (supports async drivers)
- FRONTEND_ORIGIN: Allowed origin for CORS (frontend URL)
- BACKEND_PORT: Port the backend should run on (int)
- STORAGE_DIR: Local filesystem directory for temporary or exported artifacts
- PREVIEW_BASE_URL: Base URL used for building preview links
- JWT_SECRET: Secret key for signing JWTs

Note: Do not commit actual secrets; provide them via environment at runtime.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class _CorsConfig(BaseModel):
    """CORS related settings bundled for easier injection."""
    frontend_origin: str = Field(..., description="Allowed frontend origin for CORS")


class AppSettings(BaseSettings):
    """Strongly-typed application settings loaded from environment."""

    # Database
    database_url: str = Field(..., alias="DATABASE_URL", description="SQLAlchemy database URL")

    # CORS and networking
    frontend_origin: str = Field(..., alias="FRONTEND_ORIGIN", description="Frontend origin for CORS")
    backend_port: int = Field(3001, alias="BACKEND_PORT", description="Port the backend runs on")

    # Storage and preview
    storage_dir: Path = Field(Path("/tmp/lovable_storage"), alias="STORAGE_DIR", description="Directory for persistent artifacts")
    preview_base_url: str = Field(..., alias="PREVIEW_BASE_URL", description="Base URL to construct preview links")

    # Auth
    jwt_secret: str = Field(..., alias="JWT_SECRET", description="Secret used to sign JWT tokens")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # PUBLIC_INTERFACE
    def cors(self) -> _CorsConfig:
        """Return a convenience structure containing CORS settings."""
        return _CorsConfig(frontend_origin=self.frontend_origin)


# PUBLIC_INTERFACE
@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings, loading from environment on first call.

    Raises:
        ValidationError: if required environment variables are missing or invalid.
    """
    try:
        settings = AppSettings()
    except ValidationError as e:
        # Provide a concise error to help operators configure env correctly.
        missing = []
        for err in e.errors():
            loc = ".".join([str(x) for x in err.get("loc", [])])
            if err.get("type", "").startswith("missing"):
                missing.append(loc)
        # Re-raise after computing missing vars for potential logging in future.
        raise
    # Ensure storage directory exists
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
    return settings
