# ============================================================
#  AttendIQ — Auth Service
#  File: backend/app/services/auth_service.py
#
#  FIX: Supabase Python SDK v2 sign_up() response structure
#  The user ID lives at response.user.id, NOT response.data.user.id
# ============================================================

import logging
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.db.supabase_client import supabase
from app.models.user import UserLogin, UserRegister, UserResponse, TokenResponse, UserRole

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================
#  PASSWORD UTILITIES
# ============================================================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ============================================================
#  JWT UTILITIES
# ============================================================

def create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def get_current_user_service(access_token: str) -> UserResponse:
    payload = decode_access_token(access_token)
    if not payload or not payload.get("sub"):
        raise ValueError("Invalid or expired token.")

    user_id = payload["sub"]
    response = (
        supabase.table("profiles")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )

    if getattr(response, "error", None):
        raise ValueError("Unable to validate token.")

    if not response.data:
        raise ValueError("Authenticated user not found.")

    profile = response.data
    return UserResponse(
        id=profile["id"],
        full_name=profile["full_name"],
        email=profile["email"],
        role=UserRole(profile["role"]),
        department_id=profile.get("department_id"),
        roll_number=profile.get("roll_number"),
        phone=profile.get("phone"),
        is_active=profile["is_active"],
        face_enrolled=profile["face_enrolled"],
        voice_enrolled=profile["voice_enrolled"],
    )


# ============================================================
#  DEBUG HELPER — prints the full sign_up response structure
#  Remove or disable in production.
# ============================================================

def _debug_signup_response(response) -> None:
    """
    Prints every attribute of the sign_up response so you can
    see exactly what the SDK version you have installed returns.
    """
    logger.debug("=== Supabase sign_up() raw response ===")
    logger.debug("  type(response)      : %s", type(response))
    logger.debug("  dir(response)       : %s", [a for a in dir(response) if not a.startswith("_")])

    # Attempt common attribute paths and log what exists
    for attr in ("user", "session", "data", "error"):
        val = getattr(response, attr, "<<missing>>")
        logger.debug("  response.%-10s: %s", attr, val)

    # If response.user exists, log its id
    user_obj = getattr(response, "user", None)
    if user_obj is not None:
        logger.debug("  response.user type  : %s", type(user_obj))
        logger.debug("  response.user.id    : %s", getattr(user_obj, "id", "<<missing>>"))
        logger.debug("  response.user attrs : %s",
                     [a for a in dir(user_obj) if not a.startswith("_")])

    # If response.data exists, try to find a nested user
    data = getattr(response, "data", None)
    if data is not None:
        logger.debug("  response.data       : %s", data)
        if isinstance(data, dict):
            nested_user = data.get("user")
            logger.debug("  response.data['user']: %s", nested_user)
    logger.debug("=== end sign_up response ===")


# ============================================================
#  EXTRACT USER ID — handles all known SDK v2 response shapes
# ============================================================

def _extract_user_id(response) -> Optional[str]:
    """
    Supabase Python SDK v2 changed the sign_up response structure.
    This function handles every known variant robustly.

    Known structures across SDK versions:
    ─────────────────────────────────────────────────────────────
    SDK ≥ 2.0  (current):  response.user.id          ← PRIMARY
    SDK 1.x  (legacy):     response.data.user['id']
    Some builds:           response.data['user']['id']
    ─────────────────────────────────────────────────────────────
    """

    # ── Path 1: response.user.id  (SDK v2, most common) ──────
    user_obj = getattr(response, "user", None)
    if user_obj is not None:
        uid = getattr(user_obj, "id", None)
        if uid:
            logger.debug("Extracted user ID via response.user.id: %s", uid)
            return str(uid)

    # ── Path 2: response.data.user.id  (some SDK v2 builds) ──
    data = getattr(response, "data", None)
    if data is not None:
        # data might be an object with a .user attribute
        nested_user = getattr(data, "user", None)
        if nested_user is not None:
            uid = getattr(nested_user, "id", None) or (
                nested_user.get("id") if isinstance(nested_user, dict) else None
            )
            if uid:
                logger.debug("Extracted user ID via response.data.user.id: %s", uid)
                return str(uid)

        # data might be a dict
        if isinstance(data, dict):
            user_dict = data.get("user", {})
            if isinstance(user_dict, dict):
                uid = user_dict.get("id")
                if uid:
                    logger.debug("Extracted user ID via response.data['user']['id']: %s", uid)
                    return str(uid)

    logger.warning("Could not extract user ID from sign_up response: %s", response)
    return None


