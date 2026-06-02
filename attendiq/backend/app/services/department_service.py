# ============================================================
#  AttendIQ — Department Service
#  File: backend/app/services/department_service.py
#  SDK FIX: See student_service.py header for full explanation.
# ============================================================

import logging
from uuid import uuid4

from app.db.supabase_client import supabase
from app.models.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate

logger = logging.getLogger(__name__)


def _build_department_response(row: dict) -> DepartmentResponse:
    return DepartmentResponse(
        id=row["id"],
        name=row["name"],
        code=row["code"],
        description=row.get("description"),
        created_at=row.get("created_at"),
    )


def list_departments() -> list[DepartmentResponse]:
    response = supabase.table("departments").select("*").execute()
    rows = response.data or []
    return [_build_department_response(r) for r in rows]


def get_department(department_id: str) -> DepartmentResponse:
    response = (
        supabase.table("departments")
        .select("*")
        .eq("id", department_id)
        .single()
        .execute()
    )
    if not response.data:
        raise ValueError("Department not found.")
    return _build_department_response(response.data)


def create_department(payload: DepartmentCreate) -> DepartmentResponse:
    department_data = payload.dict()
    department_data["id"] = str(uuid4())

    # FIX: .insert(data).execute()  — no .select("*")
    response = supabase.table("departments").insert(department_data).execute()

    if not response.data:
        logger.error("create_department: insert returned no data")
        raise RuntimeError("Unable to create department.")

    created = response.data[0] if isinstance(response.data, list) else response.data
    return _build_department_response(created)


def update_department(department_id: str, payload: DepartmentUpdate) -> DepartmentResponse:
    update_data = payload.dict(exclude_unset=True)
    if not update_data:
        raise ValueError("No updates provided.")

    # FIX: .update(data).eq(...).execute()  — no .select("*").single()
    response = (
        supabase.table("departments")
        .update(update_data)
        .eq("id", department_id)
        .execute()
    )
    if not response.data:
        raise ValueError("Department not found.")

    return get_department(department_id)


def delete_department(department_id: str) -> None:
    check = (
        supabase.table("departments")
        .select("id")
        .eq("id", department_id)
        .single()
        .execute()
    )
    if not check.data:
        raise ValueError("Department not found.")

    # FIX: .delete().eq(...).execute()  — no .select()
    supabase.table("departments").delete().eq("id", department_id).execute()