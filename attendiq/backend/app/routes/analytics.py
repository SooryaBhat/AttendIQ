# ============================================================
#  AttendIQ — Analytics Routes
#  File: backend/app/routes/analytics.py
#  Provides real data for dept_admin/reports.html and
#  super_admin/reports.html charts and tables.
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from uuid import UUID

from app.dependencies.auth import get_current_user
from app.models.user import UserResponse
from app.db.supabase_client import supabase

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_all_sessions() -> list:
    r = supabase.table("attendance_sessions").select("*").execute()
    return r.data or []


def _get_all_records() -> list:
    r = supabase.table("attendance_records").select("*").execute()
    return r.data or []


def _get_all_students() -> list:
    r = supabase.table("profiles").select("*").eq("role", "student").execute()
    return r.data or []


def _get_all_departments() -> list:
    r = supabase.table("departments").select("*").execute()
    return r.data or []


def _get_all_subjects() -> list:
    r = supabase.table("subjects").select("*").execute()
    return r.data or []


def _get_all_faculty() -> list:
    r = supabase.table("profiles").select("*").eq("role", "faculty").execute()
    return r.data or []


def _attendance_percent(records: list) -> float:
    if not records:
        return 0.0
    present = sum(1 for r in records if r.get("status") == "present")
    return round(present / len(records) * 100, 1)


# ── Shared summary ───────────────────────────────────────────────────────────

@router.get("/summary")
def get_analytics_summary(current_user: UserResponse = Depends(get_current_user)) -> dict:
    """
    General summary endpoint used by dept_admin/reports.html and others.
    Returns system-wide counts.
    """
    try:
        students  = _get_all_students()
        faculty   = _get_all_faculty()
        subjects  = _get_all_subjects()
        sessions  = _get_all_sessions()
        records   = _get_all_records()

        return {
            "total_students": len(students),
            "total_faculty": len(faculty),
            "total_subjects": len(subjects),
            "attendance_sessions": len(sessions),
            "total_records": len(records),
            "overall_attendance_percent": _attendance_percent(records),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Students by department (bar chart) ──────────────────────────────────────

@router.get("/students-by-department")
def students_by_department(current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        departments = _get_all_departments()
        students    = _get_all_students()

        dept_map = {d["id"]: d["name"] for d in departments}
        counts: dict = {}
        for s in students:
            did = s.get("department_id")
            if did:
                name = dept_map.get(did, "Unknown")
                counts[name] = counts.get(name, 0) + 1

        labels = list(counts.keys())
        data   = [counts[l] for l in labels]

        return {"labels": labels, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Attendance trend (line chart — last 30 days) ─────────────────────────────

@router.get("/attendance-trend")
def attendance_trend(current_user: UserResponse = Depends(get_current_user)) -> dict:
    """Returns daily attendance percentage for the last 30 session-days."""
    try:
        sessions = _get_all_sessions()
        records  = _get_all_records()

        # Build a set of unique session dates (sorted, latest 30)
        date_set = sorted({s.get("session_date", "") for s in sessions if s.get("session_date")})[-30:]

        # Map session_id → session_date
        sid_to_date = {s["id"]: s.get("session_date", "") for s in sessions}

        # Bucket records by date
        date_records: dict = {}
        for rec in records:
            sid = rec.get("session_id")
            d   = sid_to_date.get(sid)
            if d and d in date_set:
                date_records.setdefault(d, []).append(rec)

        labels = date_set
        data   = [_attendance_percent(date_records.get(d, [])) for d in date_set]

        return {"labels": labels, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Department comparison (doughnut / bar chart) ─────────────────────────────

@router.get("/department-comparison")
def department_comparison(current_user: UserResponse = Depends(get_current_user)) -> dict:
    """
    Returns per-department attendance percentage for comparison charts.
    """
    try:
        departments = _get_all_departments()
        sessions    = _get_all_sessions()
        records     = _get_all_records()
        subjects    = _get_all_subjects()

        # subject_id → department_id
        sub_dept = {s["id"]: s.get("department_id") for s in subjects}
        # session_id → department_id
        sess_dept = {}
        for sess in sessions:
            sid_dep = sub_dept.get(sess.get("subject_id"))
            if sid_dep:
                sess_dept[sess["id"]] = sid_dep

        dept_records: dict = {}
        for rec in records:
            did = sess_dept.get(rec.get("session_id"))
            if did:
                dept_records.setdefault(did, []).append(rec)

        dept_map = {d["id"]: d["name"] for d in departments}
        labels, data = [], []
        for did, name in dept_map.items():
            recs = dept_records.get(did, [])
            labels.append(name)
            data.append(_attendance_percent(recs))

        return {"labels": labels, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Subject-wise attendance ───────────────────────────────────────────────────

@router.get("/subject-attendance")
def subject_attendance(current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        subjects = _get_all_subjects()
        sessions = _get_all_sessions()
        records  = _get_all_records()

        sub_map  = {s["id"]: s.get("name", "Unknown") for s in subjects}
        sess_sub = {s["id"]: s.get("subject_id") for s in sessions}

        sub_records: dict = {}
        for rec in records:
            subid = sess_sub.get(rec.get("session_id"))
            if subid:
                sub_records.setdefault(subid, []).append(rec)

        labels, data = [], []
        for sid, name in sub_map.items():
            recs = sub_records.get(sid, [])
            labels.append(name)
            data.append(_attendance_percent(recs))

        return {"labels": labels, "data": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Top attendance students ───────────────────────────────────────────────────

@router.get("/top-students")
def top_attendance_students(
    limit: int = 10,
    current_user: UserResponse = Depends(get_current_user)
) -> list:
    return _ranked_students(limit=limit, top=True)


@router.get("/low-students")
def low_attendance_students(
    limit: int = 10,
    current_user: UserResponse = Depends(get_current_user)
) -> list:
    return _ranked_students(limit=limit, top=False)


def _ranked_students(limit: int = 10, top: bool = True) -> list:
    try:
        students    = _get_all_students()
        records     = _get_all_records()
        departments = _get_all_departments()

        dept_map = {d["id"]: d["name"] for d in departments}
        sid_map  = {s["id"]: s for s in students}

        # Group records by student
        student_records: dict = {}
        for rec in records:
            sid = rec.get("student_id")
            if sid:
                student_records.setdefault(sid, []).append(rec)

        ranked = []
        for sid, recs in student_records.items():
            pct = _attendance_percent(recs)
            st  = sid_map.get(sid, {})
            ranked.append({
                "student_id": sid,
                "full_name": st.get("full_name", "Unknown"),
                "email": st.get("email", ""),
                "department_name": dept_map.get(st.get("department_id", ""), "—"),
                "attendance_percent": pct,
                "total_sessions": len(recs),
                "present": sum(1 for r in recs if r.get("status") == "present"),
            })

        ranked.sort(key=lambda x: x["attendance_percent"], reverse=top)
        return ranked[:limit]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
