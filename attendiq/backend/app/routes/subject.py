# ============================================================
#  AttendIQ — Subject Routes  (fixed)
#  join-by-code now uses join_code column via find_subject_by_join_code
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

from app.dependencies.auth import get_current_user
from app.models.subject import SubjectCreate, SubjectResponse, SubjectUpdate
from app.models.user import UserResponse
from app.services.subject_service import (
    create_subject, delete_subject, get_subject, list_subjects,
    update_subject, enroll_student, unenroll_student,
    get_subject_students, get_student_subjects, find_subject_by_join_code,
)

router = APIRouter(prefix="/subjects", tags=["subjects"])


class EnrollPayload(BaseModel):
    student_id: Optional[UUID] = None


class JoinByCodePayload(BaseModel):
    student_id: Optional[UUID] = None
    subject_code: str   # frontend sends join_code as "subject_code"


@router.get("", response_model=list[SubjectResponse])
def get_all_subjects(current_user: UserResponse = Depends(get_current_user)):
    try:
        return list_subjects()
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("/students/{student_id}", response_model=list[SubjectResponse])
def list_student_subjects(student_id: UUID, current_user: UserResponse = Depends(get_current_user)):
    try:
        return get_student_subjects(str(student_id))
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject_by_id(subject_id: UUID, current_user: UserResponse = Depends(get_current_user)):
    try:
        return get_subject(str(subject_id))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.post("", response_model=SubjectResponse, status_code=201)
def create_subject_route(payload: SubjectCreate, current_user: UserResponse = Depends(get_current_user)):
    try:
        return create_subject(payload)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.put("/{subject_id}", response_model=SubjectResponse)
def update_subject_route(subject_id: UUID, payload: SubjectUpdate, current_user: UserResponse = Depends(get_current_user)):
    try:
        return update_subject(str(subject_id), payload)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/{subject_id}")
def delete_subject_route(subject_id: UUID, current_user: UserResponse = Depends(get_current_user)):
    try:
        delete_subject(str(subject_id))
        return {"deleted": True}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/join-by-code", response_model=SubjectResponse)
def join_subject_by_code(payload: JoinByCodePayload, current_user: UserResponse = Depends(get_current_user)):
    try:
        code = payload.subject_code.strip()
        if not code:
            raise HTTPException(400, "subject_code is required.")

        subject = find_subject_by_join_code(code)
        if not subject:
            raise HTTPException(404, f"No subject found with join code '{code}'. Please check the code and try again.")

        subject_id = str(subject["id"])
        student_id = str(payload.student_id) if payload.student_id else str(current_user.id)

        try:
            enroll_student(subject_id, student_id)
        except ValueError as ve:
            msg = str(ve)
            if "already enrolled" in msg.lower():
                # Not an error — return subject details anyway
                return get_subject(subject_id)
            raise HTTPException(400, msg) from ve

        return get_subject(subject_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.post("/{subject_id}/enroll")
def enroll_subject_member(subject_id: UUID, payload: EnrollPayload = None, current_user: UserResponse = Depends(get_current_user)):
    try:
        student_id = str(payload.student_id) if payload and payload.student_id else str(current_user.id)
        created = enroll_student(str(subject_id), student_id)
        return created
    except ValueError as exc:
        msg = str(exc)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(code, msg) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@router.delete("/{subject_id}/unenroll/{student_id}")
def unenroll_subject_member(subject_id: UUID, student_id: UUID, current_user: UserResponse = Depends(get_current_user)):
    try:
        unenroll_student(str(subject_id), str(student_id))
        return {"unenrolled": True}
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{subject_id}/students", response_model=list[UserResponse])
def list_subject_students(subject_id: UUID, current_user: UserResponse = Depends(get_current_user)):
    try:
        return get_subject_students(str(subject_id))
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
