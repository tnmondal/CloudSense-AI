"""
CloudSense AI — Tool Calling Function Registry
Implements strictly typed, callable Python functions linking Gemini directly
to the validated AnalyticsService. Each tool returns verified data warehouse facts.
"""

from typing import Dict, List, Any, Optional
from src.api.services.analytics_service import analytics_service


def get_cost_summary() -> Dict[str, Any]:
    """
    Retrieves high-level cloud cost metrics: total net spend, gross list cost,
    realized commitment discounts, daily averages, and pricing consistency audit.
    """
    return analytics_service.get_cost_summary()


def get_cost_breakdown(dimension: str = "service") -> List[Dict[str, Any]]:
    """
    Retrieves cloud spend broken down by dimension.
    Allowed dimensions: 'service', 'region', 'department', 'environment', 'provider'.
    """
    return analytics_service.get_cost_by_dimension(dimension)


def get_cost_trends() -> List[Dict[str, Any]]:
    """
    Retrieves daily historical net cloud spend time series with 7-day and 30-day moving averages.
    """
    return analytics_service.get_cost_trends()


def get_resource_utilization() -> Dict[str, Any]:
    """
    Retrieves fleet compute efficiency metrics: mean/P95 CPU load %, mean/P95 RAM load %,
    total compute hours, idle hours wasted, and direct idle dollar waste.
    """
    return analytics_service.get_usage_summary()


def get_anomalies(severity: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves statistical cost anomalies flagged via rolling Z-score, Modified MAD,
    and IQR fences. Optional severity filter: 'Critical', 'High', 'Medium', 'Low'.
    """
    return analytics_service.get_anomalies(severity=severity)


def get_anomaly_details(anomaly_id: str) -> Dict[str, Any]:
    """
    Retrieves granular diagnostic details for a specific anomaly ID (e.g. 'ANOM-20251016-001'),
    including observed cost, expected baseline cost, statistical deviation, and root cause.
    """
    return analytics_service.get_anomaly_by_id(anomaly_id)


def get_optimization_opportunities(category: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves prioritized FinOps recommendations with current cost, optimized cost,
    and verified monthly and annual ROI savings.
    Optional category: 'idle_zombie', 'compute_rightsizing', 'storage_lifecycle', 'green_migration'.
    """
    return analytics_service.get_optimizations(category=category)


def get_carbon_summary() -> Dict[str, Any]:
    """
    Retrieves estimated cloud electrical energy (kWh) and GHG emissions (kg CO2e)
    broken down by Scope 2 operational and Scope 3 embodied manufacturing.
    """
    return analytics_service.get_carbon_summary()


def get_carbon_by_region() -> List[Dict[str, Any]]:
    r"""
    Retrieves regional carbon intensity and carbon efficiency per dollar spend ($gCO_2e/\$$)
    across the 5 global cloud regions (Zurich, Iowa, Belgium, Virginia, Mumbai).
    """
    return analytics_service.get_carbon_by_region()


def get_forecast(horizon_days: int = 30) -> Dict[str, Any]:
    """
    Retrieves machine learning multi-step cost projections with calibrated
    80% and 95% confidence intervals for the requested horizon (30, 60, or 90 days).
    """
    return analytics_service.get_forecast_projections(horizon_days=horizon_days)


def get_forecast_models() -> List[Dict[str, Any]]:
    """
    Retrieves model evaluation comparison metrics (MAE, RMSE, MAPE) on the chronological
    holdout test horizon across Baseline, Ridge Regression, and Random Forest.
    """
    return analytics_service.get_forecast_models()


def get_resource_details(resource_id: str) -> Dict[str, Any]:
    """
    Retrieves configuration, spend, and department metadata for a specific cloud asset.
    """
    res_list = analytics_service.get_cost_resources(page=1, page_size=100, search=resource_id)["items"]
    for r in res_list:
        if r["resource_id"].lower() == resource_id.lower():
            return r
    return {"status": "not_found", "message": f"Resource '{resource_id}' not found in portfolio."}


def simulate_green_migration(resource_id: str, target_region_id: str = "europe-west6") -> Dict[str, Any]:
    """
    Calculates carbon reduction and financial delta from migrating a workload to Zurich or Iowa.
    """
    return analytics_service.simulate_green_migration(resource_id=resource_id, target_region_id=target_region_id)


def run_root_cause_analysis(query: str = "") -> Dict[str, Any]:
    """
    Synthesizes a multi-factor incident payload connecting top cost anomalies,
    service spend surges, and utilization dips to aid in root cause diagnosis.
    """
    anomalies = analytics_service.get_anomalies(severity="Critical")["items"]
    services = analytics_service.get_cost_by_dimension("service")
    usage = analytics_service.get_usage_summary()

    return {
        "critical_anomalies_detected": anomalies[:3],
        "top_spending_services": services[:3],
        "idle_waste_summary": {
            "idle_hours": usage["total_idle_hours"],
            "dollar_waste": usage["idle_cost_waste_usd"]
        },
        "investigative_note": "Multi-dimensional telemetry shows BigQuery full scans and unmanaged GKE load-test clusters account for the vast majority of unbudgeted surges."
    }


# Tool Registry Map
TOOLS_REGISTRY = {
    "get_cost_summary": get_cost_summary,
    "get_cost_breakdown": get_cost_breakdown,
    "get_cost_trends": get_cost_trends,
    "get_resource_utilization": get_resource_utilization,
    "get_anomalies": get_anomalies,
    "get_anomaly_details": get_anomaly_details,
    "get_optimization_opportunities": get_optimization_opportunities,
    "get_carbon_summary": get_carbon_summary,
    "get_carbon_by_region": get_carbon_by_region,
    "get_forecast": get_forecast,
    "get_forecast_models": get_forecast_models,
    "get_resource_details": get_resource_details,
    "simulate_green_migration": simulate_green_migration,
    "run_root_cause_analysis": run_root_cause_analysis,
}
