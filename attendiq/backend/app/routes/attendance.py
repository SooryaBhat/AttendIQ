# ============================================================
#  AttendIQ — Attendance Routes  (fixed)
#  Fixed:
#  1. Removed circular import of _ranked_students from analytics
#  2. get_attendance_sessions now accepts faculty_id filter
#  3. All error responses are human-readable strings, not raw objects
# ============================================================

import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel

from app.dependencies.auth import get_current_user
from app.models.user import UserResponse
from app.models.attendance import (
    AttendanceSessionCreate, AttendanceSessionResponse,
    AttendanceSessionUpdate, AttendanceRecordResponse,
    AttendanceGroupFaceCheckinResponse, AttendanceVoiceCheckinResponse,
    StudentAttendanceHistoryItem, AttendanceFaceCheckinResponse,
)
from app.services.attendance_service import (
    create_session, start_session, end_session, delete_session,
    list_sessions, get_session, mark_attendance,
    get_session_attendance, get_student_history,
    face_checkin, voice_checkin, group_face_checkin,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attendance", tags=["attendance"])

_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/bmp", "image/webp"}
_AUDIO_TYPES = {"audio/wav", "audio/wave", "audio/x-wav", "audio/mpeg", "audio/mp3",
                "audio/ogg", "audio/flac", "audio/x-flac", "audio/webm"}


def _check_image(file: UploadFile):
    if file.content_type not in _IMAGE_TYPES:
        raise HTTPException(415, f"Unsupported image type '{file.content_type}'. Use JPEG, PNG, BMP, or WEBP.")


def _check_audio(file: UploadFile):
    if file.content_type not in _AUDIO_TYPES:
        raise HTTPException(415, f"Unsupported audio type '{file.content_type}'. Use WAV, MP3, OGG, FLAC, or WEBM.")


# ── Sessions ──────────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=AttendanceSessionResponse, status_code=201)
def create_attendance_session(
    payload: AttendanceSessionCreate,
    current_user: UserResponse = Depends(get_current_user),
):
    try:
        return create_session(payload)
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        logger.exception("create_session error: %s", exc)
        raise HTTPException(400, f"Could not create session: {exc}") from exc


@router.get("/sessions", response_model=List[AttendanceSessionResponse])
def get_attendance_sessions(
    subject_id:  Optional[UUID] = None,
    faculty_id:  Optional[UUID] = None,
    current_user: UserResponse  = Depends(get_current_user),
):
    try:
        return list_sessions(
            subject_id=str(subject_id) if subject_id else None,
            faculty_id=str(faculty_id) if faculty_id else None,
        )
    except Exception as exc:
        logger.exception("list_sessions error: %s", exc)
        raise HTTPException(500, f"Could not load sessions: {exc}") from exc


@router.get("/sessions/{session_id}", response_model=AttendanceSessionResponse)
def get_attendance_session(session_id: UUID, current_user: UserResponse = Depends(get_current_user)):
    try:
        return get_session(str(session_id))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Could not load session: {exc}") from exc


@router.put("/sessions/{session_id}/start", response_model=AttendanceSessionResponse)
def start_attendance_session(session_id: UUID, current_user: UserResponse = Depends(get_current_user)):
    try:
        return start_session(str(session_id))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        logger.exception("start_session error: %s", exc)
        raise HTTPException(400, f"Could not start session: {exc}") from exc


@router.put("/sessions/{session_id}/end", response_model=AttendanceSessionResponse)
def end_attendance_session(session_id: UUID, current_user: UserResponse = Depends(get_current_user)):
    try:
        return end_session(str(session_id))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        logger.exception("end_session error: %s", exc)
        raise HTTPException(400, f"Could not end session: {exc}") from exc


@router.delete("/sessions/{session_id}")
def delete_attendance_session(session_id: UUID, current_user: UserResponse = Depends(get_current_user)):
    try:
        return delete_session(str(session_id))
    except Exception as exc:
        raise HTTPException(400, f"Could not delete session: {exc}") from exc


# ── Manual mark ───────────────────────────────────────────────────────────────

class MarkPayload(BaseModel):
    session_id:        UUID
    student_id:        UUID
    attendance_status: str


@router.post("/mark", response_model=AttendanceRecordResponse)
def mark_attendance_route(payload: MarkPayload, current_user: UserResponse = Depends(get_current_user)):
    try:
        return mark_attendance(str(payload.session_id), str(payload.student_id), payload.attendance_status)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Could not mark attendance: {exc}") from exc


# ── Records ───────────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/records", response_model=List[AttendanceRecordResponse])
def get_session_records(session_id: UUID, current_user: UserResponse = Depends(get_current_user)):
    try:
        return get_session_attendance(str(session_id))
    except Exception as exc:
        raise HTTPException(500, f"Could not load records: {exc}") from exc


@router.get("/student-history")
def get_student_history_route(current_user: UserResponse = Depends(get_current_user)):
    try:
        return get_student_history(str(current_user.id))
    except Exception as exc:
        raise HTTPException(500, f"Could not load attendance history: {exc}") from exc


# ── Face check-in ─────────────────────────────────────────────────────────────

@router.post("/face-checkin", status_code=200)
async def face_checkin_route(
    session_id: UUID = Form(...),
    image: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
):
    _check_image(image)
    data = await image.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image too large. Max 10 MB.")
    if not data:
        raise HTTPException(400, "Uploaded image is empty.")
    try:
        return face_checkin(str(session_id), data)
    except Exception as exc:
        logger.exception("face_checkin error")
        raise HTTPException(500, f"Face check-in failed: {exc}") from exc


# ── Group face check-in ───────────────────────────────────────────────────────

@router.post("/group-face-checkin", status_code=200)
async def group_face_checkin_route(
    session_id: UUID = Form(...),
    image: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
):
    _check_image(image)
    data = await image.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image too large. Max 10 MB.")
    try:
        return group_face_checkin(str(session_id), data)
    except Exception as exc:
        logger.exception("group_face_checkin error")
        raise HTTPException(500, f"Group face check-in failed: {exc}") from exc


# ── Voice check-in ────────────────────────────────────────────────────────────

@router.post("/voice-checkin", status_code=200)
async def voice_checkin_route(
    session_id: UUID = Form(...),
    audio: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
):
    _check_audio(audio)
    data = await audio.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "Audio too large. Max 25 MB.")
    try:
        return voice_checkin(str(session_id), data, original_filename=audio.filename or "recording.wav")
    except Exception as exc:
        logger.exception("voice_checkin error")
        raise HTTPException(500, f"Voice check-in failed: {exc}") from exc
