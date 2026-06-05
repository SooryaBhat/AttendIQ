# ============================================================
#  AttendIQ — Biometric Pydantic Models
#  File: backend/app/models/biometric.py
#
#  Change from previous version:
#    VoiceEnrollResponse.embedding_size description updated
#    to reflect ECAPA-TDNN output of 192 (was 256 for resemblyzer)
# ============================================================

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Enum ──────────────────────────────────────────────────────

class EnrollmentType(str, Enum):
    face  = "face"
    voice = "voice"


# ── Face enrollment ───────────────────────────────────────────

class FaceEnrollResponse(BaseModel):
    """Response returned after a successful face enrollment."""
    success:        bool = Field(..., description="True if enrollment succeeded")
    student_id:     UUID = Field(..., description="UUID of the enrolled student")
    embedding_size: int  = Field(..., description="Face embedding dimensions — dlib: 128")
    message:        str  = Field(..., description="Human-readable status message")

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
    """Response returned after face recognition."""
    matched: bool = Field(..., description="True if the uploaded face matches an enrolled student")
    student_id: Optional[UUID] = Field(None, description="Matched student UUID if any")
    confidence: Optional[float] = Field(None, description="Match confidence score between 0 and 1")

    class Config:
        json_schema_extra = {
            "example": {
                "matched": True,
                "student_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "confidence": 0.87
            }
        }


# ── Voice enrollment ──────────────────────────────────────────

class VoiceEnrollResponse(BaseModel):
    """Response returned after a successful voice enrollment."""
    success:        bool = Field(..., description="True if enrollment succeeded")
    student_id:     UUID = Field(..., description="UUID of the enrolled student")
    embedding_size: int  = Field(
        ...,
        description="Voice embedding dimensions — SpeechBrain ECAPA-TDNN: 192"
    )
    message:        str  = Field(..., description="Human-readable status message")

    class Config:
        json_schema_extra = {
            "example": {
                "success":        True,
                "student_id":     "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "embedding_size": 192,
                "message":        "Voice enrolled successfully."
            }
        }

class VoiceRecognitionResponse(BaseModel):
    """Response returned after a successful voice recognition."""
    matched: bool = Field(..., description="True if the uploaded voice matches an enrolled student")
    student_id: Optional[UUID] = Field(None, description="Matched student UUID if any")
    confidence: Optional[float] = Field(None, description="Match confidence score between 0 and 1")

    class Config:
        json_schema_extra = {
            "example": {
                "matched": True,
                "student_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "confidence": 0.91
            }
        }

# ── Shared DB record ──────────────────────────────────────────

class BiometricEnrollmentRecord(BaseModel):
    """Full DB record — used internally and for audit endpoints."""
    id:             UUID
    student_id:     UUID
    type:           EnrollmentType
    embedding_size: int
    model_version:  Optional[str]      = None
    is_active:      bool
    enrolled_at:    Optional[datetime] = None

    class Config:
        from_attributes = True