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