# ============================================================
#  AttendIQ — Biometric Pydantic Models
#  File: backend/app/models/biometric.py
# ============================================================

from uuid import UUID
from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


class EnrollmentType(str, Enum):
    face  = "face"
    voice = "voice"


# ── Request ───────────────────────────────────────────────────

class FaceEnrollRequest(BaseModel):
    """
    Body fields for face enrollment.
    The image itself arrives as a multipart file upload (UploadFile),
    so only student_id is declared here as a Form field.
    This model is used purely for documentation / validation reference.
    """
    student_id: UUID = Field(..., description="UUID of the student to enroll")


# ── Response ──────────────────────────────────────────────────

class FaceEnrollResponse(BaseModel):
    """Response returned after a successful face enrollment."""
    success:        bool  = Field(..., description="True if enrollment succeeded")
    student_id:     UUID  = Field(..., description="UUID of the enrolled student")
    embedding_size: int   = Field(..., description="Dimensions of the face embedding vector (always 128)")
    message:        str   = Field(..., description="Human-readable status message")

    class Config:
        json_schema_extra = {
            "example": {
                "success":        True,
                "student_id":     "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "embedding_size": 128,
                "message":        "Face enrolled successfully."
            }
        }


class FaceRecognitionResponse(BaseModel):
    matched: bool = Field(..., description="Whether the face matches an enrolled student")
    student_id: Optional[UUID] = Field(None, description="Matched student UUID if any")
    confidence: Optional[float] = Field(None, description="Match confidence score between 0 and 1")

    class Config:
        json_schema_extra = {
            "example": {
                "matched": True,
                "student_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "confidence": 0.92
            }
        }


class BiometricEnrollmentRecord(BaseModel):
    """Full DB record shape — used internally and for audit responses."""
    id:            UUID
    student_id:    UUID
    type:          EnrollmentType
    embedding_size: int
    model_version: Optional[str]    = None
    is_active:     bool
    enrolled_at:   Optional[datetime] = None

    class Config:
        from_attributes = True