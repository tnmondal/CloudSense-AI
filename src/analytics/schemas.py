"""
CloudSense AI — Analytics & ML Output Schemas
Defines strongly typed Pydantic models for cost analytics, utilization,
carbon estimates, statistical anomalies, forecasting, and optimization recommendations.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# 1. Cost Analytics Schemas
# -----------------------------------------------------------------------------
class CostSummaryRecord(BaseModel):
    dimension_key: str
    dimension_value: str
    list_cost_usd: float
    discount_amount_usd: float
    net_cost_usd: float
    spend_share_pct: float
    active_resources_count: int


class CostAnalyticsOutput(BaseModel):
    total_list_cost_usd: float
    total_discounts_usd: float
    total_net_cost_usd: float
    avg_daily_cost_usd: float
    cost_by_provider: List[CostSummaryRecord]
    cost_by_service: List[CostSummaryRecord]
    cost_by_region: List[CostSummaryRecord]
    cost_by_department: List[CostSummaryRecord]
    cost_by_environment: List[CostSummaryRecord]
    top_expensive_resources: List[Dict[str, Any]]
    daily_spend_trend: List[Dict[str, Any]]
    pricing_consistency_verified: bool


# -----------------------------------------------------------------------------
# 2. Resource Utilization Schemas
# -----------------------------------------------------------------------------
class ServiceUtilizationMetric(BaseModel):
    service_family: str
    mean_cpu_pct: float
    p95_cpu_pct: float
    mean_ram_pct: float
    p95_ram_pct: float
    total_compute_hours: float
    total_storage_gb: float
    total_network_egress_gb: float
    total_requests: int
    idle_resources_count: int


class UtilizationCostCorrelation(BaseModel):
    workload_type: str
    pearson_correlation: float
    spearman_correlation: float
    interpretation: str


class UtilizationAnalyticsOutput(BaseModel):
    overall_mean_cpu_pct: float
    overall_p95_cpu_pct: float
    overall_mean_ram_pct: float
    overall_p95_ram_pct: float
    total_compute_hours: float
    total_idle_hours: float
    idle_cost_waste_usd: float
    service_utilization_breakdown: List[ServiceUtilizationMetric]
    utilization_vs_cost_correlations: List[UtilizationCostCorrelation]


# -----------------------------------------------------------------------------
# 3. Carbon Analytics Schemas
# -----------------------------------------------------------------------------
class RegionalCarbonRecord(BaseModel):
    region_id: str
    region_name: str
    grid_intensity_gco2_per_kwh: float
    energy_consumed_kwh: float
    scope2_operational_kg_co2e: float
    scope3_embodied_kg_co2e: float
    total_carbon_kg_co2e: float
    carbon_per_dollar_gco2e: float


class CarbonAnalyticsOutput(BaseModel):
    is_estimate: bool = True
    disclaimer: str = Field(
        default="All values are engineering estimates derived via SPECpower and GHG Protocol Scope 2 & 3 methodology, not official cloud-provider measurements."
    )
    total_energy_consumed_kwh: float
    total_scope2_operational_kg_co2e: float
    total_scope3_embodied_kg_co2e: float
    total_carbon_kg_co2e: float
    avg_carbon_intensity_gco2_per_dollar: float
    carbon_by_region: List[RegionalCarbonRecord]
    daily_carbon_trend: List[Dict[str, Any]]
    methodology_assumptions: Dict[str, Any]


# -----------------------------------------------------------------------------
# 4. Statistical Anomaly Schemas
# -----------------------------------------------------------------------------
class AnomalyEvent(BaseModel):
    anomaly_id: str
    target_type: str  # "resource" or "service"
    target_id: str
    service_name: str
    timestamp: str
    metric_name: str
    observed_value: float
    expected_value: float
    anomaly_score: float
    detection_method: str
    severity: str  # "Low", "Medium", "High", "Critical"
    financial_impact_usd: float
    explanation: str


class AnomalyDetectionOutput(BaseModel):
    total_anomalies_detected: int
    anomalies_by_severity: Dict[str, int]
    anomalies_by_method: Dict[str, int]
    total_unbudgeted_dollar_impact: float
    detected_anomalies: List[AnomalyEvent]


# -----------------------------------------------------------------------------
# 5. Optimization Engine Schemas
# -----------------------------------------------------------------------------
class OptimizationRecommendation(BaseModel):
    recommendation_id: str
    rule_triggered: str
    optimization_category: str
    affected_resource: str
    resource_name: str
    department: str
    current_monthly_cost_usd: float
    estimated_optimized_monthly_cost_usd: float
    estimated_monthly_saving_usd: float
    estimated_annual_saving_usd: float
    estimated_monthly_carbon_saved_kg: float
    confidence: str
    reason: str
    action_item: str


class OptimizationOutput(BaseModel):
    total_recommendations_count: int
    total_potential_monthly_savings_usd: float
    total_potential_annual_savings_usd: float
    total_potential_monthly_carbon_saved_kg: float
    savings_by_category: Dict[str, float]
    recommendations: List[OptimizationRecommendation]


# -----------------------------------------------------------------------------
# 6. Forecasting Schemas
# -----------------------------------------------------------------------------
class ModelEvaluationMetrics(BaseModel):
    model_name: str
    mae: float
    rmse: float
    mape_pct: float
    train_samples: int
    test_samples: int


class ForecastPoint(BaseModel):
    date: str
    predicted_cost_usd: float
    lower_bound_80_usd: float
    upper_bound_80_usd: float
    lower_bound_95_usd: float
    upper_bound_95_usd: float


class ForecastingOutput(BaseModel):
    target_metric: str = "daily_net_cost_usd"
    champion_model: str
    train_horizon: str
    test_horizon: str
    models_evaluated: List[ModelEvaluationMetrics]
    historical_last_30_days: List[Dict[str, Any]]
    forecast_30_days: List[ForecastPoint]
    forecast_60_days: List[ForecastPoint]
    forecast_90_days: List[ForecastPoint]
    projected_monthly_spend_usd: float
