# Dependencies package
# ============================================================
#  AttendIQ — Dependencies Package
#  File: backend/app/dependencies/__init__.py
# ============================================================

from app.dependencies.auth import get_current_user

__all__ = ["get_current_user"]
