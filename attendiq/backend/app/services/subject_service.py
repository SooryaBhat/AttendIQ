# ============================================================
#  AttendIQ — Subject Service  (fixed)
#  Root causes fixed:
#  1. Enrollment table is student_subjects (NOT subject_enrollments)
#  2. Subject join code column is join_code (NOT code)
#  3. subjects.code is a separate unique identifier
# ============================================================

import logging
import random
import string
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
        semester=row.get("semester"),
        credits=row.get("credits"),
        created_at=row.get("created_at"),
    )


def _generate_join_code(length: int = 6) -> str:
    """Generate a unique alphanumeric join code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def _unique_join_code() -> str:
    for _ in range(10):
        code = _generate_join_code()
        check = supabase.table("subjects").select("id").eq("join_code", code).execute()
        if not (check.data or []):
            return code
    raise RuntimeError("Could not generate unique join code. Please try again.")


def list_subjects() -> list:
    response = supabase.table("subjects").select("*").execute()
    return [_build_subject_response(r) for r in (response.data or [])]


def get_subject(subject_id: str) -> SubjectResponse:
    response = (
        supabase.table("subjects").select("*").eq("id", subject_id).single().execute()
    )
    if not response.data:
        raise ValueError("Subject not found.")
    return _build_subject_response(response.data)


def create_subject(payload: SubjectCreate) -> SubjectResponse:
    data = payload.dict()
    data["id"] = str(uuid4())
    if data.get("faculty_id") is not None:
        data["faculty_id"] = str(data["faculty_id"])
    if data.get("department_id") is not None:
        data["department_id"] = str(data["department_id"])
    # Auto-generate join_code if schema requires it
    data["join_code"] = _unique_join_code()

    response = supabase.table("subjects").insert(data).execute()
    if not response.data:
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

    response = (
        supabase.table("subjects").update(update_data).eq("id", subject_id).execute()
    )
    if not response.data:
        raise ValueError("Subject not found.")
    return get_subject(subject_id)


def delete_subject(subject_id: str) -> None:
    supabase.table("subjects").delete().eq("id", subject_id).execute()


# ── Enrollment (table: student_subjects) ─────────────────────────────────────

def enroll_student(subject_id: str, student_id: str) -> dict:
    subject_id = str(subject_id)
    student_id = str(student_id)

    # Check subject exists
    sr = supabase.table("subjects").select("id").eq("id", subject_id).execute()
    if not sr.data:
        raise ValueError("Subject not found.")

    # Check student exists
    pr = supabase.table("profiles").select("id").eq("id", student_id).execute()
    if not pr.data:
        raise ValueError("Student not found.")

    # Check duplicate
    exist = (
        supabase.table("student_subjects")
        .select("id")
        .eq("subject_id", subject_id)
        .eq("student_id", student_id)
        .execute()
    )
    if exist.data:
        raise ValueError("Student already enrolled in this subject.")

    enrollment = {"id": str(uuid4()), "subject_id": subject_id, "student_id": student_id}
    ins = supabase.table("student_subjects").insert(enrollment).execute()
    if not ins.data:
        raise RuntimeError("Unable to enroll student.")
    return ins.data[0] if isinstance(ins.data, list) else ins.data


def unenroll_student(subject_id: str, student_id: str) -> None:
    supabase.table("student_subjects").delete().eq("subject_id", subject_id).eq(
        "student_id", student_id).execute()


def get_subject_students(subject_id: str) -> list:
    resp = (
        supabase.table("student_subjects")
        .select("student_id")
        .eq("subject_id", subject_id)
        .execute()
    )
    student_ids = [r["student_id"] for r in (resp.data or [])]
    if not student_ids:
        return []
    profiles = supabase.table("profiles").select("*").in_("id", student_ids).execute()
    return [
        UserResponse(
            id=p["id"], full_name=p["full_name"], email=p["email"],
            role=p.get("role"), department_id=p.get("department_id"),
            roll_number=p.get("roll_number"), phone=p.get("phone"),
            is_active=p.get("is_active", True),
            face_enrolled=p.get("face_enrolled", False),
            voice_enrolled=p.get("voice_enrolled", False),
        )
        for p in (profiles.data or [])
    ]


def get_student_subjects(student_id: str) -> list:
    resp = (
        supabase.table("student_subjects")
        .select("subject_id")
        .eq("student_id", student_id)
        .execute()
    )
    subject_ids = [r["subject_id"] for r in (resp.data or [])]
    if not subject_ids:
        return []
    subs = supabase.table("subjects").select("*").in_("id", subject_ids).execute()
    return [_build_subject_response(s) for s in (subs.data or [])]


def find_subject_by_join_code(join_code: str) -> Optional[dict]:
    """Find subject using the join_code column (not the code column)."""
    resp = (
        supabase.table("subjects")
        .select("*")
        .eq("join_code", join_code.strip().upper())
        .execute()
    )
    rows = resp.data or []
    return rows[0] if rows else None
