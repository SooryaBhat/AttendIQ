# ============================================================
#  AttendIQ — Face Enrollment Service
#  File: backend/app/services/face_service.py
#
#  Responsibilities:
#    1. Receive raw image bytes
#    2. Decode image with OpenCV
#    3. Detect face and compute 128-d embedding via face_recognition
#    4. Serialize embedding as JSON string
#    5. Upsert into biometric_enrollments table
#    6. Flip profiles.face_enrolled = TRUE
# ============================================================

import io
import json
import logging
import os
from uuid import uuid4

import cv2
import face_recognition
import numpy as np

from app.config import settings
from app.db.supabase_client import supabase
from app.models.biometric import FaceEnrollResponse

logger = logging.getLogger(__name__)

# face_recognition uses dlib's model — track version for re-enrollment checks
_MODEL_VERSION = "face_recognition_dlib_v1"


# ── Helpers ───────────────────────────────────────────────────

def _decode_image(image_bytes: bytes) -> np.ndarray:
    """
    Decode raw image bytes into an RGB numpy array.
    face_recognition expects RGB; OpenCV loads BGR by default, so we convert.

    Raises:
        ValueError: If the bytes cannot be decoded as a valid image.
    """
    np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(
            "Could not decode the uploaded file as an image. "
            "Accepted formats: JPEG, PNG, BMP, WEBP."
        )
    # Convert BGR → RGB (face_recognition requirement)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return rgb


def _detect_and_encode(rgb_image: np.ndarray) -> np.ndarray:
    """
    Detect faces in the image and return the 128-d embedding of the
    first (and ideally only) face found.

    Uses HOG model by default (fast, CPU-friendly).
    Switch model="cnn" for GPU environments for higher accuracy.

    Raises:
        ValueError: If no face or multiple faces are detected.
    """
    # Detect face locations
    face_locations = face_recognition.face_locations(rgb_image, model="hog")

    if len(face_locations) == 0:
        raise ValueError(
            "No face detected in the uploaded image. "
            "Please upload a clear, front-facing photo with good lighting."
        )

    if len(face_locations) > 1:
        raise ValueError(
            f"{len(face_locations)} faces detected in the image. "
            "Please upload a photo containing only the student's face."
        )

    # Compute 128-d face encoding for the single detected face
    encodings = face_recognition.face_encodings(rgb_image, face_locations)

    if not encodings:
        raise ValueError(
            "A face was detected but could not be encoded. "
            "Try a higher-resolution image."
        )

    return encodings[0]   # shape: (128,)  dtype: float64


def _save_temp_image(image_bytes: bytes, student_id: str) -> str:
    """
    Save the uploaded image to uploads/faces/ for audit purposes.
    Returns the relative file path.
    """
    upload_dir = settings.UPLOAD_DIR_FACES
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{student_id}_face.jpg"
    path = os.path.join(upload_dir, filename)
    with open(path, "wb") as f:
        f.write(image_bytes)
    return path


# ── Main service function ─────────────────────────────────────

def enroll_face(student_id: str, image_bytes: bytes) -> FaceEnrollResponse:
    """
    Full face enrollment pipeline:
      1. Validate student exists in profiles
      2. Decode image → RGB numpy array
      3. Detect face + compute 128-d embedding
      4. Serialize embedding as JSON string
      5. Upsert into biometric_enrollments (one record per student, type=face)
      6. Update profiles.face_enrolled = TRUE
      7. Save image to uploads/faces/ for audit

    Args:
        student_id:   UUID string of the student.
        image_bytes:  Raw bytes of the uploaded image file.

    Returns:
        FaceEnrollResponse with success=True and embedding_size=128.

    Raises:
        ValueError:   Student not found, no face detected, multiple faces.
        RuntimeError: DB write failure.
    """

    # ── Step 1: Validate student exists ──────────────────────
    profile_resp = (
        supabase.table("profiles")
        .select("id, full_name, role, face_enrolled")
        .eq("id", student_id)
        .eq("role", "student")
        .single()
        .execute()
    )
    if not profile_resp.data:
        raise ValueError(f"Student with id '{student_id}' not found.")

    student = profile_resp.data
    logger.info(
        "Face enrollment started for student: %s (%s)",
        student.get("full_name"), student_id
    )

    # ── Step 2: Decode image ──────────────────────────────────
    rgb_image = _decode_image(image_bytes)
    logger.debug("Image decoded: shape=%s", rgb_image.shape)

    # ── Step 3: Detect face + compute embedding ───────────────
    embedding: np.ndarray = _detect_and_encode(rgb_image)
    embedding_size = len(embedding)   # always 128 for dlib
    logger.debug("Embedding computed: size=%d", embedding_size)

    # ── Step 4: Serialize embedding → JSON string ─────────────
    # numpy float64 values → plain Python list → JSON string
    # Stored as TEXT in Supabase; loaded back via json.loads() + np.array()
    embedding_json: str = json.dumps(embedding.tolist())

    # ── Step 5: Save image file ───────────────────────────────
    file_path = _save_temp_image(image_bytes, student_id)

    # ── Step 6: Upsert biometric_enrollments ─────────────────
    # UNIQUE constraint on (student_id, type) → upsert replaces on conflict
    enrollment_row = {
        "id":            str(uuid4()),
        "student_id":    student_id,
        "type":          "face",
        "encoding":      embedding_json,
        "file_path":     file_path,
        "model_version": _MODEL_VERSION,
        "is_active":     True,
    }

    upsert_resp = (
        supabase.table("biometric_enrollments")
        .upsert(enrollment_row, on_conflict="student_id,type")
        .execute()
    )

    if not upsert_resp.data:
        logger.error(
            "biometric_enrollments upsert returned no data for student %s", student_id
        )
        raise RuntimeError(
            "Face encoding was computed but could not be saved. "
            "Check Supabase RLS policies on biometric_enrollments."
        )

    logger.info(
        "Enrollment record saved for student %s (enrollment_id=%s)",
        student_id, upsert_resp.data[0].get("id") if isinstance(upsert_resp.data, list) else ""
    )

    # ── Step 7: Flip face_enrolled flag on profile ────────────
    supabase.table("profiles").update(
        {"face_enrolled": True}
    ).eq("id", student_id).execute()

    logger.info("face_enrolled=TRUE set on profile for student %s", student_id)

    return FaceEnrollResponse(
        success=True,
        student_id=student_id,
        embedding_size=embedding_size,
        message=f"Face enrolled successfully for {student.get('full_name', student_id)}.",
    )


