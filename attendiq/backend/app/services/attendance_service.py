import logging
from uuid import uuid4
from datetime import datetime
from typing import Optional, List

from app.db.supabase_client import supabase
from app.models.attendance import (
    AttendanceSessionCreate,
    AttendanceSessionResponse,
    AttendanceSessionUpdate,
    AttendanceRecordResponse,
)

logger = logging.getLogger(__name__)


def _build_session_response(row: dict) -> AttendanceSessionResponse:
    return AttendanceSessionResponse(
        id=row["id"],
        subject_id=row["subject_id"],
        faculty_id=row.get("faculty_id"),
        session_name=row.get("session_name"),
        start_time=row.get("start_time"),
        end_time=row.get("end_time"),
        status=row.get("status", "created"),
        created_at=row.get("created_at"),
    )


def _build_record_response(row: dict) -> AttendanceRecordResponse:
    return AttendanceRecordResponse(
        id=row["id"],
        session_id=row["session_id"],
        student_id=row["student_id"],
        attendance_status=row.get("attendance_status"),
        marked_at=row.get("marked_at"),
    )


def create_session(payload: AttendanceSessionCreate) -> AttendanceSessionResponse:
    data = payload.dict()
    data["id"] = str(uuid4())
    data["status"] = "created"

    response = (
        supabase.table("attendance_sessions").insert(data).select("*").execute()
    )
    if getattr(response, "error", None):
        logger.error("Failed to create session: %s", response.error)
        raise RuntimeError("Unable to create session.")

    created = response.data[0] if isinstance(response.data, list) else response.data
    return _build_session_response(created)


def start_session(session_id: str) -> AttendanceSessionResponse:
    now = datetime.utcnow().isoformat()
    response = (
        supabase.table("attendance_sessions")
        .update({"status": "started", "start_time": now})
        .eq("id", session_id)
        .select("*")
        .single()
        .execute()
    )
    if getattr(response, "error", None):
        logger.error("Failed to start session %s: %s", session_id, response.error)
        raise RuntimeError("Unable to start session.")
    if not response.data:
        raise ValueError("Session not found.")
    return _build_session_response(response.data)


def end_session(session_id: str) -> AttendanceSessionResponse:
    now = datetime.utcnow().isoformat()
    response = (
        supabase.table("attendance_sessions")
        .update({"status": "ended", "end_time": now})
        .eq("id", session_id)
        .select("*")
        .single()
        .execute()
    )
    if getattr(response, "error", None):
        logger.error("Failed to end session %s: %s", session_id, response.error)
        raise RuntimeError("Unable to end session.")
    if not response.data:
        raise ValueError("Session not found.")
    return _build_session_response(response.data)


def list_sessions(subject_id: Optional[str] = None) -> List[AttendanceSessionResponse]:
    query = supabase.table("attendance_sessions").select("*")
    if subject_id:
        query = query.eq("subject_id", subject_id)

    response = query.execute()
    if getattr(response, "error", None):
        logger.error("Failed to list sessions: %s", response.error)
        raise RuntimeError("Unable to fetch sessions.")

    rows = response.data or []
    return [_build_session_response(r) for r in rows]


def get_session(session_id: str) -> AttendanceSessionResponse:
    response = (
        supabase.table("attendance_sessions").select("*").eq("id", session_id).single().execute()
    )
    if getattr(response, "error", None):
        logger.error("Failed to fetch session %s: %s", session_id, response.error)
        raise RuntimeError("Unable to fetch session.")
    if not response.data:
        raise ValueError("Session not found.")
    return _build_session_response(response.data)


def mark_attendance(session_id: str, student_id: str, attendance_status: str) -> AttendanceRecordResponse:
    # validate session exists
    s = supabase.table("attendance_sessions").select("*").eq("id", session_id).single().execute()
    if getattr(s, "error", None):
        logger.error("Failed to validate session %s: %s", session_id, s.error)
        raise RuntimeError("Unable to validate session.")
    if not s.data:
        raise ValueError("Session not found.")

    # check existing record
    exist = (
        supabase.table("attendance_records")
        .select("*")
        .eq("session_id", session_id)
        .eq("student_id", student_id)
        .execute()
    )
    if getattr(exist, "error", None):
        logger.error("Failed to check attendance record: %s", exist.error)
        raise RuntimeError("Unable to check attendance record.")

    now = datetime.utcnow().isoformat()
    if exist.data:
        # update
        resp = (
            supabase.table("attendance_records")
            .update({"attendance_status": attendance_status, "marked_at": now})
            .eq("session_id", session_id)
            .eq("student_id", student_id)
            .select("*")
            .single()
            .execute()
        )
        if getattr(resp, "error", None):
            logger.error("Failed to update attendance record: %s", resp.error)
            raise RuntimeError("Unable to update attendance record.")
        return _build_record_response(resp.data)
    else:
        record = {
            "id": str(uuid4()),
            "session_id": session_id,
            "student_id": student_id,
            "attendance_status": attendance_status,
            "marked_at": now,
        }
        resp = supabase.table("attendance_records").insert(record).select("*").execute()
        if getattr(resp, "error", None):
            logger.error("Failed to insert attendance record: %s", resp.error)
            raise RuntimeError("Unable to mark attendance.")
        created = resp.data[0] if isinstance(resp.data, list) else resp.data
        return _build_record_response(created)


def get_session_attendance(session_id: str) -> List[AttendanceRecordResponse]:
    resp = (
        supabase.table("attendance_records").select("*").eq("session_id", session_id).execute()
    )
    if getattr(resp, "error", None):
        logger.error("Failed to fetch attendance records for session %s: %s", session_id, resp.error)
        raise RuntimeError("Unable to fetch attendance records.")

    rows = resp.data or []
    return [_build_record_response(r) for r in rows]