# ============================================================
#  REGISTER
# ============================================================

def register_user(payload: UserRegister) -> UserResponse:
    """
    Register a new user.
    1. Create Supabase Auth account (for authentication)
    2. Insert profile row in public.profiles (for app data)
    """

    # ── Step 1: Create Supabase Auth user ────────────────────
    logger.info("Registering user: %s (role=%s)", payload.email, payload.role)

    auth_response = supabase.auth.sign_up({
        "email": payload.email,
        "password": payload.password,
    })

    # Print full response structure for debugging
    _debug_signup_response(auth_response)

    # Extract user ID from whichever SDK response shape we got
    user_id = _extract_user_id(auth_response)

    if not user_id:
        # Last resort: check if user already exists (e.g. email confirmation pending)
        # Some Supabase projects return an empty user when email confirmation is required
        logger.warning(
            "sign_up did not return a user ID for %s. "
            "This can happen when 'Confirm email' is enabled in Supabase Auth settings. "
            "Check Supabase Dashboard → Authentication → Users to verify the account was created.",
            payload.email
        )
        raise ValueError(
            "Supabase created the user but did not return an ID. "
            "Possible causes:\n"
            "  1. Email confirmation is enabled — disable it in Supabase Auth settings for dev\n"
            "  2. SDK version mismatch — check logs above for the actual response structure\n"
            "  3. The email is already registered"
        )

    # ── Step 2: Insert profile row ────────────────────────────
    profile_data = {
        "id":            user_id,
        "email":         payload.email,
        "password_hash": hash_password(payload.password),
        "full_name":     payload.full_name,
        "role":          payload.role.value,
        "department_id": str(payload.department_id) if payload.department_id else None,
        "roll_number":   payload.roll_number,
        "phone":         payload.phone,
        "is_active":     True,
        "face_enrolled": False,
        "voice_enrolled": False,
    }

    db_response = supabase.table("profiles").insert(profile_data).execute()

    if not db_response.data:
        raise RuntimeError("Profile insert returned no data. Check Supabase RLS policies.")

    created = db_response.data[0]
    logger.info("Profile created successfully for user_id=%s", user_id)

    return UserResponse(
        id=             created["id"],
        full_name=      created["full_name"],
        email=          created["email"],
        role=           UserRole(created["role"]),
        department_id=  created.get("department_id"),
        roll_number=    created.get("roll_number"),
        phone=          created.get("phone"),
        is_active=      created["is_active"],
        face_enrolled=  created["face_enrolled"],
        voice_enrolled= created["voice_enrolled"],
    )


# ============================================================
#  LOGIN
# ============================================================

def login_user(payload: UserLogin) -> TokenResponse:
    """
    Authenticate a user and return a JWT access token.
    """
    # Fetch profile by email
    db_response = (
        supabase.table("profiles")
        .select("*")
        .eq("email", payload.email)
        .single()
        .execute()
    )

    if not db_response.data:
        raise ValueError("Invalid email or password.")

    profile = db_response.data

    if not profile.get("is_active"):
        raise ValueError("Account is deactivated. Contact your administrator.")

    if not verify_password(payload.password, profile["password_hash"]):
        raise ValueError("Invalid email or password.")

    # Build JWT payload
    token = create_access_token({
        "sub":   profile["id"],
        "email": profile["email"],
        "role":  profile["role"],
    })

    user = UserResponse(
        id=             profile["id"],
        full_name=      profile["full_name"],
        email=          profile["email"],
        role=           UserRole(profile["role"]),
        department_id=  profile.get("department_id"),
        roll_number=    profile.get("roll_number"),
        phone=          profile.get("phone"),
        is_active=      profile["is_active"],
        face_enrolled=  profile["face_enrolled"],
        voice_enrolled= profile["voice_enrolled"],
    )

    return TokenResponse(access_token=token, user=user)