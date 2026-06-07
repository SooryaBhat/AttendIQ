# ============================================================
#  AttendIQ — Biometric Routes
#  File: backend/app/routes/biometric.py
#
#  Endpoints:
#    POST /biometric/enroll-face   — face_recognition + dlib  → 128-d
#    POST /biometric/enroll-voice  — SpeechBrain ECAPA-TDNN   → 192-d
#
#  Change from previous version:
#    - Removed import of resemblyzer ALLOWED_AUDIO_TYPES
#    - ALLOWED_AUDIO_TYPES now defined locally in this file
#    - Updated enroll-voice docstring to reflect new stack
# ============================================================

import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.dependencies.auth import get_current_user
from app.models.biometric import (
    FaceEnrollResponse,
    FaceRecognitionResponse,
    VoiceEnrollResponse,
    VoiceRecognitionResponse,
)
from app.models.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/biometric", tags=["Biometric Enrollment"])

BIOMETRIC_DISABLED = os.getenv("DISABLE_BIOMETRIC", "false").strip().lower() in {
    "1", "true", "yes", "on"
}


def _ensure_biometric_enabled() -> None:
    if BIOMETRIC_DISABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Biometric services are disabled on this deployment. "
                "Set DISABLE_BIOMETRIC=false to enable them."
            ),
        )


def _import_face_service():
    try:
        from app.services.face_service import enroll_face, recognize_face
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Face recognition libraries are not installed on this deployment. "
                "Enable biometric support or install the required dependencies."
            ),
        ) from exc
    return enroll_face, recognize_face


def _import_voice_service():
    try:
        from app.services.voice_service import enroll_voice, recognize_voice
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Voice recognition libraries are not installed on this deployment. "
                "Enable biometric support or install the required dependencies."
            ),
        ) from exc
    return enroll_voice, recognize_voice

# ── File type constants ───────────────────────────────────────

_ALLOWED_IMAGE_TYPES = {
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

_MAX_IMAGE_BYTES = 10 * 1024 * 1024   # 10 MB
_MAX_AUDIO_BYTES = 25 * 1024 * 1024   # 25 MB


# ── Shared validation ─────────────────────────────────────────

def _validate_upload(
    content_type: str,
    allowed_types: set,
    file_bytes: bytes,
    max_bytes: int,
    label: str,
) -> None:
    """Validate MIME type and file size. Raises HTTPException on failure."""
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported {label} type '{content_type}'. "
                f"Accepted: {', '.join(sorted(allowed_types))}."
            ),
        )
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded {label} file is empty.",
        )
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"{label.capitalize()} file too large. "
                f"Maximum: {max_bytes // (1024 * 1024)} MB."
            ),
        )


# ── POST /biometric/enroll-face ───────────────────────────────

