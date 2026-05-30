from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

from app.dependencies.auth import get_current_user
from app.models.subject import SubjectCreate, SubjectResponse, SubjectUpdate
from app.models.user import UserResponse
from app.services.subject_service import (
    create_subject,
    delete_subject,
    get_subject,
    list_subjects,
    update_subject,
)
from app.services.subject_service import (
    enroll_student,
    unenroll_student,
    get_subject_students,
    get_student_subjects,
)


class EnrollPayload(BaseModel):
    student_id: Optional[UUID] = None


class JoinByCodePayload(BaseModel):
    student_id: Optional[UUID] = None
    subject_code: str

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=list[SubjectResponse])
def get_all_subjects(current_user: UserResponse = Depends(get_current_user)) -> list[SubjectResponse]:
    try:
        return list_subjects()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject_by_id(subject_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> SubjectResponse:
    try:
        return get_subject(str(subject_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject_route(payload: SubjectCreate, current_user: UserResponse = Depends(get_current_user)) -> SubjectResponse:
    try:
        return create_subject(payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/{subject_id}", response_model=SubjectResponse)
def update_subject_by_id(subject_id: UUID, payload: SubjectUpdate, current_user: UserResponse = Depends(get_current_user)) -> SubjectResponse:
    try:
        return update_subject(str(subject_id), payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{subject_id}")
def delete_subject_by_id(subject_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        delete_subject(str(subject_id))
        return {"deleted": True}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{subject_id}/enroll")
def enroll_subject_member(subject_id: UUID, payload: EnrollPayload = None, current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        student_id = str(payload.student_id) if payload and payload.student_id else str(current_user.id)
        created = enroll_student(str(subject_id), student_id)
        return created
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.delete("/{subject_id}/unenroll/{student_id}")
def unenroll_subject_member(subject_id: UUID, student_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        unenroll_student(str(subject_id), str(student_id))
        return {"unenrolled": True}
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{subject_id}/students", response_model=list[UserResponse])
def list_subject_students(subject_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> list[UserResponse]:
    try:
        return get_subject_students(str(subject_id))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/students/{student_id}", response_model=list[SubjectResponse])
def list_student_subjects(student_id: UUID, current_user: UserResponse = Depends(get_current_user)) -> list[SubjectResponse]:
    try:
        return get_student_subjects(str(student_id))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/join-by-code", response_model=SubjectResponse)
def join_subject_by_code(payload: JoinByCodePayload, current_user: UserResponse = Depends(get_current_user)) -> SubjectResponse:
    try:
        code = payload.subject_code.strip()
        if not code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="subject_code is required")

        # find subject by code
        from app.db.supabase_client import supabase

        resp = supabase.table("subjects").select("*").eq("code", code).single().execute()
        if getattr(resp, "error", None):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to lookup subject")
        if not resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found for provided code")

        subject = resp.data
        subject_id = str(subject["id"]) if subject.get("id") else None
        if not subject_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid subject record")

        student_id = str(payload.student_id) if payload.student_id else str(current_user.id)

        # enroll
        enroll_student(subject_id, student_id)

        # return the subject details
        return get_subject(subject_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
