# ============================================================
#  AttendIQ — Attendance Service  (complete rewrite)
#  Root causes fixed:
#  1. attendance_sessions has NO department_id / method columns
#     → removed from insert payload
#  2. attendance_records has no method/confidence/subject_id cols
#     → insert only columns that exist in schema
#  3. start/end session uses wrong column name (completed_at vs end_time)
#  4. list_sessions must filter by faculty when needed
# ============================================================

import logging
from uuid import uuid4
from datetime import datetime
from typing import Optional, List

from app.db.supabase_client import supabase
from app.models.attendance import (
    AttendanceSessionCreate,
    AttendanceSessionResponse,
    AttendanceRecordResponse,
)

logger = logging.getLogger(__name__)

# ── Schema-safe column sets ───────────────────────────────────────────────────
# attendance_sessions actual columns (from schema.sql):
#   id, subject_id, faculty_id, session_date, start_time, end_time,
#   session_label, status, qr_code, created_at, updated_at
#
# attendance_records actual columns (from schema.sql):
#   id, session_id, student_id, status, marked_by, marked_at,
#   face_match_score, voice_match_score, created_at


def _build_session_response(row: dict) -> AttendanceSessionResponse:
    return AttendanceSessionResponse(
        id=row["id"],
        subject_id=row["subject_id"],
        faculty_id=row.get("faculty_id"),
        session_label=row.get("session_label") or "",
        session_date=row.get("session_date"),
        started_at=row.get("start_time"),       # schema uses start_time
        completed_at=row.get("end_time"),        # schema uses end_time
        status=row.get("status", "scheduled"),
        created_at=row.get("created_at"),
    )


def _build_record_response(row: dict) -> AttendanceRecordResponse:
    return AttendanceRecordResponse(
        id=row["id"],
        session_id=row["session_id"],
        student_id=row["student_id"],
        status=row.get("status", "unmarked"),
        marked_at=row.get("marked_at"),
    )


def _get_session_row(session_id: str) -> dict:
    resp = (
        supabase.table("attendance_sessions")
        .select("*")
        .eq("id", session_id)
        .single()
        .execute()
    )
    if not resp.data:
        raise ValueError(f"Session {session_id} not found.")
    return resp.data


def create_session(payload: AttendanceSessionCreate) -> AttendanceSessionResponse:
    """
    Insert only columns that exist in the DB schema.
    Ignore: department_id, method, total_students, present_count,
            absent_count, processing_log, started_at, completed_at.
    """
    data = {
        "id":            str(uuid4()),
        "subject_id":    str(payload.subject_id),
        "faculty_id":    str(payload.faculty_id),
        "session_date":  payload.session_date.isoformat() if payload.session_date else None,
        "session_label": payload.session_label,
        "status":        payload.status or "scheduled",
    }

    response = supabase.table("attendance_sessions").insert(data).execute()

    if not response.data:
        logger.error("create_session: insert returned no data — %s", response)
        raise RuntimeError("Unable to create session — database insert returned no data.")

    created = response.data[0] if isinstance(response.data, list) else response.data
    return _build_session_response(created)


def start_session(session_id: str) -> AttendanceSessionResponse:
    now = datetime.utcnow().strftime("%H:%M:%S")  # start_time is TIME type
    session_id = str(session_id)

    response = (
        supabase.table("attendance_sessions")
        .update({"status": "active", "start_time": now})
        .eq("id", session_id)
        .execute()
    )
    if not response.data:
        raise ValueError("Session not found or could not be started.")

    return _build_session_response(_get_session_row(session_id))


def end_session(session_id: str) -> AttendanceSessionResponse:
    now = datetime.utcnow().strftime("%H:%M:%S")  # end_time is TIME type
    session_id = str(session_id)

    response = (
        supabase.table("attendance_sessions")
        .update({"status": "completed", "end_time": now})
        .eq("id", session_id)
        .execute()
    )
    if not response.data:
        raise ValueError("Session not found or could not be ended.")

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
    return {"deleted": True}