# ── Utility: load all face encodings (used by attendance AI) ──

def load_all_face_encodings(department_id: str | None = None) -> list[dict]:
    """
    Load all active face encodings from biometric_enrollments.
    Optionally filter by department via a JOIN on profiles.

    Returns a list of dicts:
        [{"student_id": "...", "encoding": np.ndarray(128,)}, ...]

    Used by the attendance recognition pipeline.
    """
    if department_id:
        # Get student IDs from the department first
        profiles_resp = (
            supabase.table("profiles")
            .select("id")
            .eq("role", "student")
            .eq("department_id", department_id)
            .execute()
        )
        student_ids = [p["id"] for p in (profiles_resp.data or [])]
        if not student_ids:
            return []

        resp = (
            supabase.table("biometric_enrollments")
            .select("student_id, encoding")
            .eq("type", "face")
            .eq("is_active", True)
            .in_("student_id", student_ids)
            .execute()
        )
    else:
        resp = (
            supabase.table("biometric_enrollments")
            .select("student_id, encoding")
            .eq("type", "face")
            .eq("is_active", True)
            .execute()
        )

    result = []
    for row in (resp.data or []):
        try:
            vec = np.array(json.loads(row["encoding"]), dtype=np.float64)
            result.append({"student_id": row["student_id"], "encoding": vec})
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "Skipping corrupted encoding for student %s: %s",
                row["student_id"], e
            )

    logger.debug("Loaded %d face encodings", len(result))
    return result


def load_face_encodings_for_students(student_ids: list[str]) -> list[dict]:
    """Load face encodings only for the specified student IDs."""
    if not student_ids:
        return []

    resp = (
        supabase.table("biometric_enrollments")
        .select("student_id, encoding")
        .eq("type", "face")
        .eq("is_active", True)
        .in_("student_id", student_ids)
        .execute()
    )

    result = []
    for row in (resp.data or []):
        try:
            vec = np.array(json.loads(row["encoding"]), dtype=np.float64)
            result.append({"student_id": row["student_id"], "encoding": vec})
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "Skipping corrupted encoding for student %s: %s",
                row["student_id"], e
            )

    logger.debug("Loaded %d filtered face encodings", len(result))
    return result


def _detect_and_encode_all(rgb_image: np.ndarray) -> list[np.ndarray]:
    """Detect all faces in an image and return their 128-d encodings."""
    face_locations = face_recognition.face_locations(rgb_image, model="hog")
    if not face_locations:
        return []

    encodings = face_recognition.face_encodings(rgb_image, face_locations)
    if not encodings:
        raise ValueError(
            "No faces could be encoded from the uploaded image. "
            "Please provide a clear classroom photo."
        )

    return encodings


def recognize_faces(image_bytes: bytes, student_ids: list[str] | None = None) -> list[dict]:
    """Recognize multiple faces in a classroom image against enrolled embeddings."""
    rgb_image = _decode_image(image_bytes)
    query_encodings = _detect_and_encode_all(rgb_image)
    if not query_encodings:
        return []

    enrolled = (
        load_face_encodings_for_students(student_ids)
        if student_ids is not None
        else load_all_face_encodings()
    )
    if not enrolled:
        return []

    encodings = np.vstack([row["encoding"] for row in enrolled])
    matched_students = []
    seen_student_ids = set()

    for query_embedding in query_encodings:
        distances = face_recognition.face_distance(encodings, query_embedding)
        best_index = int(np.argmin(distances))
        best_distance = float(distances[best_index])

        if best_distance < 0.6:
            student_id = enrolled[best_index]["student_id"]
            if student_id in seen_student_ids:
                continue
            seen_student_ids.add(student_id)
            confidence = max(0.0, min(1.0, 1.0 - best_distance))
            matched_students.append({
                "student_id": student_id,
                "confidence": round(confidence, 4),
            })

    return matched_students


def recognize_face(image_bytes: bytes) -> dict:
    """Recognize a single face image against enrolled face encodings."""
    rgb_image = _decode_image(image_bytes)
    query_embedding = _detect_and_encode(rgb_image)

    enrolled = load_all_face_encodings()
    if not enrolled:
        return {"matched": False}

    encodings = np.vstack([row["encoding"] for row in enrolled])
    distances = face_recognition.face_distance(encodings, query_embedding)
    best_index = int(np.argmin(distances))
    best_distance = float(distances[best_index])

    if best_distance < 0.6:
        student_id = enrolled[best_index]["student_id"]
        confidence = max(0.0, min(1.0, 1.0 - best_distance))
        return {
            "matched": True,
            "student_id": student_id,
            "confidence": round(confidence, 4),
        }

    return {"matched": False}
