"""
CloudSense AI — Executive Dashboard Router
"""

from fastapi import APIRouter
from src.api.services.analytics_service import analytics_service

router = APIRouter(prefix="/dashboard", tags=["Executive Dashboard"])


@router.get("/summary", summary="Executive FinOps & GreenOps KPI Rollup")
async def get_dashboard_summary():
    """
    Returns consolidated high-level KPIs across Financial Spend,
    Resource Utilization, Carbon Emissions, Anomalies, Optimizations, and Forecasts.
    """
    return analytics_service.get_dashboard_summary()
