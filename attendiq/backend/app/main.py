# ============================================================
#  AttendIQ — FastAPI Application Entry Point
#  File: backend/app/main.py
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth       import router as auth_router
from app.routes.dept_admin import router as dept_admin_router
from app.routes.student    import router as student_router
from app.routes.faculty    import router as faculty_router
from app.routes.subject    import router as subject_router
from app.routes.attendance import router as attendance_router
from app.routes.biometric  import router as biometric_router   # NEW

app = FastAPI(
    title="AttendIQ API",
    version="1.0.0",
    description="Backend API for AttendIQ — AI-powered College Attendance System",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dept_admin_router)
app.include_router(student_router)
app.include_router(faculty_router)
app.include_router(subject_router)
app.include_router(attendance_router)
app.include_router(biometric_router)   # NEW


@app.get("/", tags=["root"])
def read_root() -> dict:
    return {"message": "AttendIQ API Running"}