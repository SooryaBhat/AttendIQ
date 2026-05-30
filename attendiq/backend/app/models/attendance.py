from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


class AttendanceSessionCreate(BaseModel):
    subject_id: UUID = Field(..., description="Subject identifier")
    faculty_id: Optional[UUID] = Field(None, description="Faculty who created the session")
    session_name: str = Field(..., description="Human readable session name")
    start_time: Optional[datetime] = Field(None, description="Planned start time")
    end_time: Optional[datetime] = Field(None, description="Planned end time")


class AttendanceSessionUpdate(BaseModel):
    session_name: Optional[str] = Field(None, description="Updated session name")
    start_time: Optional[datetime] = Field(None, description="Updated start time")
    end_time: Optional[datetime] = Field(None, description="Updated end time")
    status: Optional[str] = Field(None, description="Session status")


class AttendanceSessionResponse(BaseModel):
    id: UUID
    subject_id: UUID
    faculty_id: Optional[UUID] = None
    session_name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AttendanceRecordResponse(BaseModel):
    id: UUID
    session_id: UUID
    student_id: UUID
    attendance_status: str
    marked_at: Optional[datetime] = None

    class Config:
        from_attributes = True
