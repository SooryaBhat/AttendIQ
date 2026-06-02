"""
Temporary debug routes for development and troubleshooting.
Remove in production.
"""

import os
from fastapi import APIRouter

from app.db.supabase_client import supabase

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/profiles")
def debug_profiles():
    """
    Temporary debug endpoint to test Supabase connection and profiles table.
    Returns the first profile record or an error.
    """
    try:
        result = supabase.table("profiles").select("*").limit(1).execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/env")
def debug_env():
    """
    Temporary debug endpoint to expose Supabase environment variable state.
    """
    return {
        "url": os.getenv("SUPABASE_URL"),
        "service_key_exists": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "service_key_length": len(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")),
        "publishable_key_length": len(os.getenv("SUPABASE_PUBLISHABLE_KEY", "")),
        "service_key_prefix": os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")[:30],
    }
@router.get("/auth-user")
def debug_auth_user():
    try:
        return {
            "user": supabase.auth.get_user()
        }
    except Exception as e:
        return {"error": str(e)}
    
@router.get("/departments")
def debug_departments():
    try:
        result = supabase.table("departments").select("*").limit(1).execute()
        return {"success": True, "data": result.data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/auth-test")
def debug_auth_test():
    """
    Temporary debug endpoint to test Supabase connection and URL.
    """
    try:
        # Get URL from supabase client
        url_result = {
            "url": str(supabase.supabase_url)
        }
        
        # Query departments table
        result = supabase.table("departments").select("*").limit(1).execute()
        
        # Return both URL and query result
        return {
            "supabase_url": url_result["url"],
            "query_success": True,
            "data": result.data
        }
    except Exception as e:
        return {
            "supabase_url": str(supabase.supabase_url) if hasattr(supabase, 'supabase_url') else None,
            "query_success": False,
            "error": str(e)
        }
