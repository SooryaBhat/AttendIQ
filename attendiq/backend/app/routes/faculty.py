from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from uuid import UUID

from app.dependencies.auth import get_current_user
from app.models.faculty import FacultyCreate, FacultyResponse, FacultyUpdate
from app.models.user import UserResponse
from app.services.faculty_service import (
    create_faculty,
    delete_faculty,
    get_faculty,
    list_faculty,
    update_faculty,
)

router = APIRouter(prefix="/faculties", tags=["faculties"])


@router.get("", response_model=list[FacultyResponse])
def get_faculties(
    search: Optional[str] = None,
    department_id: Optional[UUID] = None,
    current_user: UserResponse = Depends(get_current_user),
) -> list[FacultyResponse]:
    try:
        return list_faculty(
            department_id=str(department_id) if department_id else None,
            search=search,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{faculty_id}", response_model=FacultyResponse)
def get_faculty_by_id(faculty_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> FacultyResponse:
    try:
        return get_faculty(str(faculty_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
def create_faculty_route(payload: FacultyCreate, current_user: UserResponse = Depends(get_current_user)) -> FacultyResponse:
    try:
        return create_faculty(payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{faculty_id}", response_model=FacultyResponse)
def update_faculty_by_id(faculty_id: UUID, payload: FacultyUpdate, current_user: UserResponse = Depends(get_current_user)) -> FacultyResponse:
    try:
        return update_faculty(str(faculty_id), payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{faculty_id}")
def delete_faculty_by_id(faculty_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        delete_faculty(str(faculty_id))
        return {"deleted": True}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
