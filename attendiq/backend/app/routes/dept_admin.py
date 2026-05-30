from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from app.dependencies.auth import get_current_user
from app.models.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.models.user import UserResponse
from app.services.department_service import (
    create_department,
    delete_department,
    get_department,
    list_departments,
    update_department,
)

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentResponse])
def get_departments(current_user: UserResponse = Depends(get_current_user)) -> list[DepartmentResponse]:
    try:
        return list_departments()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department_by_id(department_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> DepartmentResponse:
    try:
        return get_department(str(department_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department_route(payload: DepartmentCreate, current_user: UserResponse = Depends(get_current_user)) -> DepartmentResponse:
    try:
        return create_department(payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department_by_id(department_id: UUID, payload: DepartmentUpdate, current_user: UserResponse = Depends(get_current_user)) -> DepartmentResponse:
    try:
        return update_department(str(department_id), payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{department_id}")
def delete_department_by_id(department_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        delete_department(str(department_id))
        return {"deleted": True}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
