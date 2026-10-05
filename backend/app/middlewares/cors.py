from typing import Any, Dict
from app.core.config import settings


def get_cors_config() -> Dict[str, Any]:
    return {
        "allow_origins": settings.BACKEND_CORS_ORIGINS,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "expose_headers": ["X-Request-ID", "X-Process-Time"],
    }
