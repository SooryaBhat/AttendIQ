from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List
from pydantic import BaseModel

from app.dependencies.auth import get_current_user
from app.models.user import UserResponse
from app.models.attendance import (
    AttendanceSessionCreate,
    AttendanceSessionResponse,
    AttendanceSessionUpdate,
    AttendanceRecordResponse,
)
from app.services.attendance_service import (
    create_session,
    start_session,
    end_session,
    list_sessions,
    get_session,
    mark_attendance,
    get_session_attendance,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/sessions", response_model=AttendanceSessionResponse, status_code=status.HTTP_201_CREATED)
def create_attendance_session(payload: AttendanceSessionCreate, current_user: UserResponse = Depends(get_current_user)) -> AttendanceSessionResponse:
    try:
        return create_session(payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/sessions", response_model=List[AttendanceSessionResponse])
def get_attendance_sessions(subject_id: UUID = None, current_user: UserResponse = Depends(get_current_user)) -> List[AttendanceSessionResponse]:
    try:
        sid = str(subject_id) if subject_id else None
        return list_sessions(subject_id=sid)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/sessions/{session_id}", response_model=AttendanceSessionResponse)
def get_attendance_session(session_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> AttendanceSessionResponse:
    try:
        return get_session(str(session_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.put("/sessions/{session_id}/start", response_model=AttendanceSessionResponse)
def start_attendance_session(session_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> AttendanceSessionResponse:
    try:
        return start_session(str(session_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/sessions/{session_id}/end", response_model=AttendanceSessionResponse)
def end_attendance_session(session_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> AttendanceSessionResponse:
    try:
        return end_session(str(session_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


class MarkPayload(BaseModel := __import__('pydantic').BaseModel):
    session_id: UUID
    student_id: UUID
    attendance_status: str


@router.post("/mark", response_model=AttendanceRecordResponse)
def mark_attendance_route(payload: MarkPayload, current_user: UserResponse = Depends(get_current_user)) -> AttendanceRecordResponse:
    try:
        return mark_attendance(str(payload.session_id), str(payload.student_id), payload.attendance_status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/records", response_model=List[AttendanceRecordResponse])
def get_session_records(session_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> List[AttendanceRecordResponse]:
    try:
        return get_session_attendance(str(session_id))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
