from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


class SubjectCreate(BaseModel):
    name: str = Field(..., description="Subject name")
    code: str = Field(..., description="Unique subject code")
    faculty_id: Optional[UUID] = Field(None, description="Faculty owner id")
    department_id: Optional[UUID] = Field(None, description="Department id")


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated subject name")
    code: Optional[str] = Field(None, description="Updated subject code")
    faculty_id: Optional[UUID] = Field(None, description="Updated faculty id")
    department_id: Optional[UUID] = Field(None, description="Updated department id")


class SubjectResponse(BaseModel):
    id: UUID
    name: str
    code: str
    faculty_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "name": "Advanced Algorithms",
                "code": "ALG-301",
                "faculty_id": "f1d2c3b4-e5f6-7890-abcd-ef1234567890",
                "department_id": "d2c3b4a5-e6f7-8901-bcde-1234567890ab",
                "created_at": "2026-05-30T12:00:00Z",
            }
        }
