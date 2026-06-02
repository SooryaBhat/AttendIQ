# ============================================================
#  AttendIQ — Subject Service
#  File: backend/app/services/subject_service.py
#  SDK FIX: See student_service.py header for full explanation.
# ============================================================

import logging
from uuid import uuid4
from typing import Optional

from app.db.supabase_client import supabase
from app.models.subject import SubjectCreate, SubjectResponse, SubjectUpdate
from app.models.user import UserResponse

logger = logging.getLogger(__name__)


def _build_subject_response(row: dict) -> SubjectResponse:
    return SubjectResponse(
        id=row["id"],
        name=row["name"],
        code=row["code"],
        faculty_id=row.get("faculty_id"),
        department_id=row.get("department_id"),
        semester=row["semester"],
        credits=row["credits"],
        created_at=row.get("created_at"),
    )


def list_subjects() -> list[SubjectResponse]:
    response = supabase.table("subjects").select("*").execute()
    rows = response.data or []
    return [_build_subject_response(r) for r in rows]


def get_subject(subject_id: str) -> SubjectResponse:
    response = (
        supabase.table("subjects")
        .select("*")
        .eq("id", subject_id)
        .single()
        .execute()
    )
    if not response.data:
        raise ValueError("Subject not found.")
    return _build_subject_response(response.data)


def create_subject(payload: SubjectCreate) -> SubjectResponse:
    subject_data = payload.dict()
    subject_data["id"] = str(uuid4())
    subject_data["semester"] = payload.semester
    subject_data["credits"] = payload.credits
    if subject_data.get("faculty_id") is not None:
        subject_data["faculty_id"] = str(subject_data["faculty_id"])
    if subject_data.get("department_id") is not None:
        subject_data["department_id"] = str(subject_data["department_id"])

    # FIX: .insert(data).execute()  — no .select("*") chaining
    response = supabase.table("subjects").insert(subject_data).execute()

    if not response.data:
        logger.error("create_subject: insert returned no data")
        raise RuntimeError("Unable to create subject.")

    created = response.data[0] if isinstance(response.data, list) else response.data
    return _build_subject_response(created)


def update_subject(subject_id: str, payload: SubjectUpdate) -> SubjectResponse:
    update_data = payload.dict(exclude_unset=True)
    if update_data.get("faculty_id") is not None:
        update_data["faculty_id"] = str(update_data["faculty_id"])
    if update_data.get("department_id") is not None:
        update_data["department_id"] = str(update_data["department_id"])
    if not update_data:
        raise ValueError("No updates provided.")

    # FIX: .update(data).eq(...).execute()  — no .select("*").single()
    response = (
        supabase.table("subjects")
        .update(update_data)
        .eq("id", subject_id)
        .execute()
    )
    if not response.data:
        raise ValueError("Subject not found.")

    return get_subject(subject_id)


def delete_subject(subject_id: str) -> None:
    check = (
        supabase.table("subjects")
        .select("id")
        .eq("id", subject_id)
        .single()
        .execute()
    )
    if not check.data:
        raise ValueError("Subject not found.")

    # FIX: .delete().eq(...).execute()  — no .select() chaining
    supabase.table("subjects").delete().eq("id", subject_id).execute()


# ── Enrollment helpers ────────────────────────────────────────

def enroll_student(subject_id: str, student_id: str) -> dict:
    subject_id = str(subject_id)
    student_id = str(student_id)
    # validate subject
    resp = supabase.table("subjects").select("id").eq("id", subject_id).single().execute()
    if not resp.data:
        raise ValueError("Subject not found.")

    # validate student
    sresp = supabase.table("profiles").select("id").eq("id", student_id).single().execute()
    if not sresp.data:
        raise ValueError("Student not found.")

    # check duplicate
    exist = (
        supabase.table("subject_enrollments")
        .select("id")
        .eq("subject_id", subject_id)
        .eq("student_id", student_id)
        .execute()
    )
    if exist.data:
        raise ValueError("Student already enrolled in this subject.")

    enrollment = {
        "id":         str(uuid4()),
        "subject_id": subject_id,
        "student_id": student_id,
    }

    # FIX: .insert(data).execute()  — no .select("*")
    ins = supabase.table("subject_enrollments").insert(enrollment).execute()

    if not ins.data:
        logger.error("enroll_student: insert returned no data")
        raise RuntimeError("Unable to enroll student.")

    return ins.data[0] if isinstance(ins.data, list) else ins.data


def unenroll_student(subject_id: str, student_id: str) -> None:
    check = (
        supabase.table("subject_enrollments")
        .select("id")
        .eq("subject_id", subject_id)
        .eq("student_id", student_id)
        .execute()
    )
    if not check.data:
        raise ValueError("Enrollment not found.")

    # FIX: .delete().eq(...).execute()
    supabase.table("subject_enrollments").delete().eq("subject_id", subject_id).eq("student_id", student_id).execute()


def get_subject_students(subject_id: str) -> list[UserResponse]:
    resp = (
        supabase.table("subject_enrollments")
        .select("student_id")
        .eq("subject_id", subject_id)
        .execute()
    )
    rows = resp.data or []
    student_ids = [r["student_id"] for r in rows]
    if not student_ids:
        return []

    profiles = supabase.table("profiles").select("*").in_("id", student_ids).execute()
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
        supabase.table("subject_enrollments")
        .select("subject_id")
        .eq("student_id", student_id)
        .execute()
    )
    rows = resp.data or []
    subject_ids = [r["subject_id"] for r in rows]
    if not subject_ids:
        return []

    subs = supabase.table("subjects").select("*").in_("id", subject_ids).execute()
    return [_build_subject_response(s) for s in (subs.data or [])]