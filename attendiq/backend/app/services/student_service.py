# ============================================================
#  AttendIQ — Student Service
#  File: backend/app/services/student_service.py
#
#  SDK FIX SUMMARY (supabase-py v2.x / postgrest-py v2.x):
#  ─────────────────────────────────────────────────────────
#  .insert()  → returns SyncQueryRequestBuilder  → has .select()
#  .update()  → returns SyncFilterRequestBuilder → has .select()
#  .delete()  → returns SyncFilterRequestBuilder → has .select()
#
#  BROKEN pattern:  .insert(data).select("*").execute()
#    insert() already defaults to returning=representation,
#    so chaining .select("*") on SyncQueryRequestBuilder is
#    redundant AND breaks — SyncQueryRequestBuilder.select()
#    re-opens a SELECT query, it does NOT mean "return columns".
#
#  FIXED pattern:   .insert(data).execute()
#    Response data is already the full row via representation.
#
#  For update/delete after filters:
#  BROKEN:  .update(data).eq(...).select("*").single().execute()
#  FIXED:   .update(data).eq(...).execute()  then re-fetch if needed.
#    SyncFilterRequestBuilder DOES have .select() but chaining it
#    after .eq() causes the builder to switch to a SELECT operation
#    and drop the update, which is wrong.
# ============================================================

import logging
from uuid import uuid4
from typing import Optional

from app.db.supabase_client import supabase
from app.models.student import StudentCreate, StudentResponse, StudentUpdate
from app.services.auth_service import hash_password

logger = logging.getLogger(__name__)


def _build_student_response(row: dict) -> StudentResponse:
    return StudentResponse(
        id=row["id"],
        full_name=row["full_name"],
        roll_number=row["roll_number"],
        email=row["email"],
        phone=row.get("phone"),
        department_id=row.get("department_id"),
        face_enrolled=row.get("face_enrolled", False),
        voice_enrolled=row.get("voice_enrolled", False),
        is_active=row.get("is_active", True),
    )


def list_students(
    department_id: Optional[str] = None,
    search: Optional[str] = None,
) -> list[StudentResponse]:
    # .select("*").eq() → SyncFilterRequestBuilder — no change needed here
    query = supabase.table("profiles").select("*").eq("role", "student")
    if department_id:
        query = query.eq("department_id", department_id)

    response = query.execute()
    rows = response.data or []

    if search:
        value = search.strip().lower()
        rows = [
            r for r in rows
            if value in str(r.get("full_name", "")).lower()
            or value in str(r.get("email", "")).lower()
            or value in str(r.get("roll_number", "")).lower()
        ]

    return [_build_student_response(r) for r in rows]


def get_student(student_id: str) -> StudentResponse:
    response = (
        supabase.table("profiles")
        .select("*")
        .eq("id", student_id)
        .eq("role", "student")
        .single()
        .execute()
    )
    if not response.data:
        raise ValueError("Student not found.")
    return _build_student_response(response.data)


def create_student(payload: StudentCreate) -> StudentResponse:
    student_id = str(uuid4())
    password = payload.password or "welcome123"
    profile_data = {
        "id":            student_id,
        "full_name":     payload.full_name,
        "roll_number":   payload.roll_number,
        "email":         payload.email,
        "phone":         payload.phone,
        "department_id": str(payload.department_id) if payload.department_id else None,
        "face_enrolled": payload.face_enrolled,
        "voice_enrolled": payload.voice_enrolled,
        "role":          "student",
        "is_active":     True,
        "password_hash": hash_password(password),
    }

    # FIX: .insert(data).execute()  — do NOT chain .select("*")
    # insert() already returns the full row (returning=representation by default)
    response = supabase.table("profiles").insert(profile_data).execute()

    if not response.data:
        logger.error("create_student: insert returned no data")
        raise RuntimeError("Unable to create student.")

    created = response.data[0] if isinstance(response.data, list) else response.data
    return _build_student_response(created)


def update_student(student_id: str, payload: StudentUpdate) -> StudentResponse:
    update_data = payload.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))
    if not update_data:
        raise ValueError("No update fields were provided.")
    if update_data.get("department_id") is not None:
        update_data["department_id"] = str(update_data["department_id"])

    # FIX: .update(data).eq(...).execute()  — do NOT chain .select("*").single()
    # After update, re-fetch with a plain select to get the updated row.
    response = (
        supabase.table("profiles")
        .update(update_data)
        .eq("id", student_id)
        .eq("role", "student")
        .execute()
    )

    if not response.data:
        raise ValueError("Student not found.")

    # Re-fetch the updated row cleanly
    return get_student(student_id)


