import json
import os
import sys
from typing import Any, Dict

"""
Utility script to generate and write OpenAPI schema for the FastAPI app.

This script:
- Safely initializes the FastAPI app (without requiring real environment variables).
- Injects explicit documentation entries for WebSocket endpoints since OpenAPI
  does not natively include ws routes.
- Writes the final schema to interfaces/openapi.json.

Run:
    python -m src.api.generate_openapi
"""

# Ensure we can import the package when invoked directly
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Set minimal env defaults to avoid validation errors during import
# These are ONLY for schema generation and have no effect at runtime servers.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./dev-openapi.db")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:3000")
os.environ.setdefault("BACKEND_PORT", "3001")
os.environ.setdefault("STORAGE_DIR", "/tmp/lovable_storage")
os.environ.setdefault("PREVIEW_BASE_URL", "http://localhost:3001/preview")
os.environ.setdefault("JWT_SECRET", "dev-secret-not-for-prod")

from src.api.main import app  # noqa: E402


def _augment_with_websocket_docs(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Add pseudo-docs for WebSocket endpoints to the OpenAPI as vendor extensions.

    OpenAPI does not define ws routes. We expose them under a custom extension for
    consumer UIs and for our frontend to discover usage.
    """
    x_ws_endpoints = [
        {
            "operation_id": "ws_stream_generation",
            "summary": "WebSocket: Generation stream",
            "path": "/ws/generate/{task_id}",
            "method": "GET",
            "protocol": "websocket",
            "tags": ["generation"],
            "description": (
                "Connect with header 'Authorization: Bearer token-<email>'. "
                "Server streams JSON lines with fields {type, data}. "
                "Event types: status, token, file_diff, error, end."
            ),
            "path_params": [{"name": "task_id", "in": "path", "required": True, "schema": {"type": "string"}}],
        },
        {
            "operation_id": "ws_preview_reload",
            "summary": "WebSocket: Preview reload channel",
            "path": "/preview/ws/preview/{project_id}",
            "aliases": ["/ws/preview/{project_id}"],
            "method": "GET",
            "protocol": "websocket",
            "tags": ["preview"],
            "description": (
                "Connect with header 'Authorization: Bearer token-<email>'. "
                "Server pushes messages like {\"type\":\"reload\",\"data\":{\"reason\":\"file_change\"}}. "
                "Send 'ping' to keep-alive; server responds 'pong'."
            ),
            "path_params": [{"name": "project_id", "in": "path", "required": True, "schema": {"type": "string"}}],
        },
    ]
    schema.setdefault("info", {})
    schema["info"].setdefault("x-websocket-endpoints", x_ws_endpoints)

    # Also surface an index help at /docs/websocket if present
    schema.setdefault("paths", {})
    # No changes to real HTTP routes here; the /docs/websocket is already a GET route in app.
    return schema


def main() -> None:
    """Generate and write the OpenAPI schema with WebSocket docs included."""
    openapi_schema = app.openapi()
    openapi_schema = _augment_with_websocket_docs(openapi_schema)

    # Write to interfaces/openapi.json relative to repo root of this container
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "interfaces"))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "openapi.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"Wrote OpenAPI schema to {output_path}")


if __name__ == "__main__":
    main()