@router.post(
    "/enroll-face",
    response_model=FaceEnrollResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a student's face",
    description=(
        "Upload a student photo. Detects the face with dlib/face_recognition, "
        "computes a 128-d embedding, and stores it in biometric_enrollments. "
        "Sets profiles.face_enrolled = TRUE on success."
    ),
)
async def enroll_face_endpoint(
    student_id: UUID = Form(..., description="UUID of the student to enroll"),
    image: UploadFile = File(
        ..., description="Student face photo — JPEG / PNG / BMP / WEBP, max 10 MB"
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> FaceEnrollResponse:
    image_bytes = await image.read()

    _ensure_biometric_enabled()
    enroll_face, _ = _import_face_service()

    _validate_upload(
        content_type=image.content_type or "",
        allowed_types=_ALLOWED_IMAGE_TYPES,
        file_bytes=image_bytes,
        max_bytes=_MAX_IMAGE_BYTES,
        label="image",
    )

    logger.info(
        "Face enroll: student=%s file=%s size=%d by=%s",
        student_id, image.filename, len(image_bytes), current_user.email,
    )

    try:
        return enroll_face(student_id=str(student_id), image_bytes=image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in enroll_face: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during face enrollment.",
        )


# ── POST /biometric/recognize-face ─────────────────────────────

@router.post(
    "/recognize-face",
    response_model=FaceRecognitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Recognize a student's face",
    description=(
        "Upload a student photo to compare against enrolled face embeddings. "
        "Returns the matched student and confidence if a match is found."
    ),
)
async def recognize_face_endpoint(
    image: UploadFile = File(
        ..., description="Student face image — JPEG / PNG / BMP / WEBP, max 10 MB"
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> FaceRecognitionResponse:
    image_bytes = await image.read()

    _ensure_biometric_enabled()
    _, recognize_face = _import_face_service()

    _validate_upload(
        content_type=image.content_type or "",
        allowed_types=_ALLOWED_IMAGE_TYPES,
        file_bytes=image_bytes,
        max_bytes=_MAX_IMAGE_BYTES,
        label="image",
    )

    logger.info(
        "Face recognize: file=%s size=%d by=%s",
        image.filename, len(image_bytes), current_user.email,
    )

    try:
        result = recognize_face(image_bytes=image_bytes)
        return FaceRecognitionResponse(
            matched=result.get("matched", False),
            student_id=result.get("student_id"),
            confidence=result.get("confidence"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in recognize_face: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during face recognition.",
        ) from exc


# ── POST /biometric/recognize-voice ───────────────────────────

@router.post(
    "/recognize-voice",
    response_model=VoiceRecognitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Recognize a student's voice",
    description=(
        "Upload a student audio recording and compare it against enrolled "
        "voice embeddings. Returns the matched student and confidence if a "
        "match is found."
    ),
)
async def recognize_voice_endpoint(
    audio: UploadFile = File(
        ...,
        description=(
            "Student voice recording — WAV / MP3 / OGG / FLAC / WEBM, "
            "max 25 MB, minimum 2 seconds of speech"
        ),
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> VoiceRecognitionResponse:
    audio_bytes = await audio.read()

    _ensure_biometric_enabled()
    _, recognize_voice = _import_voice_service()

    _validate_upload(
        content_type=audio.content_type or "",
        allowed_types=_ALLOWED_AUDIO_TYPES,
        file_bytes=audio_bytes,
        max_bytes=_MAX_AUDIO_BYTES,
        label="audio",
    )

    logger.info(
        "Voice recognize: file=%s size=%d by=%s",
        audio.filename, len(audio_bytes), current_user.email,
    )

    try:
        result = recognize_voice(
            audio_bytes=audio_bytes,
            original_filename=audio.filename or "recording.wav",
        )
        return VoiceRecognitionResponse(
            matched=result.get("matched", False),
            student_id=result.get("student_id"),
            confidence=result.get("confidence"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in recognize_voice: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during voice recognition.",
        ) from exc


# ── POST /biometric/enroll-voice ──────────────────────────────

@router.post(
    "/enroll-voice",
    response_model=VoiceEnrollResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a student's voice",
    description=(
        "Upload a student audio recording. "
        "Loads and resamples to 16 kHz mono via torchaudio (librosa fallback). "
        "Generates a 192-dimensional speaker embedding using SpeechBrain "
        "ECAPA-TDNN (speechbrain/spkrec-ecapa-voxceleb). "
        "Stores it in biometric_enrollments with type='voice'. "
        "Sets profiles.voice_enrolled = TRUE on success. "
        "Requires at least 2 seconds of clear speech. "
        "WAV recommended; MP3, OGG, FLAC also accepted."
    ),
)
async def enroll_voice_endpoint(
    student_id: UUID = Form(..., description="UUID of the student to enroll"),
    audio: UploadFile = File(
        ...,
        description=(
            "Student voice recording — WAV / MP3 / OGG / FLAC / WEBM, "
            "max 25 MB, minimum 2 seconds of speech"
        ),
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> VoiceEnrollResponse:
    """
    POST /biometric/enroll-voice

    Multipart form fields:
      - student_id  (UUID, required)
      - audio       (file, required)

    Returns:
        { success, student_id, embedding_size: 192, message }
    """
    audio_bytes = await audio.read()

    _ensure_biometric_enabled()
    enroll_voice, _ = _import_voice_service()

    _validate_upload(
        content_type=audio.content_type or "",
        allowed_types=_ALLOWED_AUDIO_TYPES,
        file_bytes=audio_bytes,
        max_bytes=_MAX_AUDIO_BYTES,
        label="audio",
    )

    logger.info(
        "Voice enroll: student=%s file=%s size=%d by=%s",
        student_id, audio.filename, len(audio_bytes), current_user.email,
    )

    try:
        return enroll_voice(
            student_id=str(student_id),
            audio_bytes=audio_bytes,
            original_filename=audio.filename or "recording.wav",
        )
    except ValueError as exc:
        logger.warning("Voice enroll validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    except RuntimeError as exc:
        logger.error("Voice enroll DB error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )
    except Exception as exc:
        logger.exception("Unexpected error in enroll_voice: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during voice enrollment.",
        )