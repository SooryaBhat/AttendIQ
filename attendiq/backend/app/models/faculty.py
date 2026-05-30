from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class FacultyCreate(BaseModel):
    full_name: str = Field(..., description="Full name of the faculty member")
    email: EmailStr = Field(..., description="Faculty email address")
    phone: Optional[str] = Field(None, description="Optional contact phone")
    department_id: UUID = Field(..., description="Department identifier")
    password: Optional[str] = Field(None, min_length=6, description="Initial password for the faculty user")


class FacultyUpdate(BaseModel):
    full_name: Optional[str] = Field(None, description="Updated full name")
    email: Optional[EmailStr] = Field(None, description="Updated email address")
    phone: Optional[str] = Field(None, description="Updated phone number")
    department_id: Optional[UUID] = Field(None, description="Updated department")
    password: Optional[str] = Field(None, min_length=6, description="New password to set")
    is_active: Optional[bool] = Field(None, description="Active status for the faculty user")


class FacultyResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    department_id: Optional[UUID] = None
    is_active: bool

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "f1d2c3b4-e5f6-7890-abcd-ef1234567890",
                "full_name": "Priya Menon",
                "email": "priya.menon@college.edu",
                "phone": "9876543210",
                "department_id": "d2c3b4a5-e6f7-8901-bcde-1234567890ab",
                "is_active": True,
            }
        }
