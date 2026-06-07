from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.models.user import TokenResponse, UserLogin, UserRegister, UserResponse
from app.services.auth_service import (
    login_user as login_user_service,
    register_user as register_user_service,
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


class PasswordChangePayload(BaseModel := __import__('pydantic').BaseModel):
    current_password: str
    new_password: str


@router.get("/profile")
def get_full_profile(current_user: UserResponse = Depends(get_current_user)) -> dict:
    """
    Extended profile with department name, enrolled subjects, and biometric status.
    Used by all profile pages.
    """
    from app.db.supabase_client import supabase

    profile = current_user.dict()

    # Enrich with department name
    if current_user.department_id:
        dept = (
            supabase.table("departments")
            .select("id, name, code")
            .eq("id", str(current_user.department_id))
            .single()
            .execute()
        )
        profile["department"] = dept.data if dept.data else None

    # Add enrolled subjects (for students) or assigned subjects (for faculty)
    if current_user.role == "student":
        enr = (
            supabase.table("student_subjects")
            .select("subject_id")
            .eq("student_id", str(current_user.id))
            .execute()
        )
        subject_ids = [r["subject_id"] for r in (enr.data or [])]
        if subject_ids:
            subs = supabase.table("subjects").select("id, name, code, semester, section, faculty_id").in_("id", subject_ids).execute()
            profile["enrolled_subjects"] = subs.data or []
        else:
            profile["enrolled_subjects"] = []
    elif current_user.role == "faculty":
        subs = (
            supabase.table("subjects")
            .select("id, name, code, semester, section")
            .eq("faculty_id", str(current_user.id))
            .execute()
        )
        profile["assigned_subjects"] = subs.data or []

    return profile


@router.post("/change-password")
def change_password(
    payload: PasswordChangePayload,
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    from app.db.supabase_client import supabase
    from app.services.auth_service import verify_password, hash_password

    user_row = (
        supabase.table("profiles")
        .select("password_hash")
        .eq("id", str(current_user.id))
        .single()
        .execute()
    )
    if not user_row.data:
        raise HTTPException(status_code=404, detail="User not found.")

    if not verify_password(payload.current_password, user_row.data["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    new_hash = hash_password(payload.new_password)
    supabase.table("profiles").update({"password_hash": new_hash}).eq("id", str(current_user.id)).execute()
    return {"success": True, "message": "Password changed successfully."}
