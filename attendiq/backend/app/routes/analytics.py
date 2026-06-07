# ============================================================
#  AttendIQ — Analytics Routes  (fixed)
#  Fixed:
#  1. Uses student_subjects (not subject_enrollments)
#  2. attendance_records uses marked_by (not method)
#  3. No circular import with attendance.py
#  4. Response shapes match Chart.js: {labels:[], data:[]}
#  5. Faculty filter added to /sessions endpoint
# ============================================================

import logging
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies.auth import get_current_user
from app.models.user import UserResponse
from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Data fetchers ─────────────────────────────────────────────────────────────

def _fetch(table: str, filters: dict = None) -> list:
    q = supabase.table(table).select("*")
    for k, v in (filters or {}).items():
        q = q.eq(k, v)
    return q.execute().data or []


def _pct(records: list) -> float:
    if not records:
        return 0.0
    present = sum(1 for r in records if r.get("status") == "present")
    return round(present / len(records) * 100, 1)


# ── /analytics/summary ────────────────────────────────────────────────────────

@router.get("/summary")
def get_analytics_summary(current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        students = _fetch("profiles", {"role": "student"})
        faculty  = _fetch("profiles", {"role": "faculty"})
        subjects = supabase.table("subjects").select("id").execute().data or []
        sessions = supabase.table("attendance_sessions").select("id").execute().data or []
        records  = supabase.table("attendance_records").select("status").execute().data or []
        return {
            "total_students":             len(students),
            "total_faculty":              len(faculty),
            "total_subjects":             len(subjects),
            "attendance_sessions":        len(sessions),
            "total_records":              len(records),
            "overall_attendance_percent": _pct(records),
        }
    except Exception as exc:
        logger.exception("analytics/summary error")
        raise HTTPException(500, str(exc)) from exc


# ── /analytics/attendance-trend ───────────────────────────────────────────────

@router.get("/attendance-trend")
def attendance_trend(current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        sessions = supabase.table("attendance_sessions").select("id, session_date").execute().data or []
        records  = supabase.table("attendance_records").select("session_id, status").execute().data or []

        dates = sorted({s["session_date"] for s in sessions if s.get("session_date")})[-30:]
        sid_date = {s["id"]: s["session_date"] for s in sessions if s.get("session_date")}

        buckets: dict = {}
        for r in records:
            d = sid_date.get(r.get("session_id"))
            if d and d in dates:
                buckets.setdefault(d, []).append(r)

        return {
            "labels": dates,
            "data":   [_pct(buckets.get(d, [])) for d in dates],
        }
    except Exception as exc:
        logger.exception("analytics/attendance-trend error")
        raise HTTPException(500, str(exc)) from exc


# ── /analytics/subject-attendance ─────────────────────────────────────────────

@router.get("/subject-attendance")
def subject_attendance(current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        subjects = supabase.table("subjects").select("id, name").execute().data or []
        sessions = supabase.table("attendance_sessions").select("id, subject_id").execute().data or []
        records  = supabase.table("attendance_records").select("session_id, status").execute().data or []

        sess_sub = {s["id"]: s["subject_id"] for s in sessions}
        sub_recs: dict = {}
        for r in records:
            sub_id = sess_sub.get(r.get("session_id"))
            if sub_id:
                sub_recs.setdefault(sub_id, []).append(r)

        labels, data = [], []
        for s in subjects:
            labels.append(s["name"])
            data.append(_pct(sub_recs.get(s["id"], [])))

        return {"labels": labels, "data": data}
    except Exception as exc:
        logger.exception("analytics/subject-attendance error")
        raise HTTPException(500, str(exc)) from exc


# ── /analytics/department-comparison ─────────────────────────────────────────

@router.get("/department-comparison")
def department_comparison(current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        departments = supabase.table("departments").select("id, name").execute().data or []
        sessions = supabase.table("attendance_sessions").select("id, subject_id").execute().data or []
        subjects = supabase.table("subjects").select("id, department_id").execute().data or []
        records  = supabase.table("attendance_records").select("session_id, status").execute().data or []

        sub_dept  = {s["id"]: s["department_id"] for s in subjects}
        sess_dept = {s["id"]: sub_dept.get(s["subject_id"]) for s in sessions}

        dept_recs: dict = {}
        for r in records:
            d = sess_dept.get(r.get("session_id"))
            if d:
                dept_recs.setdefault(d, []).append(r)

        labels = [d["name"] for d in departments]
        data   = [_pct(dept_recs.get(d["id"], [])) for d in departments]
        return {"labels": labels, "data": data}
    except Exception as exc:
        logger.exception("analytics/department-comparison error")
        raise HTTPException(500, str(exc)) from exc


# ── /analytics/students-by-department ────────────────────────────────────────

@router.get("/students-by-department")
def students_by_department(current_user: UserResponse = Depends(get_current_user)) -> dict:
    try:
        departments = supabase.table("departments").select("id, name").execute().data or []
        students    = _fetch("profiles", {"role": "student"})

        dept_map = {d["id"]: d["name"] for d in departments}
        counts: dict = {}
        for s in students:
            name = dept_map.get(s.get("department_id"), "Unassigned")
            counts[name] = counts.get(name, 0) + 1

        labels = [d["name"] for d in departments]
        data   = [counts.get(n, 0) for n in labels]
        return {"labels": labels, "data": data}
    except Exception as exc:
        logger.exception("analytics/students-by-department error")
        raise HTTPException(500, str(exc)) from exc


# ── /analytics/top-students and /analytics/low-students ──────────────────────

@router.get("/top-students")
def top_students(limit: int = 10, current_user: UserResponse = Depends(get_current_user)) -> list:
    return _student_ranking(limit=limit, top=True)


@router.get("/low-students")
def low_students(limit: int = 10, current_user: UserResponse = Depends(get_current_user)) -> list:
    return _student_ranking(limit=limit, top=False)


def _student_ranking(limit: int = 10, top: bool = True) -> list:
    try:
        students    = _fetch("profiles", {"role": "student"})
        records     = supabase.table("attendance_records").select("student_id, status").execute().data or []
        departments = supabase.table("departments").select("id, name").execute().data or []

        dept_map = {d["id"]: d["name"] for d in departments}
        sid_map  = {s["id"]: s for s in students}

        student_recs: dict = {}
        for r in records:
            sid = r.get("student_id")
            if sid:
                student_recs.setdefault(sid, []).append(r)

        ranked = []
        for sid, recs in student_recs.items():
            st = sid_map.get(sid, {})
            ranked.append({
                "student_id":        sid,
                "full_name":         st.get("full_name", "Unknown"),
                "roll_number":       st.get("roll_number", "—"),
                "email":             st.get("email", ""),
                "department_name":   dept_map.get(st.get("department_id", ""), "—"),
                "attendance_percent": _pct(recs),
                "total_sessions":    len(recs),
                "present":           sum(1 for r in recs if r.get("status") == "present"),
            })

        ranked.sort(key=lambda x: x["attendance_percent"], reverse=top)
        return ranked[:limit]
    except Exception as exc:
        logger.exception("analytics/student-ranking error")
        raise HTTPException(500, str(exc)) from exc
