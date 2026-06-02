# ============================================================
#  AttendIQ — Biometric Routes
#  File: backend/app/routes/biometric.py
# ============================================================

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.dependencies.auth import get_current_user
from app.models.biometric import FaceEnrollResponse, FaceRecognitionResponse
from app.models.user import UserResponse
from app.services.face_service import enroll_face, recognize_face

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/biometric", tags=["biometric"])

# Allowed image MIME types
_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/bmp",
    "image/webp",
}

# Max file size: 10 MB
_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


def _validate_image_upload(file: UploadFile) -> None:
    """
    Validate content type of the uploaded file.
    Size is checked after reading to avoid streaming issues.
    """
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Accepted types: JPEG, PNG, BMP, WEBP."
            ),
        )


@router.post(
    "/enroll-face",
    response_model=FaceEnrollResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a student's face",
    description=(
        "Upload a student photo to detect the face, compute a 128-dimensional "
        "embedding using dlib, and store it in biometric_enrollments. "
        "The student's face_enrolled flag is updated to TRUE on success."
    ),
)
async def enroll_face_endpoint(
    student_id: UUID = Form(
        ...,
        description="UUID of the student to enroll",
    ),
    image: UploadFile = File(
        ...,
        description="Student face image (JPEG / PNG / BMP / WEBP, max 10 MB)",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> FaceEnrollResponse:
    """
    POST /biometric/enroll-face

    Multipart form fields:
    - student_id  (UUID, required)
    - image       (file, required)

    Returns:
        FaceEnrollResponse — { success, student_id, embedding_size, message }
    """

    # ── Validate file type ────────────────────────────────────
    _validate_image_upload(image)

    # ── Read file bytes ───────────────────────────────────────
    image_bytes = await image.read()

    # ── Validate file size ────────────────────────────────────
    if len(image_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is 10 MB.",
        )

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    logger.info(
        "Face enrollment request: student_id=%s, file=%s, size=%d bytes, requested_by=%s",
        student_id, image.filename, len(image_bytes), current_user.email,
    )

    # ── Run enrollment pipeline ───────────────────────────────
    try:
        result = enroll_face(
            student_id=str(student_id),
            image_bytes=image_bytes,
        )
        return result

    except ValueError as exc:
        # Student not found, no face detected, multiple faces, etc.
        logger.warning("Face enrollment validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        # DB write failure
        logger.error("Face enrollment DB error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error during face enrollment: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during face enrollment.",
        ) from exc


@router.post(
    "/recognize-face",
    response_model=FaceRecognitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Recognize a student's face",
    description=(
        "Upload a face image to detect exactly one face, compare it to enrolled face embeddings, "
        "and return the best matching student if the match is above the threshold."
    ),
)
async def recognize_face_endpoint(
    image: UploadFile = File(
        ...,
        description="Student face image (JPEG / PNG / BMP / WEBP, max 10 MB)",
    ),
    current_user: UserResponse = Depends(get_current_user),
) -> FaceRecognitionResponse:
    """
    POST /biometric/recognize-face

    Multipart form fields:
    - image       (file, required)

    Returns:
        FaceRecognitionResponse — { matched, student_id?, confidence? }
    """

    _validate_image_upload(image)
    image_bytes = await image.read()

    if len(image_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is 10 MB.",
        )

    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    logger.info(
        "Face recognition request: file=%s, size=%d bytes, requested_by=%s",
        image.filename, len(image_bytes), current_user.email,
    )

    try:
        result = recognize_face(image_bytes=image_bytes)
        return FaceRecognitionResponse(**result)

    except ValueError as exc:
        logger.warning("Face recognition validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error during face recognition: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during face recognition.",
        ) from exc