def delete_student(student_id: str) -> None:
    # First verify it exists
    check = (
        supabase.table("profiles")
        .select("id")
        .eq("id", student_id)
        .eq("role", "student")
        .single()
        .execute()
    )
    if not check.data:
        raise ValueError("Student not found.")

    # FIX: .delete().eq(...).execute()  — no .select() chaining
    supabase.table("profiles").delete().eq("id", student_id).execute()


# ============================================================
#  STUDENT ACCOUNT ACTIVATION
# ============================================================

import string
import random
from datetime import datetime, timedelta
from app.models.user import UserResponse, UserRole


def generate_activation_token() -> str:
    """Generate a secure activation token."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=64))


def create_student_with_activation(
    full_name: str,
    email: str,
    usn: str,
    department_id: str,
    semester: int,
    section: str,
) -> dict:
    """
    Create a student account with activation token (not yet active).
    Returns activation token that must be sent to student.
    """
    token = generate_activation_token()
    expires = datetime.utcnow() + timedelta(days=7)  # Token valid for 7 days
    
    student_id = str(uuid4())
    profile_data = {
        "id": student_id,
        "full_name": full_name,
        "email": email,
        "roll_number": usn,
        "department_id": str(department_id),
        "semester": semester,
        "section": section,
        "role": "student",
        "is_active": False,
        "activation_token": token,
        "activation_expires": expires.isoformat(),
        "password_hash": "pending",
        "face_enrolled": False,
        "voice_enrolled": False,
    }
    
    response = supabase.table("profiles").insert(profile_data).execute()
    
    if not response.data:
        raise RuntimeError("Failed to create student account")
    
    return {
        "student_id": student_id,
        "activation_token": token,
        "activation_url": f"/activate-account/{token}",
        "expires_at": expires.isoformat(),
    }


def activate_student_account(token: str, password: str) -> UserResponse:
    """
    Activate a student account by validating token and setting password.
    """
    response = (
        supabase.table("profiles")
        .select("*")
        .eq("activation_token", token)
        .single()
        .execute()
    )
    
    if not response.data:
        raise ValueError("Invalid or expired activation token")
    
    student = response.data
    
    # Check if token has expired
    expires_at = datetime.fromisoformat(student["activation_expires"])
    if datetime.utcnow() > expires_at:
        raise ValueError("Activation token has expired")
    
    # Update student account to activate
    update_response = (
        supabase.table("profiles")
        .update({
            "password_hash": hash_password(password),
            "is_active": True,
            "activation_token": None,
            "activation_expires": None,
        })
        .eq("id", student["id"])
        .execute()
    )
    
    if not update_response.data:
        raise ValueError("Failed to activate account")
    
    return UserResponse(
        id=student["id"],
        full_name=student["full_name"],
        email=student["email"],
        role=UserRole(student["role"]),
        department_id=student.get("department_id"),
        roll_number=student.get("roll_number"),
        phone=student.get("phone"),
        is_active=True,
        face_enrolled=False,
        voice_enrolled=False,
    )


def bulk_import_students(students_data: list) -> dict:
    """
    Bulk import students from CSV data.
    Each item should have: full_name, email, usn, department_id, semester, section
    Returns activation tokens for all successfully created students.
    """
    tokens = []
    errors = []
    
    for idx, student in enumerate(students_data):
        try:
            token_info = create_student_with_activation(
                full_name=student["full_name"],
                email=student["email"],
                usn=student["usn"],
                department_id=student["department_id"],
                semester=int(student.get("semester", 1)),
                section=student.get("section", ""),
            )
            tokens.append({
                "email": student["email"],
                "student_id": token_info["student_id"],
                "activation_token": token_info["activation_token"],
                "activation_url": token_info["activation_url"],
            })
        except Exception as e:
            errors.append({
                "row": idx + 1,
                "email": student.get("email"),
                "error": str(e),
            })
    
    return {
        "imported": len(tokens),
        "failed": len(errors),
        "activation_tokens": tokens,
        "errors": errors,
    }