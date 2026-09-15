"""
CloudSense AI — Resource Utilization Router
"""

from fastapi import APIRouter
from src.api.services.analytics_service import analytics_service

router = APIRouter(prefix="/usage", tags=["Resource Utilization"])


@router.get("/summary", summary="Global Fleet Utilization & Waste Overview")
async def get_usage_summary():
    """Returns global mean and P95 CPU/RAM load, total compute hours, and idle cost waste."""
    return analytics_service.get_usage_summary()


@router.get("/services", summary="Utilization Profiles by Service Family")
async def get_service_utilization():
    """Returns CPU, RAM, storage, and request metrics across all cloud service families."""
    return analytics_service.get_service_utilization()


@router.get("/correlations", summary="Empirical Load-to-Cost Correlations")
async def get_utilization_correlations():
    """Returns Pearson and Spearman correlation analysis demonstrating billing elasticity."""
    return analytics_service.get_utilization_correlations()
