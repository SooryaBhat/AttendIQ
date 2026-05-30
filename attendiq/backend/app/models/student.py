from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class StudentCreate(BaseModel):
    full_name: str = Field(..., description="Full name of the student")
    roll_number: str = Field(..., description="Student roll number")
    email: EmailStr = Field(..., description="Student email address")
    phone: Optional[str] = Field(None, description="Optional phone number")
    department_id: Optional[UUID] = Field(None, description="Department identifier")
    face_enrolled: bool = Field(False, description="Face enrollment status")
    voice_enrolled: bool = Field(False, description="Voice enrollment status")
    password: Optional[str] = Field(None, min_length=6, description="Initial login password")


class StudentUpdate(BaseModel):
    full_name: Optional[str] = Field(None, description="Updated full name")
    roll_number: Optional[str] = Field(None, description="Updated roll number")
    email: Optional[EmailStr] = Field(None, description="Updated email")
    phone: Optional[str] = Field(None, description="Updated phone number")
    department_id: Optional[UUID] = Field(None, description="Updated department")
    face_enrolled: Optional[bool] = Field(None, description="Face enrollment status")
    voice_enrolled: Optional[bool] = Field(None, description="Voice enrollment status")
    password: Optional[str] = Field(None, min_length=6, description="New password to set")


class StudentResponse(BaseModel):
    id: UUID
    full_name: str
    roll_number: str
    email: EmailStr
    phone: Optional[str] = None
    department_id: Optional[UUID] = None
    face_enrolled: bool
    voice_enrolled: bool
    is_active: bool

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "full_name": "Neha Sharma",
                "roll_number": "STU-2026-001",
                "email": "neha.sharma@college.edu",
                "phone": "9876543210",
                "department_id": "d2c3b4a5-e6f7-8901-bcde-1234567890ab",
                "face_enrolled": True,
                "voice_enrolled": False,
                "is_active": True,
            }
        }
