# ============================================================
#  AttendIQ — Application Configuration
#  File: backend/app/config.py
# ============================================================

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env file before Pydantic reads environment variables
load_dotenv()


class Settings(BaseSettings):
    """
    Central application settings.
    All values are read from environment variables / .env file.
    Pydantic validates types and raises clearly on missing required fields.
    """

    # ----------------------------------------------------------
    #  Supabase
    # ----------------------------------------------------------
    SUPABASE_URL:               str
    SUPABASE_PUBLISHABLE_KEY:   str

    # ----------------------------------------------------------
    #  JWT Authentication
    # ----------------------------------------------------------
    JWT_SECRET:                 str
    JWT_ALGORITHM:              str = "HS256"
    JWT_EXPIRE_MINUTES:         int = 60 * 8      # 8 hours

    # ----------------------------------------------------------
    #  Application
    # ----------------------------------------------------------
    APP_NAME:                   str = "AttendIQ"
    APP_VERSION:                str = "1.0.0"
    DEBUG:                      bool = False

    # ----------------------------------------------------------
    #  File Upload
    # ----------------------------------------------------------
    UPLOAD_DIR_FACES:           str = "uploads/faces"
    UPLOAD_DIR_AUDIO:           str = "uploads/audio"
    MAX_UPLOAD_SIZE_MB:         int = 20

    # ----------------------------------------------------------
    #  AI Thresholds
    # ----------------------------------------------------------
    FACE_MATCH_TOLERANCE:       float = 0.5    # Lower = stricter match
    VOICE_MATCH_THRESHOLD:      float = 0.75   # Higher = stricter match

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached Settings instance.
    Use this function everywhere instead of instantiating Settings directly.

    Usage:
        from app.config import settings
    """
    return Settings()


# ============================================================
#  Module-level singleton — import this directly anywhere:
#  from app.config import settings
# ============================================================

settings: Settings = get_settings()