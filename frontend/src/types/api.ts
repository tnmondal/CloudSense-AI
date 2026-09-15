/**
 * TypeScript types mirroring the CloudSense AI FastAPI response schemas.
 * Field names and shapes are taken directly from `src/api/services/analytics_service.py`
 * and verified against live responses from the running backend — nothing here is invented.
 */

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  analytics_data_loaded: boolean;
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export interface DashboardSummary {
  financial_kpis: {
    total_net_spend_usd: number;
    total_list_cost_usd: number;
    total_discounts_usd: number;
    avg_daily_spend_usd: number;
    pricing_consistency_verified: boolean;
  };
  efficiency_kpis: {
    overall_mean_cpu_pct: number;
    overall_p95_cpu_pct: number;
    overall_mean_ram_pct: number;
    overall_p95_ram_pct: number;
    total_compute_hours: number;
    idle_hours_wasted: number;
    idle_dollar_waste_usd: number;
  };
  environmental_kpis: {
    is_estimate: boolean;
    disclaimer: string;
    total_energy_consumed_kwh: number;
    total_carbon_kg_co2e: number;
    total_carbon_metric_tonnes: number;
    scope2_operational_kg: number;
    scope3_embodied_kg: number;
    carbon_intensity_gco2e_per_dollar: number;
  };
  incident_kpis: {
    active_anomalies_count: number;
    anomalies_by_severity: Record<string, number>;
    total_unbudgeted_dollar_surge_usd: number;
  };
  optimization_kpis: {
    total_actionable_recommendations: number;
    total_potential_monthly_savings_usd: number;
    total_potential_annual_savings_usd: number;
    total_monthly_carbon_avoidable_kg: number;
  };
  forecast_kpis: {
    champion_forecasting_model: string;
    projected_next_30_days_spend_usd: number;
  };
}

// ---------------------------------------------------------------------------
// Cost
// ---------------------------------------------------------------------------
export interface CostSummary {
  total_net_cost_usd: number;
  total_list_cost_usd: number;
  total_discounts_usd: number;
  avg_daily_cost_usd: number;
  pricing_consistency_verified: boolean;
}

export interface CostDimensionBreakdown {
  dimension_key: string;
  dimension_value: string;
  list_cost_usd: number;
  discount_amount_usd: number;
  net_cost_usd: number;
  spend_share_pct: number;
  active_resources_count: number;
}

// Only these three dimensions have dedicated REST endpoints
// (GET /cost/by-service, /cost/by-region, /cost/by-department).
export type CostDimension = "service" | "region" | "department";

export interface CostTrendPoint {
  usage_date: string;
  net_cost_usd: number;
  rolling_7d: number;
  rolling_30d: number;
  mom_pct: number;
}

export interface CostResourceItem {
  resource_id: string;
  resource_name: string;
  service_name: string;
  department: string;
  environment: string;
  region_name: string;
  total_net_spend_usd: number;
  avg_daily_spend_usd: number;
  active_days: number;
}

export interface PaginatedCostResources {
  total_items: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: CostResourceItem[];
}

// ---------------------------------------------------------------------------
// Usage / Utilization
// ---------------------------------------------------------------------------
export interface UsageSummary {
  overall_mean_cpu_pct: number;
  overall_p95_cpu_pct: number;
  overall_mean_ram_pct: number;
  overall_p95_ram_pct: number;
  total_compute_hours: number;
  total_idle_hours: number;
  idle_cost_waste_usd: number;
}

export interface ServiceUtilization {
  service_family: string;
  mean_cpu_pct: number;
  p95_cpu_pct: number;
  mean_ram_pct: number;
  p95_ram_pct: number;
  total_compute_hours: number;
  total_storage_gb: number;
  total_network_egress_gb: number;
  total_requests: number;
  idle_resources_count: number;
}

export interface UtilizationCorrelation {
  workload_type: string;
  pearson_correlation: number;
  spearman_correlation: number;
  interpretation: string;
}

// ---------------------------------------------------------------------------
// Anomalies
// ---------------------------------------------------------------------------
export type AnomalySeverity = "Critical" | "High" | "Medium" | "Low";

