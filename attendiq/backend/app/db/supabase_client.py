# Supabase connection client (placeholder)
# ============================================================
#  AttendIQ — Supabase Client
#  File: backend/app/db/supabase_client.py
# ============================================================

import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()


def _get_env(key: str) -> str:
    """Read a required environment variable; raise clearly if missing."""
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
    Create and return a reusable Supabase client.

    Uses @lru_cache so the client is instantiated only once
    for the lifetime of the application process.

    Returns:
        supabase.Client: Authenticated Supabase client instance.

    Raises:
        EnvironmentError: If SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY
                          are missing from the environment.
    """
    url: str = _get_env("SUPABASE_URL")
    key: str = _get_env("SUPABASE_PUBLISHABLE_KEY")

    client: Client = create_client(url, key)
    return client


# ============================================================
#  Module-level singleton — import this directly anywhere:
#  from app.db.supabase_client import supabase
# ============================================================

supabase: Client = get_supabase_client()