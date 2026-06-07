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
    create_student_with_activation,
    activate_student_account,
    bulk_import_students,
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


# ============================================================
#  STUDENT ACCOUNT ACTIVATION & BULK IMPORT
# ============================================================

class StudentActivationCreate(BaseModel):
    full_name: str
    email: str
    usn: str
    department_id: UUID
    semester: int
    section: str


from pydantic import BaseModel


class StudentActivationPayload(BaseModel):
    password: str


@router.post("/create-with-activation", status_code=status.HTTP_201_CREATED)
def create_student_activation(payload: StudentActivationCreate, current_user: UserResponse = Depends(get_current_user)) -> dict:
    """
    Create student account with activation token (for dept admins).
    Returns activation token to send to student.
    """
    try:
        token_info = create_student_with_activation(
            full_name=payload.full_name,
            email=payload.email,
            usn=payload.usn,
            department_id=str(payload.department_id),
            semester=payload.semester,
            section=payload.section,
        )
        return token_info
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/activate/{token}", response_model=dict)
def activate_student(token: str, payload: StudentActivationPayload) -> dict:
    """
    Activate a student account using activation token.
    Student sets password and account becomes active.
    """
    try:
        user = activate_student_account(token, payload.password)
        return {
            "success": True,
            "user": user,
            "message": "Account activated successfully. You can now login.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/{department_id}/bulk-import", status_code=status.HTTP_201_CREATED)
def bulk_import_students_route(department_id: UUID, students: list[StudentActivationCreate], current_user: UserResponse = Depends(get_current_user)) -> dict:
    """
    Bulk import students for a department (CSV → JSON).
    Creates accounts with activation tokens.
    Dept admin must distribute activation tokens to students.
    """
    try:
        students_data = [
            {
                "full_name": s.full_name,
                "email": s.email,
                "usn": s.usn,
                "department_id": str(department_id),
                "semester": s.semester,
                "section": s.section,
            }
            for s in students
        ]
        result = bulk_import_students(students_data)
        return result
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
