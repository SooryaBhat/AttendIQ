from typing import Optional, List
from uuid import UUID
from datetime import date, datetime

from pydantic import BaseModel, Field


class AttendanceSessionCreate(BaseModel):
    subject_id: UUID = Field(..., description="Subject identifier")
    faculty_id: UUID = Field(..., description="Faculty who created the session")
    department_id: UUID = Field(..., description="Department identifier")
    session_date: date = Field(..., description="Attendance session date")
    session_label: str = Field(..., description="Human readable session label")
    method: str = Field("face", description="Attendance method")
    status: Optional[str] = Field("pending", description="Session status")
    uploaded_file_path: Optional[str] = Field(None, description="Path to uploaded attendance file")
    total_students: Optional[int] = Field(0, description="Total number of students")
    present_count: Optional[int] = Field(0, description="Present student count")
    absent_count: Optional[int] = Field(0, description="Absent student count")
    processing_log: Optional[str] = Field(None, description="Processing log or notes")
    started_at: Optional[datetime] = Field(None, description="Actual start time")
    completed_at: Optional[datetime] = Field(None, description="Actual completion time")


class AttendanceSessionUpdate(BaseModel):
    session_label: Optional[str] = Field(None, description="Updated session label")
    started_at: Optional[datetime] = Field(None, description="Updated start time")
    completed_at: Optional[datetime] = Field(None, description="Updated completion time")
    status: Optional[str] = Field(None, description="Session status")


class AttendanceSessionResponse(BaseModel):
    id: UUID
    subject_id: UUID
    faculty_id: Optional[UUID] = None
    session_label: str
    session_date: Optional[date] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AttendanceRecordResponse(BaseModel):
    id: UUID
    session_id: UUID
    student_id: UUID
    status: str
    marked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AttendancePresentStudent(BaseModel):
    student_id: UUID
    name: str
    confidence: float


class AttendanceAbsentStudent(BaseModel):
    student_id: UUID
    name: str


class AttendanceGroupFaceCheckinResponse(BaseModel):
    present_count: int
    absent_count: int
    attendance_percentage: float
    present_students: List[AttendancePresentStudent]
    absent_students: List[AttendanceAbsentStudent]

    class Config:
        from_attributes = True


class AttendanceVoiceCheckinResponse(BaseModel):
    attendance_marked: bool
    student_id: Optional[UUID] = None
    confidence: Optional[float] = None
    session_id: Optional[UUID] = None
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceFaceCheckinResponse(BaseModel):
    attendance_marked: bool
    student_id: Optional[UUID] = None
    confidence: Optional[float] = None
    session_id: Optional[UUID] = None
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class StudentAttendanceHistoryItem(BaseModel):
    attendance_id: UUID
    session_id: UUID
    session_name: Optional[str] = None
    subject_name: Optional[str] = None
    attendance_status: Optional[str] = None
    method: Optional[str] = None
    confidence: Optional[float] = None
    marked_at: Optional[datetime] = None
    session_date: Optional[date] = None

    class Config:
        from_attributes = True
