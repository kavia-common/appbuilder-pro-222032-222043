#!/usr/bin/env python3
"""
Entrypoint script to run the Lovable Backend API with uvicorn.

- Binds to 0.0.0.0 on the configured BACKEND_PORT (default 3001)
- Imports the FastAPI app from src.api.main:app
- Uses environment (.env) via pydantic-settings
"""

import uvicorn

# Import app and settings
from src.api.main import app
from src.core.config import get_settings


def main() -> None:
    """Start the FastAPI application using uvicorn on the configured port."""
    settings = get_settings()
    port = int(settings.backend_port or 3001)

    # Bind to 0.0.0.0 so container is reachable externally
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
