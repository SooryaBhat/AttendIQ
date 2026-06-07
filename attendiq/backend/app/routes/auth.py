from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.models.user import TokenResponse, UserLogin, UserRegister, UserResponse, UserUpdate
from app.services.auth_service import (
    login_user as login_user_service,
    register_user as register_user_service,
    update_user as update_user_service,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserRegister) -> UserResponse:
    """Register a new user and create a profile record."""
    try:
        return register_user_service(user)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login_user(credentials: UserLogin) -> TokenResponse:
    """Authenticate a user and return an access token plus profile."""
    try:
        return login_user_service(credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.get("/me", response_model=UserResponse)
def get_me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated current user's profile.
    
    Requires valid Bearer token in Authorization header.
    Token is automatically validated by the get_current_user dependency.
    
    Returns:
        UserResponse: The current authenticated user's profile.
        
    Raises:
        401: If Authorization header is missing, invalid, or token is expired.
    """
    return current_user


@router.put("/profile", response_model=UserResponse)
def update_profile(payload: UserUpdate, current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Update the current authenticated user's profile."""
    try:
        update_data = payload.dict(exclude_unset=True)
        # Only allow basic profile updates from the authenticated user.
        allowed_keys = {"full_name", "email", "password", "phone"}
        safe_updates = {k: v for k, v in update_data.items() if k in allowed_keys}
        if not safe_updates:
            raise ValueError("No allowed profile fields were provided.")
        return update_user_service(str(current_user.id), safe_updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
