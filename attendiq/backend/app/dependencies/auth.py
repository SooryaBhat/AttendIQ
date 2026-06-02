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

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.user import UserResponse
from app.services.auth_service import get_current_user_service

# HTTP Bearer scheme for Swagger UI Authorize button
bearer_scheme = HTTPBearer(bearerFormat="JWT", auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> UserResponse:
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
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = get_current_user_service(access_token=token)
        return user
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
