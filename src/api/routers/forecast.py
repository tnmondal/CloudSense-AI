"""
CloudSense AI — Cost Forecasting Router
"""

from fastapi import APIRouter, Query
from src.api.services.analytics_service import analytics_service

router = APIRouter(prefix="/forecast", tags=["Cost Forecasting"])


@router.get("/summary", summary="Forecasting Overview & Champion Model")
async def get_forecast_summary():
    """Returns champion model name, training/test horizons, and projected 30-day forward spend."""
    return analytics_service.get_forecast_summary()


@router.get("/models", summary="Model Benchmarking & Evaluation Comparison")
async def get_forecast_models():
    """Returns MAE, RMSE, and MAPE metrics on the chronological holdout test set for all models."""
    return analytics_service.get_forecast_models()


@router.get("/projections", summary="Multi-Step Cost Projections with Confidence Cones")
async def get_forecast_projections(
    horizon_days: int = Query(30, ge=1, le=90, description="Forecast horizon in days (30, 60, or 90)")
):
    """Returns daily projected spend with calibrated 80% and 95% confidence intervals."""
    return analytics_service.get_forecast_projections(horizon_days=horizon_days)
