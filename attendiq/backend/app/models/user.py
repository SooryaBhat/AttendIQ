# User schema (Pydantic) (placeholder)
# ============================================================
#  AttendIQ — User Pydantic Models
#  File: backend/app/models/user.py
# ============================================================

from enum import Enum
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================
#  ENUM: UserRole
# ============================================================

class UserRole(str, Enum):
    """
    All roles in AttendIQ.
    Inherits from str so it serializes cleanly to JSON as a string.
    """
    super_admin        = "super_admin"
    department_admin   = "department_admin"
    faculty            = "faculty"
    student            = "student"


# ============================================================
#  REQUEST MODELS
# ============================================================

class UserLogin(BaseModel):
    """Payload for POST /auth/login"""

    email:    EmailStr = Field(..., description="Registered email address")
    password: str      = Field(..., min_length=6, description="Account password")

    class Config:
        json_schema_extra = {
            "example": {
                "email":    "student@college.edu",
                "password": "secret123"
            }
        }


class UserRegister(BaseModel):
    """
    Payload for creating a new user.
    Used by super_admin (creating dept admins),
    dept_admin (creating faculty / students).
    """

    full_name:     str            = Field(..., min_length=2, max_length=150,
                                          description="Full name of the user")
    email:         EmailStr       = Field(..., description="Unique email address")
    password:      str            = Field(..., min_length=6,
                                          description="Plain-text password (hashed before storage)")
    role:          UserRole       = Field(..., description="Role assigned to this user")
    department_id: Optional[UUID] = Field(None,
                                          description="Required for all roles except super_admin")
    roll_number:   Optional[str]  = Field(None, max_length=50,
                                          description="Required for students only")
    phone:         Optional[str]  = Field(None, max_length=20,
                                          description="Optional contact number")

    @field_validator("department_id")
    @classmethod
    def dept_required_for_non_super(cls, v, info):
        role = info.data.get("role")
        if role and role != UserRole.super_admin and v is None:
            raise ValueError("department_id is required for all roles except super_admin")
        return v

    @field_validator("roll_number")
    @classmethod
    def roll_required_for_student(cls, v, info):
        role = info.data.get("role")
        if role == UserRole.student and not v:
            raise ValueError("roll_number is required for students")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "full_name":     "Ravi Kumar",
                "email":         "ravi@college.edu",
                "password":      "secret123",
                "role":          "student",
                "department_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "roll_number":   "CS2021001",
                "phone":         "9876543210"
            }
        }


# ============================================================
#  RESPONSE MODELS
# ============================================================

class UserResponse(BaseModel):
    """
    Safe user object returned in API responses.
    Never includes password_hash.
    """

    id:              UUID
    full_name:       str
    email:           EmailStr
    role:            UserRole
    department_id:   Optional[UUID] = None
    roll_number:     Optional[str]  = None
    phone:           Optional[str]  = None
    is_active:       bool
    face_enrolled:   bool
    voice_enrolled:  bool

    class Config:
        from_attributes = True          # Allow building from ORM / dict objects
        json_schema_extra = {
            "example": {
                "id":             "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "full_name":      "Ravi Kumar",
                "email":          "ravi@college.edu",
                "role":           "student",
                "department_id":  "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "roll_number":    "CS2021001",
                "phone":          "9876543210",
                "is_active":      True,
                "face_enrolled":  False,
                "voice_enrolled": False
            }
        }


class TokenResponse(BaseModel):
    """Returned after a successful login."""

    access_token: str
    token_type:   str        = "bearer"
    user:         UserResponse