def list_sessions(
    subject_id: Optional[str] = None,
    faculty_id: Optional[str] = None,
) -> List[AttendanceSessionResponse]:
    query = supabase.table("attendance_sessions").select("*")
    if subject_id:
        query = query.eq("subject_id", str(subject_id))
    if faculty_id:
        query = query.eq("faculty_id", str(faculty_id))

    response = query.order("created_at", desc=True).execute()
    rows = response.data or []
    return [_build_session_response(r) for r in rows]


def get_session(session_id: str) -> AttendanceSessionResponse:
    return _build_session_response(_get_session_row(str(session_id)))


def _get_enrolled_student_ids(subject_id: str) -> list:
    """Query student_subjects (the actual table in schema.sql)."""
    resp = (
        supabase.table("student_subjects")
        .select("student_id")
        .eq("subject_id", str(subject_id))
        .execute()
    )
    return [r["student_id"] for r in (resp.data or [])]


def _get_student_names(student_ids: list) -> dict:
    if not student_ids:
        return {}
    resp = (
        supabase.table("profiles")
        .select("id, full_name")
        .in_("id", student_ids)
        .execute()
    )
    return {r["id"]: r.get("full_name", "") for r in (resp.data or [])}


def mark_attendance(
    session_id: str,
    student_id: str,
    attendance_status: str,
    method: str = "manual",
    confidence: float = 1.0,
) -> AttendanceRecordResponse:
    """
    Insert/update an attendance record.
    Only uses columns that exist in schema:
      id, session_id, student_id, status, marked_by, marked_at,
      face_match_score, voice_match_score
    """
    session_id = str(session_id)
    student_id = str(student_id)
    now = datetime.utcnow().isoformat()

    # Map method → score column
    face_score  = float(confidence) if method == "face"  else None
    voice_score = float(confidence) if method == "voice" else None

    # Check existing
    exist = (
        supabase.table("attendance_records")
        .select("id")
        .eq("session_id", session_id)
        .eq("student_id", student_id)
        .execute()
    )

    if exist.data:
        update_data = {
            "status":    attendance_status,
            "marked_at": now,
            "marked_by": method,
        }
        if face_score  is not None: update_data["face_match_score"]  = face_score
        if voice_score is not None: update_data["voice_match_score"] = voice_score

        supabase.table("attendance_records").update(update_data).eq(
            "session_id", session_id).eq("student_id", student_id).execute()

        updated = (
            supabase.table("attendance_records")
            .select("*").eq("session_id", session_id).eq("student_id", student_id)
            .single().execute()
        )
        return _build_record_response(updated.data)
    else:
        record = {
            "id":         str(uuid4()),
            "session_id": session_id,
            "student_id": student_id,
            "status":     attendance_status,
            "marked_by":  method,
            "marked_at":  now,
        }
        if face_score  is not None: record["face_match_score"]  = face_score
        if voice_score is not None: record["voice_match_score"] = voice_score

        resp = supabase.table("attendance_records").insert(record).execute()
        if not resp.data:
            raise RuntimeError("Unable to mark attendance — insert returned no data.")
        created = resp.data[0] if isinstance(resp.data, list) else resp.data
        return _build_record_response(created)


def get_session_attendance(session_id: str) -> List[AttendanceRecordResponse]:
    resp = (
        supabase.table("attendance_records")
        .select("*")
        .eq("session_id", str(session_id))
        .execute()
    )
    return [_build_record_response(r) for r in (resp.data or [])]


