# JWT Authentication Dependencies
# ============================================================
#  AttendIQ — JWT Authentication Dependency
#  File: backend/app/dependencies/auth.py
#
#  Provides reusable FastAPI dependencies for:
#  - Extracting Bearer tokens from Authorization headers
#  - Validating tokens with Supabase
#  - Protecting routes with current_user dependency
# ============================================================

from fastapi import Depends, Header, HTTPException, status
from typing import Optional

from app.models.user import UserResponse
from app.services.auth_service import get_current_user_service

async def get_current_user(authorization: Optional[str] = Header(None, alias="Authorization")) -> UserResponse:
    """
    FastAPI dependency to extract and validate JWT token from Authorization header.

    Extracts the Bearer token, validates it with Supabase, and returns the current user.

    Args:
        authorization: Optional Authorization header value (injected by FastAPI).
                      Expected format: "Bearer <token>"

    Returns:
        UserResponse: The authenticated user's profile.

    Raises:
        HTTPException (401): If token is missing, invalid, or expired.

    Usage:
        @router.get("/protected")
        def protected_route(current_user: UserResponse = Depends(get_current_user)):
            return {"message": f"Hello, {current_user.full_name}"}
    """
    # Check if Authorization header is present
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if header uses Bearer scheme
    auth_parts = authorization.split()
    if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme. Use 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_parts[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token with Supabase and fetch user profile
    try:
        user = get_current_user_service(access_token=token)
        return user
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
