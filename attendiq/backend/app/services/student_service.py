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


def list_students(department_id: Optional[str] = None, search: Optional[str] = None) -> list[StudentResponse]:
    query = supabase.table("profiles").select("*").eq("role", "student")

    if department_id:
        query = query.eq("department_id", department_id)

    response = query.execute()
    if getattr(response, "error", None):
        logger.error("Failed to list students: %s", response.error)
        raise RuntimeError("Unable to fetch students.")

    rows = response.data or []
    if search:
        value = search.strip().lower()
        rows = [
            row for row in rows
            if value in str(row.get("full_name", "")).lower()
            or value in str(row.get("email", "")).lower()
            or value in str(row.get("roll_number", "")).lower()
        ]

    return [_build_student_response(row) for row in rows]


def get_student(student_id: str) -> StudentResponse:
    response = (
        supabase.table("profiles")
        .select("*")
        .eq("id", student_id)
        .eq("role", "student")
        .single()
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to fetch student %s: %s", student_id, response.error)
        raise RuntimeError("Unable to fetch student.")

    if not response.data:
        raise ValueError("Student not found.")

    return _build_student_response(response.data)


def create_student(payload: StudentCreate) -> StudentResponse:
    student_id = str(uuid4())
    password = payload.password or "welcome123"
    profile_data = {
        "id": student_id,
        "full_name": payload.full_name,
        "roll_number": payload.roll_number,
        "email": payload.email,
        "phone": payload.phone,
        "department_id": str(payload.department_id) if payload.department_id else None,
        "face_enrolled": payload.face_enrolled,
        "voice_enrolled": payload.voice_enrolled,
        "role": "student",
        "is_active": True,
        "password_hash": hash_password(password),
    }

    response = (
        supabase.table("profiles")
        .insert(profile_data)
        .select("*")
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to create student: %s", response.error)
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

    response = (
        supabase.table("profiles")
        .update(update_data)
        .eq("id", student_id)
        .eq("role", "student")
        .select("*")
        .single()
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to update student %s: %s", student_id, response.error)
        raise RuntimeError("Unable to update student.")

    if not response.data:
        raise ValueError("Student not found.")

    return _build_student_response(response.data)


def delete_student(student_id: str) -> None:
    response = (
        supabase.table("profiles")
        .delete()
        .eq("id", student_id)
        .eq("role", "student")
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to delete student %s: %s", student_id, response.error)
        raise RuntimeError("Unable to delete student.")

    if not response.data:
        raise ValueError("Student not found.")
