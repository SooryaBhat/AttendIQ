import logging
from uuid import uuid4
from typing import Optional

from app.db.supabase_client import supabase
from app.models.subject import (
    SubjectCreate,
    SubjectResponse,
    SubjectUpdate,
)
from app.models.user import UserResponse

logger = logging.getLogger(__name__)


def _build_subject_response(row: dict) -> SubjectResponse:
    return SubjectResponse(
        id=row["id"],
        name=row["name"],
        code=row["code"],
        faculty_id=row.get("faculty_id"),
        department_id=row.get("department_id"),
        created_at=row.get("created_at"),
    )


def list_subjects() -> list[SubjectResponse]:
    response = supabase.table("subjects").select("*").execute()
    if getattr(response, "error", None):
        logger.error("Failed to list subjects: %s", response.error)
        raise RuntimeError("Unable to fetch subjects.")

    rows = response.data or []
    return [_build_subject_response(row) for row in rows]


def get_subject(subject_id: str) -> SubjectResponse:
    response = (
        supabase.table("subjects")
        .select("*")
        .eq("id", subject_id)
        .single()
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to fetch subject %s: %s", subject_id, response.error)
        raise RuntimeError("Unable to fetch subject.")

    if not response.data:
        raise ValueError("Subject not found.")

    return _build_subject_response(response.data)


def create_subject(payload: SubjectCreate) -> SubjectResponse:
    subject_data = payload.dict()
    subject_data["id"] = str(uuid4())

    response = (
        supabase.table("subjects")
        .insert(subject_data)
        .select("*")
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to create subject: %s", response.error)
        raise RuntimeError("Unable to create subject.")

    created = response.data[0] if isinstance(response.data, list) else response.data
    return _build_subject_response(created)


def update_subject(subject_id: str, payload: SubjectUpdate) -> SubjectResponse:
    update_data = payload.dict(exclude_unset=True)
    if not update_data:
        raise ValueError("No updates provided.")

    response = (
        supabase.table("subjects")
        .update(update_data)
        .eq("id", subject_id)
        .select("*")
        .single()
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to update subject %s: %s", subject_id, response.error)
        raise RuntimeError("Unable to update subject.")

    if not response.data:
        raise ValueError("Subject not found.")

    return _build_subject_response(response.data)


def delete_subject(subject_id: str) -> None:
    response = (
        supabase.table("subjects")
        .delete()
        .eq("id", subject_id)
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to delete subject %s: %s", subject_id, response.error)
        raise RuntimeError("Unable to delete subject.")

    if not response.data:
        raise ValueError("Subject not found.")


def enroll_student(subject_id: str, student_id: str) -> dict:
    # validate subject exists
    resp = (
        supabase.table("subjects").select("*").eq("id", subject_id).single().execute()
    )
    if getattr(resp, "error", None):
        logger.error("Failed to validate subject %s: %s", subject_id, resp.error)
        raise RuntimeError("Unable to validate subject.")
    if not resp.data:
        raise ValueError("Subject not found.")

    # validate student exists
    sresp = (
        supabase.table("profiles").select("*").eq("id", student_id).single().execute()
    )
    if getattr(sresp, "error", None):
        logger.error("Failed to validate student %s: %s", student_id, sresp.error)
        raise RuntimeError("Unable to validate student.")
    if not sresp.data:
        raise ValueError("Student not found.")

    # prevent duplicate enrollment
    exist = (
        supabase.table("subject_enrollments")
        .select("*")
        .eq("subject_id", subject_id)
        .eq("student_id", student_id)
        .execute()
    )
    if getattr(exist, "error", None):
        logger.error("Failed to check existing enrollment: %s", exist.error)
        raise RuntimeError("Unable to check enrollment.")
    if exist.data:
        raise ValueError("Student already enrolled in this subject.")

    enrollment = {
        "id": str(uuid4()),
        "subject_id": subject_id,
        "student_id": student_id,
    }

    ins = (
        supabase.table("subject_enrollments").insert(enrollment).select("*").execute()
    )
    if getattr(ins, "error", None):
        logger.error("Failed to enroll student: %s", ins.error)
        raise RuntimeError("Unable to enroll student.")

    created = ins.data[0] if isinstance(ins.data, list) else ins.data
    return created


def unenroll_student(subject_id: str, student_id: str) -> None:
    resp = (
        supabase.table("subject_enrollments")
        .delete()
        .eq("subject_id", subject_id)
        .eq("student_id", student_id)
        .execute()
    )
    if getattr(resp, "error", None):
        logger.error("Failed to unenroll student %s from subject %s: %s", student_id, subject_id, resp.error)
        raise RuntimeError("Unable to unenroll student.")
    if not resp.data:
        raise ValueError("Enrollment not found.")


def get_subject_students(subject_id: str) -> list[UserResponse]:
    resp = (
        supabase.table("subject_enrollments").select("student_id").eq("subject_id", subject_id).execute()
    )
    if getattr(resp, "error", None):
        logger.error("Failed to fetch enrollments for subject %s: %s", subject_id, resp.error)
        raise RuntimeError("Unable to fetch subject students.")

    rows = resp.data or []
    student_ids = [r["student_id"] for r in rows]
    if not student_ids:
        return []

    profiles = (
        supabase.table("profiles").select("*").in_("id", student_ids).execute()
    )
    if getattr(profiles, "error", None):
        logger.error("Failed to fetch profiles for students: %s", profiles.error)
        raise RuntimeError("Unable to fetch student profiles.")

    return [
        UserResponse(
            id=p["id"],
            full_name=p["full_name"],
            email=p["email"],
            role=p.get("role"),
            department_id=p.get("department_id"),
            roll_number=p.get("roll_number"),
            phone=p.get("phone"),
            is_active=p.get("is_active", True),
            face_enrolled=p.get("face_enrolled", False),
            voice_enrolled=p.get("voice_enrolled", False),
        )
        for p in (profiles.data or [])
    ]


def get_student_subjects(student_id: str) -> list[SubjectResponse]:
    resp = (
        supabase.table("subject_enrollments").select("subject_id").eq("student_id", student_id).execute()
    )
    if getattr(resp, "error", None):
        logger.error("Failed to fetch enrollments for student %s: %s", student_id, resp.error)
        raise RuntimeError("Unable to fetch student subjects.")

    rows = resp.data or []
    subject_ids = [r["subject_id"] for r in rows]
    if not subject_ids:
        return []

    subs = (
        supabase.table("subjects").select("*").in_("id", subject_ids).execute()
    )
    if getattr(subs, "error", None):
        logger.error("Failed to fetch subjects for student %s: %s", student_id, subs.error)
        raise RuntimeError("Unable to fetch subjects.")

    return [_build_subject_response(s) for s in (subs.data or [])]
