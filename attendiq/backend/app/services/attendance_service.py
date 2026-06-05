# ============================================================
#  AttendIQ — Attendance Service
#  File: backend/app/services/attendance_service.py
#  SDK FIX: See student_service.py header for full explanation.
# ============================================================

import logging
import math
from uuid import uuid4
from datetime import datetime
from typing import Optional, List

from app.db.supabase_client import supabase
from app.models.attendance import (
    AttendanceSessionCreate,
    AttendanceSessionResponse,
    AttendanceRecordResponse,
)
from app.services.face_service import recognize_faces
from app.services.face_service import recognize_face
from app.services.voice_service import recognize_voice

logger = logging.getLogger(__name__)


def _build_session_response(row: dict) -> AttendanceSessionResponse:
    return AttendanceSessionResponse(
        id=row["id"],
        subject_id=row["subject_id"],
        faculty_id=row.get("faculty_id"),
        session_label=row.get("session_label"),
        session_date=row.get("session_date"),
        started_at=row.get("started_at"),
        completed_at=row.get("completed_at"),
        status=row.get("status", "created"),
        created_at=row.get("created_at"),
    )


def _build_record_response(row: dict) -> AttendanceRecordResponse:
    return AttendanceRecordResponse(
        id=row["id"],
        session_id=row["session_id"],
        student_id=row["student_id"],
        status=row.get("status"),
        marked_at=row.get("marked_at"),
    )


