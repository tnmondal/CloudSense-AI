"""
CloudSense AI — Infrastructure Optimization Router
"""

from typing import Optional
from fastapi import APIRouter, Query, Path
from src.api.services.analytics_service import analytics_service

router = APIRouter(prefix="/optimizations", tags=["Infrastructure Optimization"])


@router.get("", summary="List Prioritized Optimization Recommendations")
async def list_optimizations(
    category: Optional[str] = Query(None, description="Filter: idle_zombie, compute_rightsizing, storage_lifecycle, green_migration"),
    limit: int = Query(50, ge=1, le=100, description="Maximum recommendations to return"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    Returns rule-based FinOps recommendations with current cost, optimized cost,
    and verified monthly and annual ROI savings.
    """
    return analytics_service.get_optimizations(category=category, limit=limit, offset=offset)


@router.get("/{recommendation_id}", summary="Get Specific Optimization Detail")
async def get_optimization_detail(
    recommendation_id: str = Path(..., description="Unique recommendation ID, e.g. REC-RIGHTSIZE-001")
):
    """Returns granular recommendation details, action items, and confidence level."""
    return analytics_service.get_optimization_by_id(recommendation_id=recommendation_id)
