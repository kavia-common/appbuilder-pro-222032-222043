from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

# Note: No settings are required for dummy auth in this module.

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# Simple in-memory token store for demo/dummy auth.
# In production, use JWTs or a proper session/token system with storage.
_TOKEN_PREFIX = "token-"


class UserPublic(BaseModel):
    """Public shape of a user returned by auth endpoints."""
    email: str = Field(..., description="User email address")
    display_name: Optional[str] = Field(None, description="Optional display name")


class LoginRequest(BaseModel):
    """Login request payload accepting only email for dummy auth."""
    email: str = Field(..., description="Email used as identity for dummy auth")


class LoginResponse(BaseModel):
    """Login response returns a dummy token and user info."""
    access_token: str = Field(..., description="Dummy access token to use as Bearer token")
    token_type: str = Field("bearer", description="Token type")
    user: UserPublic = Field(..., description="Authenticated user information")


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Extract a bearer token from an Authorization header."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts[0], parts[1]
    if scheme.lower() != "bearer":
        return None
    return token.strip() or None


# PUBLIC_INTERFACE
async def get_current_user(authorization: Optional[str] = Header(default=None)) -> UserPublic:
    """FastAPI dependency to get the current user from a dummy token.

    The token format is 'token-<email>' issued by /auth/login. This function validates
    the token and returns a minimal user object.

    Args:
        authorization: Authorization header value ("Bearer <token>")

    Returns:
        UserPublic: the authenticated user's public profile.

    Raises:
        HTTPException 401 if token is missing or invalid.
    """
    token = _extract_bearer_token(authorization)
    if not token or not token.startswith(_TOKEN_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
        )
    email = token[len(_TOKEN_PREFIX) :].strip()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    # For this dummy auth, display_name mirrors email's local-part.
    display_name = email.split("@")[0] if "@" in email else email
    return UserPublic(email=email, display_name=display_name)


# PUBLIC_INTERFACE
@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login (dummy)",
    description="Issues a static/dummy token for the given email. Use the token as 'Authorization: Bearer <token>'.",
    responses={
        200: {"description": "Login succeeded, token returned"},
        400: {"description": "Invalid input"},
    },
)
async def login(payload: LoginRequest) -> LoginResponse:
    """Issue a dummy token for a given email.

    This endpoint does not verify passwords and is intended solely for development/demo.
    The token format is 'token-<email>' and should be used as a Bearer token.

    Args:
        payload: An object containing the email of the user.

    Returns:
        LoginResponse containing the dummy access token and user profile.
    """
    # Note: We don't need to load settings here; config is validated at app startup.
    email = payload.email.strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email is required")
    token = f"{_TOKEN_PREFIX}{email}"
    user = UserPublic(email=email, display_name=email.split("@")[0])
    return LoginResponse(access_token=token, token_type="bearer", user=user)


# PUBLIC_INTERFACE
@router.get(
    "/me",
    response_model=UserPublic,
    summary="Get current user",
    description="Returns the current user's profile inferred from the dummy token.",
)
async def me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    """Return the current authenticated user."""
    return current_user
