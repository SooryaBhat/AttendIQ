from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DepartmentBase(BaseModel):
    name: str = Field(..., description="Department name")
    code: str = Field(..., description="Unique department code")
    description: Optional[str] = Field(None, description="Optional description")


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated department name")
    code: Optional[str] = Field(None, description="Updated department code")
    description: Optional[str] = Field(None, description="Updated department description")


class DepartmentResponse(DepartmentBase):
    id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "name": "Computer Science",
                "code": "CSE",
                "description": "Computing and software engineering department.",
                "created_at": "2026-05-30T12:00:00Z",
            }
        }
