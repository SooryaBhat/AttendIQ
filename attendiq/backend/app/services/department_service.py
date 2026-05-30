import logging
from uuid import uuid4

from app.db.supabase_client import supabase
from app.models.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)

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
    if getattr(response, "error", None):
        logger.error("Failed to list departments: %s", response.error)
        raise RuntimeError("Unable to fetch departments.")

    rows = response.data or []
    return [_build_department_response(row) for row in rows]


def get_department(department_id: str) -> DepartmentResponse:
    response = (
        supabase.table("departments")
        .select("*")
        .eq("id", department_id)
        .single()
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to fetch department %s: %s", department_id, response.error)
        raise RuntimeError("Unable to fetch department.")

    if not response.data:
        raise ValueError("Department not found.")

    return _build_department_response(response.data)


def create_department(payload: DepartmentCreate) -> DepartmentResponse:
    department_data = payload.dict()
    department_data["id"] = str(uuid4())

    response = (
        supabase.table("departments")
        .insert(department_data)
        .select("*")
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to create department: %s", response.error)
        raise RuntimeError("Unable to create department.")

    created = response.data[0] if isinstance(response.data, list) else response.data
    return _build_department_response(created)


def update_department(department_id: str, payload: DepartmentUpdate) -> DepartmentResponse:
    update_data = payload.dict(exclude_unset=True)
    if not update_data:
        raise ValueError("No updates provided.")

    response = (
        supabase.table("departments")
        .update(update_data)
        .eq("id", department_id)
        .select("*")
        .single()
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to update department %s: %s", department_id, response.error)
        raise RuntimeError("Unable to update department.")

    if not response.data:
        raise ValueError("Department not found.")

    return _build_department_response(response.data)


def delete_department(department_id: str) -> None:
    response = (
        supabase.table("departments")
        .delete()
        .eq("id", department_id)
        .execute()
    )

    if getattr(response, "error", None):
        logger.error("Failed to delete department %s: %s", department_id, response.error)
        raise RuntimeError("Unable to delete department.")

    if not response.data:
        raise ValueError("Department not found.")
