# ============================================================
#  AttendIQ — Faculty Service
#  File: backend/app/services/faculty_service.py
#  SDK FIX: See student_service.py header for full explanation.
# ============================================================

import logging
from uuid import uuid4
from typing import Optional

from app.db.supabase_client import supabase
from app.models.faculty import FacultyCreate, FacultyResponse, FacultyUpdate
from app.services.auth_service import hash_password

logger = logging.getLogger(__name__)


def _build_faculty_response(row: dict) -> FacultyResponse:
    return FacultyResponse(
        id=row["id"],
        full_name=row["full_name"],
        email=row["email"],
        phone=row.get("phone"),
        department_id=row.get("department_id"),
        is_active=row.get("is_active", True),
    )


def list_faculty(
    department_id: Optional[str] = None,
    search: Optional[str] = None,
) -> list[FacultyResponse]:
    query = supabase.table("profiles").select("*").eq("role", "faculty")
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
            or value in str(r.get("phone", "")).lower()
        ]

    return [_build_faculty_response(r) for r in rows]


def get_faculty(faculty_id: str) -> FacultyResponse:
    response = (
        supabase.table("profiles")
        .select("*")
        .eq("id", faculty_id)
        .eq("role", "faculty")
        .single()
        .execute()
    )
    if not response.data:
        raise ValueError("Faculty member not found.")
    return _build_faculty_response(response.data)


def create_faculty(payload: FacultyCreate) -> FacultyResponse:
    faculty_id = str(uuid4())
    password = payload.password or "welcome123"
    profile_data = {
        "id":            faculty_id,
        "full_name":     payload.full_name,
        "email":         payload.email,
        "phone":         payload.phone,
        "department_id": str(payload.department_id),
        "role":          "faculty",
        "is_active":     True,
        "password_hash": hash_password(password),
        "face_enrolled": False,
        "voice_enrolled": False,
    }

    # FIX: .insert(data).execute()  — no .select("*") chaining
    response = supabase.table("profiles").insert(profile_data).execute()

    if not response.data:
        logger.error("create_faculty: insert returned no data")
        raise RuntimeError("Unable to create faculty.")

    created = response.data[0] if isinstance(response.data, list) else response.data
    return _build_faculty_response(created)


def update_faculty(faculty_id: str, payload: FacultyUpdate) -> FacultyResponse:
    update_data = payload.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))
    if not update_data:
        raise ValueError("No update fields were provided.")
    if update_data.get("department_id") is not None:
        update_data["department_id"] = str(update_data["department_id"])

    # FIX: .update(data).eq(...).execute()  — no .select("*").single()
    response = (
        supabase.table("profiles")
        .update(update_data)
        .eq("id", faculty_id)
        .eq("role", "faculty")
        .execute()
    )
    if not response.data:
        raise ValueError("Faculty member not found.")

    return get_faculty(faculty_id)


def delete_faculty(faculty_id: str) -> None:
    check = (
        supabase.table("profiles")
        .select("id")
        .eq("id", faculty_id)
        .eq("role", "faculty")
        .single()
        .execute()
    )
    if not check.data:
        raise ValueError("Faculty member not found.")

    # FIX: .delete().eq(...).execute()  — no .select() chaining
    supabase.table("profiles").delete().eq("id", faculty_id).execute()