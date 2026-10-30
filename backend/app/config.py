"""Application configuration loaded from environment variables."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@lru_cache
def get_settings() -> dict[str, object]:
    """Return cached application settings."""
    origins = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return {
        "app_name": os.getenv("APP_NAME", "DeepGeneLens"),
        "frontend_origins": [origin.strip() for origin in origins.split(",") if origin.strip()],
    }