def _get_session_row(session_id: str) -> dict:
    """Helper: fetch a session row directly — used after update to return data."""
    session_id = str(session_id)
    resp = (
        supabase.table("attendance_sessions")
        .select("*")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise ValueError("Session not found.")
    return resp.data


def create_session(payload: AttendanceSessionCreate) -> AttendanceSessionResponse:
    data = payload.dict()
    data["id"] = str(uuid4())

    # ensure UUIDs are serialized to strings for Supabase
    data["subject_id"] = str(data["subject_id"])
    data["faculty_id"] = str(data["faculty_id"])
    data["department_id"] = str(data["department_id"])

    # set DB defaults for counts/status
    data.setdefault("method", "face")
    data.setdefault("status", "pending")
    data.setdefault("total_students", 0)
    data.setdefault("present_count", 0)
    data.setdefault("absent_count", 0)

    # ensure dates/datetimes are sent as ISO strings (Supabase client requires JSON-serializable values)
    if data.get("session_date") is not None:
        data["session_date"] = data["session_date"].isoformat()
    if data.get("started_at") is not None:
        data["started_at"] = data["started_at"].isoformat()
    if data.get("completed_at") is not None:
        data["completed_at"] = data["completed_at"].isoformat()

    # FIX: .insert(data).execute()  — no .select("*")
    response = supabase.table("attendance_sessions").insert(data).execute()

    if not response.data:
        logger.error("create_session: insert returned no data")
        raise RuntimeError("Unable to create session.")

    created = response.data[0] if isinstance(response.data, list) else response.data
    return _build_session_response(created)


def start_session(session_id: str) -> AttendanceSessionResponse:
    now = datetime.utcnow().isoformat()
    session_id = str(session_id)

    # FIX: .update(data).eq(...).execute()  — no .select("*").single()
    response = (
        supabase.table("attendance_sessions")
        .update({"status": "processing", "started_at": now})
        .eq("id", session_id)
        .execute()
    )
    if not response.data:
        raise ValueError("Session not found.")

    return _build_session_response(_get_session_row(session_id))


def end_session(session_id: str) -> AttendanceSessionResponse:
    now = datetime.utcnow().isoformat()
    session_id = str(session_id)

    # FIX: .update(data).eq(...).execute()  — no .select("*").single()
    response = (
        supabase.table("attendance_sessions")
        .update({"status": "completed", "completed_at": now})
        .eq("id", session_id)
        .execute()
    )
    if not response.data:
        raise ValueError("Session not found.")

    return _build_session_response(_get_session_row(session_id))


def delete_session(session_id: str) -> dict:
    session_id = str(session_id)
    supabase.table("attendance_records").delete().eq("session_id", session_id).execute()
    response = (
        supabase.table("attendance_sessions")
        .delete()
        .eq("id", session_id)
        .execute()
    )
    if not response.data:
        raise ValueError("Session not found.")
    return {"deleted": True}


def list_sessions(subject_id: Optional[str] = None) -> List[AttendanceSessionResponse]:
    query = supabase.table("attendance_sessions").select("*")
    if subject_id:
        subject_id = str(subject_id)
        query = query.eq("subject_id", subject_id)

    response = query.execute()
    rows = response.data or []
    return [_build_session_response(r) for r in rows]


def get_session(session_id: str) -> AttendanceSessionResponse:
    session_id = str(session_id)
    response = (
        supabase.table("attendance_sessions")
        .select("*")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not response.data:
        raise ValueError("Session not found.")
    return _build_session_response(response.data)


def _get_subject_enrolled_student_ids(subject_id: str) -> list[str]:
    response = (
        supabase.table("subject_enrollments")
        .select("student_id")
        .eq("subject_id", str(subject_id))
        .execute()
    )
    return [row["student_id"] for row in (response.data or [])]


def _get_student_names(student_ids: list[str]) -> dict[str, str]:
    if not student_ids:
        return {}

    response = (
        supabase.table("profiles")
        .select("id, full_name")
        .in_("id", student_ids)
        .execute()
    )
    return {row["id"]: row.get("full_name", "") for row in (response.data or [])}


def group_face_checkin(session_id: str, image_bytes: bytes) -> dict:
    session_id = str(session_id)
    session = _get_session_row(session_id)
    subject_id = session.get("subject_id")
    if not subject_id:
        raise ValueError("Attendance session does not have an associated subject.")

    enrolled_student_ids = _get_subject_enrolled_student_ids(subject_id)
    if not enrolled_student_ids:
        return {
            "present_count": 0,
            "absent_count": 0,
            "attendance_percentage": 0.0,
            "present_students": [],
            "absent_students": [],
        }

    student_names = _get_student_names(enrolled_student_ids)
    recognized = recognize_faces(image_bytes=image_bytes, student_ids=enrolled_student_ids)

    present_students = []
    present_set = set()
    for match in recognized:
        student_id = match.get("student_id")
        if not student_id or student_id in present_set:
            continue
        present_set.add(student_id)
        present_students.append({
            "student_id": student_id,
            "name": student_names.get(student_id, "Unknown"),
            "confidence": float(match.get("confidence", 0.0)),
        })
        mark_attendance(
            session_id=session_id,
            student_id=str(student_id),
            attendance_status="present",
            method="face",
            confidence=float(match.get("confidence", 0.0)),
        )

    absent_students = [
        {"student_id": sid, "name": student_names.get(sid, "Unknown")}
        for sid in enrolled_student_ids
        if sid not in present_set
    ]

    total_students = len(enrolled_student_ids)
    attendance_percentage = round((len(present_students) / total_students) * 100.0, 2) if total_students else 0.0

    return {
        "present_count": len(present_students),
        "absent_count": len(absent_students),
        "attendance_percentage": attendance_percentage,
        "present_students": present_students,
        "absent_students": absent_students,
    }


def face_checkin(session_id: str, image_bytes: bytes) -> dict:
    session_id = str(session_id)
    try:
        recognition = recognize_face(image_bytes)
    except ValueError:
        return {"attendance_marked": False, "reason": "face_not_recognized"}

    if not recognition.get("matched"):
        return {"attendance_marked": False, "reason": "face_not_recognized"}

    student_id = str(recognition["student_id"])
    confidence = float(recognition.get("confidence", 0.0))

    mark_attendance(
        session_id=session_id,
        student_id=student_id,
        attendance_status="present",
        method="face",
        confidence=confidence,
    )

    return {
        "attendance_marked": True,
        "student_id": student_id,
        "confidence": confidence,
        "session_id": session_id,
    }


def voice_checkin(session_id: str, audio_bytes: bytes, original_filename: str = "recording.wav") -> dict:
    session_id = str(session_id)
    recognition = recognize_voice(audio_bytes=audio_bytes, original_filename=original_filename)

    if not recognition.get("matched"):
        return {"attendance_marked": False, "reason": "voice_not_recognized"}

    student_id = str(recognition["student_id"])
    confidence = float(recognition.get("confidence", 0.0))
    print(f"DEBUG voice_checkin confidence={confidence}")

    if math.isnan(confidence) or math.isinf(confidence):
        confidence = 0.0

    confidence = max(0.0, min(confidence, 1.0))

    mark_attendance(
        session_id=session_id,
        student_id=student_id,
        attendance_status="present",
        method="voice",
        confidence=confidence,
    )

    return {
        "attendance_marked": True,
        "student_id": student_id,
        "confidence": confidence,
        "session_id": session_id,
    }


def mark_attendance(
    session_id: str,
    student_id: str,
    attendance_status: str,
    method: str = "face",
    confidence: float = 1.0,
) -> AttendanceRecordResponse:
    # normalize IDs to strings for Supabase
    session_id = str(session_id)
    student_id = str(student_id)

    # validate session and capture related subject/department IDs
    s = (
        supabase.table("attendance_sessions")
        .select("id,subject_id,department_id")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not s.data:
        raise ValueError("Session not found.")

    subject_id = s.data.get("subject_id")
    department_id = s.data.get("department_id")

    now = datetime.utcnow().isoformat()

    # check existing record
    exist = (
        supabase.table("attendance_records")
        .select("id")
        .eq("session_id", session_id)
        .eq("student_id", student_id)
        .execute()
    )

    confidence = float(confidence)

    if exist.data:
        # UPDATE existing — FIX: no .select("*").single() after .eq()
        supabase.table("attendance_records").update(
            {
                "status": attendance_status,
                "marked_at": now,
                "method": method,
                "confidence": confidence,
            }
        ).eq("session_id", session_id).eq("student_id", student_id).execute()

        # Re-fetch updated record
        updated = (
            supabase.table("attendance_records")
            .select("*")
            .eq("session_id", session_id)
            .eq("student_id", student_id)
            .single()
            .execute()
        )
        return _build_record_response(updated.data)
    else:
        record = {
            "id":             str(uuid4()),
            "session_id":    session_id,
            "student_id":    student_id,
            "subject_id":    subject_id,
            "department_id": department_id,
            "status":        attendance_status,
            "method":        method,
            "confidence":    confidence,
            "marked_at":     now,
        }
        # FIX: .insert(data).execute()  — no .select("*")
        resp = supabase.table("attendance_records").insert(record).execute()

        if not resp.data:
            logger.error("mark_attendance: insert returned no data")
            raise RuntimeError("Unable to mark attendance.")

        created = resp.data[0] if isinstance(resp.data, list) else resp.data
        return _build_record_response(created)


def get_session_attendance(session_id: str) -> List[AttendanceRecordResponse]:
    session_id = str(session_id)
    resp = (
        supabase.table("attendance_records")
        .select("*")
        .eq("session_id", session_id)
        .execute()
    )
    rows = resp.data or []
    return [_build_record_response(r) for r in rows]


def get_student_history(student_id: str) -> List[dict]:
    """Return attendance history for a given student (newest first).

    Returns a list of dicts matching the frontend contract:
    {
      "attendance_id": "...",
      "session_id": "...",
      "session_name": "...",
      "subject_name": "...",
      "attendance_status": "present",
      "method": "face",
      "confidence": 0.95,
      "marked_at": "...",
      "session_date": "..."
    }
    """
    student_id = str(student_id)
    resp = (
        supabase.table("attendance_records")
        .select("*")
        .eq("student_id", student_id)
        .order("marked_at", desc=True)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return []

    # collect session ids
    session_ids = list({r.get("session_id") for r in rows if r.get("session_id")})

    sessions_map = {}
    if session_ids:
        sresp = (
            supabase.table("attendance_sessions")
            .select("id,session_label,session_date,subject_id")
            .in_("id", session_ids)
            .execute()
        )
        for s in (sresp.data or []):
            sessions_map[s["id"]] = s

    # collect subject ids from sessions
    subject_ids = list({sessions_map[sid].get("subject_id") for sid in sessions_map if sessions_map[sid].get("subject_id")})
    subjects_map = {}
    if subject_ids:
        subresp = (
            supabase.table("subjects")
            .select("id,name")
            .in_("id", subject_ids)
            .execute()
        )
        for sub in (subresp.data or []):
            subjects_map[sub["id"]] = sub.get("name")

    result = []
    for r in rows:
        sid = r.get("session_id")
        session = sessions_map.get(sid) or {}
        subject_name = subjects_map.get(session.get("subject_id")) if session else None
        result.append({
            "attendance_id": r.get("id"),
            "session_id": sid,
            "session_name": session.get("session_label"),
            "subject_name": subject_name,
            "attendance_status": r.get("status"),
            "method": r.get("method"),
            "confidence": float(r.get("confidence")) if r.get("confidence") is not None else None,
            "marked_at": r.get("marked_at"),
            "session_date": session.get("session_date"),
        })

    return result