export interface AnomalyItem {
  anomaly_id: string;
  target_type: string;
  target_id: string;
  service_name: string;
  timestamp: string;
  metric_name: string;
  observed_value: number;
  expected_value: number;
  anomaly_score: number;
  detection_method: string;
  severity: AnomalySeverity;
  financial_impact_usd: number;
  explanation: string;
}

export interface AnomaliesResponse {
  total_anomalies: number;
  total_unbudgeted_dollar_impact: number;
  anomalies_by_severity: Record<AnomalySeverity, number>;
  items: AnomalyItem[];
}

// ---------------------------------------------------------------------------
// Optimizations
// ---------------------------------------------------------------------------
export type OptimizationCategory =
  | "idle_zombie"
  | "compute_rightsizing"
  | "storage_lifecycle"
  | "green_migration";

export interface OptimizationItem {
  recommendation_id: string;
  rule_triggered: string;
  optimization_category: OptimizationCategory | string;
  affected_resource: string;
  resource_name: string;
  department: string;
  current_monthly_cost_usd: number;
  estimated_optimized_monthly_cost_usd: number;
  estimated_monthly_saving_usd: number;
  estimated_annual_saving_usd: number;
  estimated_monthly_carbon_saved_kg: number;
  confidence: string;
  reason: string;
  action_item: string;
}

export interface OptimizationsResponse {
  total_recommendations: number;
  total_potential_monthly_savings_usd: number;
  total_potential_annual_savings_usd: number;
  total_potential_monthly_carbon_saved_kg: number;
  savings_by_category: Record<string, number>;
  items: OptimizationItem[];
}

// ---------------------------------------------------------------------------
// Carbon
// ---------------------------------------------------------------------------
export interface CarbonSummary {
  is_estimate: boolean;
  disclaimer: string;
  total_energy_consumed_kwh: number;
  total_scope2_operational_kg_co2e: number;
  total_scope3_embodied_kg_co2e: number;
  total_carbon_kg_co2e: number;
  avg_carbon_intensity_gco2_per_dollar: number;
  methodology_assumptions: Record<string, unknown>;
}

export interface CarbonRegionBreakdown {
  region_id: string;
  region_name: string;
  grid_intensity_gco2_per_kwh: number;
  energy_consumed_kwh: number;
  scope2_operational_kg_co2e: number;
  scope3_embodied_kg_co2e: number;
  total_carbon_kg_co2e: number;
  carbon_per_dollar_gco2e: number;
}

export interface CarbonTrendPoint {
  usage_date: string;
  energy_kwh: number;
  scope2_kg: number;
  scope3_kg: number;
  total_carbon_kg: number;
  rolling_7d_carbon: number;
}

export interface GreenMigrationSimulation {
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Forecast
// ---------------------------------------------------------------------------
export interface ForecastSummary {
  target_metric: string;
  champion_model: string;
  train_horizon: string;
  test_horizon: string;
  projected_monthly_spend_usd: number;
}

export interface ForecastModelResult {
  model_name: string;
  mae: number;
  rmse: number;
  mape_pct: number;
  train_samples: number;
  test_samples: number;
}

export interface ForecastPredictionPoint {
  date: string;
  predicted_cost_usd: number;
  lower_bound_80_usd: number;
  upper_bound_80_usd: number;
  lower_bound_95_usd: number;
  upper_bound_95_usd: number;
}

export interface ForecastProjections {
  horizon_days: number;
  projected_total_usd: number;
  predictions: ForecastPredictionPoint[];
}

// ---------------------------------------------------------------------------
// AI Context / Tools Manifest
// ---------------------------------------------------------------------------
export interface AiGroundingContext {
  grounding_instruction: string;
  verified_estate_overview: Record<string, number>;
  verified_critical_anomalies: AnomalyItem[];
  verified_top_recommendations: OptimizationItem[];
  verified_regional_carbon_profiles: CarbonRegionBreakdown[];
}

export interface ToolManifestEntry {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface ToolsManifestResponse {
  tools: ToolManifestEntry[];
}

// ---------------------------------------------------------------------------
// AI Copilot Chat
// ---------------------------------------------------------------------------
export interface ChatMessage {
  role: "user" | "model" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  conversation_history?: ChatMessage[];
}

export interface ChatResponse {
  answer: string;
  tools_used: string[];
  analytical_sources: string[];
  relevant_metrics: Record<string, unknown>;
  warnings: string[];
  is_grounded: boolean;
}