def get_student_history(student_id: str) -> list:
    """
    Rich attendance history for a student.
    Joins records → sessions → subjects in Python (Supabase free tier has no joins).
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

    session_ids = list({r["session_id"] for r in rows if r.get("session_id")})
    sessions_map = {}
    if session_ids:
        sr = (
            supabase.table("attendance_sessions")
            .select("id, session_label, session_date, subject_id")
            .in_("id", session_ids)
            .execute()
        )
        sessions_map = {s["id"]: s for s in (sr.data or [])}

    subject_ids = list({s.get("subject_id") for s in sessions_map.values() if s.get("subject_id")})
    subjects_map = {}
    if subject_ids:
        sub_r = (
            supabase.table("subjects")
            .select("id, name")
            .in_("id", subject_ids)
            .execute()
        )
        subjects_map = {s["id"]: s.get("name") for s in (sub_r.data or [])}

    result = []
    for r in rows:
        sid = r.get("session_id")
        session = sessions_map.get(sid, {})
        result.append({
            "attendance_id":    r.get("id"),
            "session_id":       sid,
            "session_name":     session.get("session_label"),
            "subject_name":     subjects_map.get(session.get("subject_id")),
            "attendance_status": r.get("status"),
            "method":           r.get("marked_by"),
            "confidence":       r.get("face_match_score") or r.get("voice_match_score"),
            "marked_at":        r.get("marked_at"),
            "session_date":     session.get("session_date"),
        })
    return result


# ── Biometric check-in wrappers (lazy import so deploy works without ML libs) ─

def face_checkin(session_id: str, image_bytes: bytes) -> dict:
    try:
        from app.services.face_service import recognize_face
        recognition = recognize_face(image_bytes)
    except ImportError:
        return {"attendance_marked": False, "reason": "Face recognition not available on this deployment."}
    except ValueError:
        return {"attendance_marked": False, "reason": "No face detected in image."}

    if not recognition.get("matched"):
        return {"attendance_marked": False, "reason": "Face not recognized."}

    student_id = str(recognition["student_id"])
    confidence = float(recognition.get("confidence", 0.0))
    mark_attendance(session_id, student_id, "present", "face", confidence)
    return {"attendance_marked": True, "student_id": student_id, "confidence": confidence, "session_id": session_id}


def voice_checkin(session_id: str, audio_bytes: bytes, original_filename: str = "recording.wav") -> dict:
    try:
        from app.services.voice_service import recognize_voice
        recognition = recognize_voice(audio_bytes=audio_bytes, original_filename=original_filename)
    except ImportError:
        return {"attendance_marked": False, "reason": "Voice recognition not available on this deployment."}

    if not recognition.get("matched"):
        return {"attendance_marked": False, "reason": "Voice not recognized."}

    student_id = str(recognition["student_id"])
    confidence = float(recognition.get("confidence", 0.0))
    import math
    if math.isnan(confidence) or math.isinf(confidence):
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))
    mark_attendance(session_id, student_id, "present", "voice", confidence)
    return {"attendance_marked": True, "student_id": student_id, "confidence": confidence, "session_id": session_id}


def group_face_checkin(session_id: str, image_bytes: bytes) -> dict:
    try:
        from app.services.face_service import recognize_faces
    except ImportError:
        return {"present_count": 0, "absent_count": 0, "attendance_percentage": 0.0,
                "present_students": [], "absent_students": [],
                "error": "Face recognition not available on this deployment."}

    session_id = str(session_id)
    session = _get_session_row(session_id)
    subject_id = session.get("subject_id")

    enrolled = _get_enrolled_student_ids(subject_id) if subject_id else []
    names = _get_student_names(enrolled)

    recognized = recognize_faces(image_bytes=image_bytes, student_ids=enrolled)

    present_set = set()
    present_list = []
    for match in recognized:
        sid = match.get("student_id")
        if sid and sid not in present_set:
            present_set.add(sid)
            present_list.append({"student_id": sid, "name": names.get(sid, "Unknown"),
                                  "confidence": float(match.get("confidence", 0.0))})
            mark_attendance(session_id, sid, "present", "face", float(match.get("confidence", 0.0)))

    absent_list = [{"student_id": sid, "name": names.get(sid, "Unknown")}
                   for sid in enrolled if sid not in present_set]
    total = len(enrolled)
    pct = round(len(present_list) / total * 100, 2) if total else 0.0
    return {"present_count": len(present_list), "absent_count": len(absent_list),
            "attendance_percentage": pct, "present_students": present_list, "absent_students": absent_list}
