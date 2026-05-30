from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from uuid import UUID

from app.dependencies.auth import get_current_user
from app.models.student import (
    StudentCreate,
    StudentResponse,
    StudentUpdate,
)
from app.models.user import UserResponse
from app.services.student_service import (
    create_student,
    delete_student,
    get_student,
    list_students,
    update_student,
)

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=list[StudentResponse])
def get_students(
    search: Optional[str] = None,
    department_id: Optional[UUID] = None,
    current_user: UserResponse = Depends(get_current_user),
) -> list[StudentResponse]:
    try:
        return list_students(
            department_id=str(department_id) if department_id else None,
            search=search,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{student_id}", response_model=StudentResponse)
def get_student_by_id(student_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> StudentResponse:
    try:
        return get_student(str(student_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student_route(payload: StudentCreate, current_user: UserResponse = Depends(get_current_user)) -> StudentResponse:
    try:
        return create_student(payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{student_id}", response_model=StudentResponse)
def update_student_by_id(student_id: UUID, payload: StudentUpdate, current_user: UserResponse = Depends(get_current_user)) -> StudentResponse:
    try:
        return update_student(str(student_id), payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{student_id}")
def delete_student_by_id(student_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        delete_student(str(student_id))
        return {"deleted": True}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
