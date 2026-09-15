"""
CloudSense AI — Health & Readiness Router
"""

from fastapi import APIRouter
from src.api.config import settings

router = APIRouter(prefix="/health", tags=["System Health"])


@router.get("", summary="Service Health & Status Check")
async def health_check():
    """Returns application status, version, and environment configuration."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "analytics_data_loaded": settings.analytics_summary_path.exists()
    }
