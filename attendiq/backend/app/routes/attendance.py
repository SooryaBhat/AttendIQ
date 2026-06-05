import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel

from app.dependencies.auth import get_current_user
from app.models.user import UserResponse
from app.models.attendance import (
    AttendanceSessionCreate,
    AttendanceSessionResponse,
    AttendanceSessionUpdate,
    AttendanceRecordResponse,
    AttendanceGroupFaceCheckinResponse,
    AttendanceVoiceCheckinResponse,
    StudentAttendanceHistoryItem,
)
from app.services.attendance_service import (
    create_session,
    start_session,
    end_session,
    delete_session,
    list_sessions,
    get_session,
    mark_attendance,
    get_session_attendance,
    get_student_history,
    face_checkin,
    voice_checkin,
    group_face_checkin,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attendance", tags=["attendance"])


# Allowed image MIME types for face check-in
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/bmp",
    "image/webp",
}

_ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/flac",
    "audio/x-flac",
    "audio/webm",
}


def _validate_image_upload(file: UploadFile) -> None:
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Accepted types: JPEG, PNG, BMP, WEBP."
            ),
        )


def _validate_audio_upload(file: UploadFile) -> None:
    if file.content_type not in _ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Accepted types: WAV, MP3, OGG, FLAC, WEBM."
            ),
        )


@router.post("/sessions", response_model=AttendanceSessionResponse, status_code=status.HTTP_201_CREATED)
def create_attendance_session(payload: AttendanceSessionCreate, current_user: UserResponse = Depends(get_current_user)) -> AttendanceSessionResponse:
    try:
        return create_session(payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/sessions", response_model=List[AttendanceSessionResponse])
def get_attendance_sessions(subject_id: UUID = None, current_user: UserResponse = Depends(get_current_user)) -> List[AttendanceSessionResponse]:
    try:
        sid = str(subject_id) if subject_id else None
        return list_sessions(subject_id=sid)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/sessions/{session_id}", response_model=AttendanceSessionResponse)
def get_attendance_session(session_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> AttendanceSessionResponse:
    try:
        return get_session(str(session_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.put("/sessions/{session_id}/start", response_model=AttendanceSessionResponse)
def start_attendance_session(session_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> AttendanceSessionResponse:
    try:
        return start_session(str(session_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/sessions/{session_id}/end", response_model=AttendanceSessionResponse)
def end_attendance_session(session_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> AttendanceSessionResponse:
    try:
        return end_session(str(session_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/sessions/{session_id}")
def delete_attendance_session(session_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        return delete_session(str(session_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


class MarkPayload(BaseModel := __import__('pydantic').BaseModel):
    session_id: UUID
    student_id: UUID
    attendance_status: str


class AttendanceFaceCheckinResponse(BaseModel):
    attendance_marked: bool
    student_id: Optional[UUID] = None
    confidence: Optional[float] = None
    session_id: Optional[UUID] = None
    reason: Optional[str] = None


@router.post("/mark", response_model=AttendanceRecordResponse)
def mark_attendance_route(payload: MarkPayload, current_user: UserResponse = Depends(get_current_user)) -> AttendanceRecordResponse:
    try:
        return mark_attendance(str(payload.session_id), str(payload.student_id), payload.attendance_status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post(
    "/face-checkin",
    response_model=AttendanceFaceCheckinResponse,
    status_code=status.HTTP_200_OK,
    summary="Face-based attendance check-in",
)
async def face_checkin_route(
    session_id: UUID = Form(..., description="UUID of the attendance session"),
    image: UploadFile = File(
        ..., description="Student face image (JPEG / PNG / BMP / WEBP, max 10 MB)"
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> AttendanceFaceCheckinResponse:
    _validate_image_upload(image)
    image_bytes = await image.read()

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum allowed size is 10 MB.",
        )

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        result = face_checkin(str(session_id), image_bytes)
        return AttendanceFaceCheckinResponse(**result)

    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during face check-in: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during face check-in.",
        ) from exc


@router.post(
    "/group-face-checkin",
    response_model=AttendanceGroupFaceCheckinResponse,
    status_code=status.HTTP_200_OK,
    summary="Group face-based attendance check-in",
)
async def group_face_checkin_route(
    session_id: UUID = Form(..., description="UUID of the attendance session"),
    image: UploadFile = File(
        ..., description="Classroom photo containing multiple students' faces"
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> AttendanceGroupFaceCheckinResponse:
    _validate_image_upload(image)
    image_bytes = await image.read()

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum allowed size is 10 MB.",
        )

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        result = group_face_checkin(str(session_id), image_bytes)
        return AttendanceGroupFaceCheckinResponse(**result)

    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during group face check-in: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during group face check-in.",
        ) from exc


@router.post(
    "/voice-checkin",
    response_model=AttendanceVoiceCheckinResponse,
    status_code=status.HTTP_200_OK,
    summary="Voice-based attendance check-in",
)
async def voice_checkin_route(
    session_id: UUID = Form(..., description="UUID of the attendance session"),
    audio: UploadFile = File(
        ..., description="Student voice recording — WAV / MP3 / OGG / FLAC / WEBM, max 25 MB"
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> AttendanceVoiceCheckinResponse:
    _validate_audio_upload(audio)
    audio_bytes = await audio.read()

    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum allowed size is 25 MB.",
        )

    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        result = voice_checkin(str(session_id), audio_bytes, original_filename=audio.filename or "recording.wav")
        return AttendanceVoiceCheckinResponse(**result)

    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during voice check-in: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during voice check-in.",
        ) from exc


@router.get("/sessions/{session_id}/records", response_model=List[AttendanceRecordResponse])
def get_session_records(session_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> List[AttendanceRecordResponse]:
    try:
        return get_session_attendance(str(session_id))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/student-history", response_model=List[StudentAttendanceHistoryItem])
def get_student_history_route(current_user: UserResponse = Depends(get_current_user)) -> List[StudentAttendanceHistoryItem]:
    try:
        return get_student_history(str(current_user.id))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
