# ============================================================
#  AttendIQ — Supabase Client
#  File: backend/app/db/supabase_client.py
#
#  FIX: Use SUPABASE_SERVICE_ROLE_KEY for all backend queries.
#  The anon/publishable key is blocked by RLS on the server side.
#  The service role key bypasses RLS safely from the backend.
# ============================================================

import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def _get_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"[AttendIQ] Missing required environment variable: '{key}'. "
            f"Check your backend/.env file."
        )
    return value


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Backend Supabase client using the SERVICE ROLE KEY.

    Why service role and not anon key?
    - The anon key respects RLS (Row Level Security).
    - Without RLS policies defined, ALL queries are denied.
    - The service role key bypasses RLS for trusted server-side code.
    - Never expose this key in frontend code.
    """
    url: str = _get_env("SUPABASE_URL")
    key: str = _get_env("SUPABASE_SERVICE_ROLE_KEY")
    
    
    return create_client(url, key)

supabase: Client = get_supabase_client()