"""
CloudSense AI — Cost Analytics Router
"""

from typing import Optional
from fastapi import APIRouter, Query
from src.api.services.analytics_service import analytics_service

router = APIRouter(prefix="/cost", tags=["Cost Analytics"])


@router.get("/summary", summary="Total Cost & Macro Metrics")
async def get_cost_summary():
    """Returns total net spend, list cost, realized discounts, and daily averages."""
    return analytics_service.get_cost_summary()


@router.get("/by-service", summary="Spend Breakdown by Cloud Service Family")
async def get_cost_by_service():
    """Returns spend aggregated by service family (Analytics, Compute, Containers, etc.)."""
    return analytics_service.get_cost_by_dimension("service")


@router.get("/by-region", summary="Spend Breakdown by Cloud Region")
async def get_cost_by_region():
    """Returns spend aggregated by geographic cloud region."""
    return analytics_service.get_cost_by_dimension("region")


@router.get("/by-department", summary="Spend Breakdown by Business Department")
async def get_cost_by_department():
    """Returns spend attributed to business units (Engineering, Data & AI, Operations, etc.)."""
    return analytics_service.get_cost_by_dimension("department")


@router.get("/trends", summary="Daily Cost Time Series Trends")
async def get_cost_trends():
    """Returns daily historical net spend with 7-day and 30-day moving averages."""
    return analytics_service.get_cost_trends()


@router.get("/resources", summary="Top Expensive Resources (Paginated & Filterable)")
async def get_cost_resources(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by resource name or ID substring"),
    department: Optional[str] = Query(None, description="Filter by department name")
):
    """Returns top cloud spend assets with search and pagination support."""
    return analytics_service.get_cost_resources(page=page, page_size=page_size, search=search, department=department)
