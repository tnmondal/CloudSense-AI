"""
CloudSense AI — Statistical Anomalies Router
"""

from typing import Optional
from fastapi import APIRouter, Query, Path
from src.api.services.analytics_service import analytics_service

router = APIRouter(prefix="/anomalies", tags=["Statistical Anomalies"])


@router.get("", summary="List Detected Statistical Anomalies")
async def list_anomalies(
    severity: Optional[str] = Query(None, description="Filter by severity: Critical, High, Medium, Low"),
    limit: int = Query(50, ge=1, le=100, description="Maximum anomalies to return"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    Returns verified statistical anomalies flagged via rolling Z-score,
    Modified MAD, and IQR consensus, with total unbudgeted financial impact.
    """
    return analytics_service.get_anomalies(severity=severity, limit=limit, offset=offset)


@router.get("/{anomaly_id}", summary="Get Detailed Anomaly Diagnostic Payload")
async def get_anomaly_detail(
    anomaly_id: str = Path(..., description="Unique anomaly identifier, e.g. ANOM-20251016-001")
):
    """Returns granular diagnostic information, observed vs expected spend, and root-cause analysis."""
    return analytics_service.get_anomaly_by_id(anomaly_id=anomaly_id)
