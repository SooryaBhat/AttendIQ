from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from uuid import UUID

from app.dependencies.auth import get_current_user
from app.models.user import UserRegister, UserResponse, UserRole
from app.services.auth_service import (
    delete_user,
    get_user,
    list_users_by_role,
    register_user,
    update_user,
)
from app.services.attendance_service import list_sessions
from app.services.department_service import list_departments
from app.services.faculty_service import list_faculty
from app.services.student_service import list_students
from app.services.subject_service import list_subjects

router = APIRouter(prefix="/super-admin", tags=["super-admin"])


def _ensure_super_admin(current_user: UserResponse) -> None:
    if current_user.role != UserRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required.",
        )


class DepartmentAdminUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    department_id: Optional[UUID] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/admins", response_model=List[UserResponse])
def list_department_admins(
    search: Optional[str] = None,
    department_id: Optional[UUID] = None,
    current_user: UserResponse = Depends(get_current_user),
) -> List[UserResponse]:
    _ensure_super_admin(current_user)
    try:
        return list_users_by_role(
            UserRole.department_admin,
            department_id=str(department_id) if department_id else None,
            search=search,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/admins/{admin_id}", response_model=UserResponse)
def get_department_admin(admin_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    _ensure_super_admin(current_user)
    try:
        return get_user(str(admin_id), role=UserRole.department_admin)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/admins", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_department_admin(payload: UserRegister, current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    _ensure_super_admin(current_user)
    if payload.role != UserRole.department_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be department_admin when creating a department admin.",
        )

    try:
        return register_user(payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/admins/{admin_id}", response_model=UserResponse)
def update_department_admin(
    admin_id: UUID,
    payload: DepartmentAdminUpdate,
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    _ensure_super_admin(current_user)
    try:
        update_data = payload.dict(exclude_unset=True)
        return update_user(str(admin_id), update_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/admins/{admin_id}/activate")
def activate_department_admin(admin_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> dict:
    _ensure_super_admin(current_user)
    try:
        update_user(str(admin_id), {"is_active": True})
        return {"activated": True}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/admins/{admin_id}/deactivate")
def deactivate_department_admin(admin_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> dict:
    _ensure_super_admin(current_user)
    try:
        update_user(str(admin_id), {"is_active": False})
        return {"deactivated": True}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/admins/{admin_id}")
def delete_department_admin(admin_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> dict:
    _ensure_super_admin(current_user)
    try:
        delete_user(str(admin_id))
        return {"deleted": True}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/summary")
def get_super_admin_summary(current_user: UserResponse = Depends(get_current_user)) -> dict:
    _ensure_super_admin(current_user)
    try:
        departments = list_departments()
        admins = list_users_by_role(UserRole.department_admin)
        faculty = list_faculty()
        students = list_students()
        subjects = list_subjects()
        sessions = list_sessions()

        return {
            "total_departments": len(departments),
            "total_department_admins": len(admins),
            "total_faculty": len(faculty),
            "total_students": len(students),
            "total_subjects": len(subjects),
            "total_attendance_sessions": len(sessions),
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


class DepartmentStatsResponse(BaseModel):
    department_id: UUID
    department_name: str
    total_department_admins: int
    total_students: int
    total_faculty: int
    total_subjects: int
    total_sessions: int


@router.get("/department-stats", response_model=List[DepartmentStatsResponse])
def get_department_statistics(current_user: UserResponse = Depends(get_current_user)) -> List[DepartmentStatsResponse]:
    _ensure_super_admin(current_user)
    try:
        departments = list_departments()
        admins = list_users_by_role(UserRole.department_admin)
        students = list_students()
        faculty = list_faculty()
        subjects = list_subjects()
        sessions = list_sessions()

        stats = []
        for department in departments:
            dept_id = str(department.id)
            stats.append(
                DepartmentStatsResponse(
                    department_id=department.id,
                    department_name=department.name,
                    total_department_admins=sum(1 for admin in admins if str(admin.department_id) == dept_id),
                    total_students=sum(1 for student in students if str(student.department_id) == dept_id),
                    total_faculty=sum(1 for member in faculty if str(member.department_id) == dept_id),
                    total_subjects=sum(1 for subject in subjects if str(subject.department_id) == dept_id),
                    total_sessions=sum(1 for session in sessions if str(session.department_id) == dept_id),
                )
            )

        return stats
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
