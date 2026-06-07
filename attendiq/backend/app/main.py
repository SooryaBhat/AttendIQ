# ============================================================
#  AttendIQ — FastAPI Application Entry Point
#  File: backend/app/main.py
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from uuid import uuid4

from app.db.supabase_client import supabase
from app.routes.auth        import router as auth_router
from app.routes.dept_admin  import router as dept_admin_router
from app.routes.student     import router as student_router
from app.routes.faculty     import router as faculty_router
from app.routes.subject     import router as subject_router
from app.routes.attendance  import router as attendance_router
from app.routes.biometric   import router as biometric_router
from app.routes.super_admin import router as super_admin_router
from app.routes.analytics   import router as analytics_router   # NEW
from app.services.auth_service import hash_password
from app.models.user import UserRole

app = FastAPI(
    title="AttendIQ API",
    version="1.0.0",
    description="Backend API for AttendIQ — AI-powered College Attendance System",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dept_admin_router)
app.include_router(student_router)
app.include_router(faculty_router)
app.include_router(subject_router)
app.include_router(attendance_router)
app.include_router(biometric_router)
app.include_router(super_admin_router)
app.include_router(analytics_router)          # NEW


def _seed_demo_users() -> None:
    """Create demo user accounts when no profiles exist."""
    existing = supabase.table("profiles").select("id").limit(1).execute()
    if getattr(existing, "data", None):
        return

    department_id = str(uuid4())
    supabase.table("departments").insert({
        "id": department_id,
        "name": "Computer Science",
        "code": "CSE",
        "description": "Demo Computer Science department",
        "contact_email": "cs@attendiq.edu",
    }).execute()

    demo_users = [
        {
            "id": str(uuid4()),
            "full_name": "Super Admin",
            "email": "super@attendiq.edu",
            "password_hash": hash_password("superadmin123"),
            "role": UserRole.super_admin.value,
            "is_active": True,
            "face_enrolled": False,
            "voice_enrolled": False,
        },
        {
            "id": str(uuid4()),
            "full_name": "Department Admin",
            "email": "deptadmin@attendiq.edu",
            "password_hash": hash_password("deptadmin123"),
            "role": UserRole.department_admin.value,
            "department_id": department_id,
            "is_active": True,
            "face_enrolled": False,
            "voice_enrolled": False,
        },
        {
            "id": str(uuid4()),
            "full_name": "Faculty User",
            "email": "faculty@attendiq.edu",
            "password_hash": hash_password("faculty123"),
            "role": UserRole.faculty.value,
            "department_id": department_id,
            "is_active": True,
            "face_enrolled": False,
            "voice_enrolled": False,
        },
        {
            "id": str(uuid4()),
            "full_name": "Student User",
            "email": "student@attendiq.edu",
            "password_hash": hash_password("student123"),
            "role": UserRole.student.value,
            "department_id": department_id,
            "roll_number": "CSE-2026-001",
            "semester": 1,
            "section": "A",
            "is_active": True,
            "face_enrolled": False,
            "voice_enrolled": False,
        },
    ]

    supabase.table("profiles").insert(demo_users).execute()


@app.on_event("startup")
def startup_event() -> None:
    try:
        _seed_demo_users()
    except Exception as exc:
        print("Failed to seed demo users:", exc)


@app.get("/", tags=["root"])
def read_root() -> dict:
    return {"message": "AttendIQ API Running"}
