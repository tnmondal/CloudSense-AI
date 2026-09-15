-- ============================================================================
-- CloudSense AI — BigQuery Analytical Views
-- ============================================================================
-- These views are pure SELECTs over the physical Gold fact tables and
-- Analytics Mart tables created by src/pipeline/bigquery_client.py
-- (schema sourced from src/pipeline/schema.py — no columns are invented
-- here that don't already exist in GOLD_TABLE_SCHEMAS / MART_TABLE_SCHEMAS).
--
-- IMPORTANT — synthetic data disclaimer:
-- All pricing, usage, and carbon figures behind these views come from
-- CloudSense AI's synthetic, configurable dataset generator
-- (src/generator/config.py). They are NOT official Google Cloud list
-- prices and NOT official Google Cloud Carbon Footprint measurements.
--
-- This file is parsed by BigQueryClient.create_views_from_file(), which
-- splits it on the "-- view: <name>" markers below. Each view's SELECT
-- statement may reference `{dataset}` as a placeholder for the fully
-- qualified `project.dataset` reference, substituted at creation time.
-- ============================================================================

-- view: v_cost_summary
SELECT
  COUNT(*) AS total_cost_records,
  SUM(list_cost_usd) AS total_list_cost_usd,
  SUM(discount_amount_usd) AS total_discounts_usd,
  SUM(net_cost_usd) AS total_net_cost_usd,
  SAFE_DIVIDE(SUM(net_cost_usd), COUNT(DISTINCT usage_date)) AS avg_daily_net_cost_usd,
  MIN(usage_date) AS earliest_usage_date,
  MAX(usage_date) AS latest_usage_date
FROM `{dataset}.fact_cost`;

-- view: v_cost_by_service
SELECT
  s.service_name,
  s.service_family,
  SUM(c.list_cost_usd) AS total_list_cost_usd,
  SUM(c.discount_amount_usd) AS total_discounts_usd,
  SUM(c.net_cost_usd) AS total_net_cost_usd,
  COUNT(DISTINCT c.resource_id) AS active_resources_count
FROM `{dataset}.fact_cost` c
JOIN `{dataset}.dim_service` s ON c.service_id = s.service_id
GROUP BY s.service_name, s.service_family
ORDER BY total_net_cost_usd DESC;

-- view: v_cost_by_region
SELECT
  r.region_name,
  r.country,
  r.continent,
  SUM(c.list_cost_usd) AS total_list_cost_usd,
  SUM(c.discount_amount_usd) AS total_discounts_usd,
  SUM(c.net_cost_usd) AS total_net_cost_usd,
  COUNT(DISTINCT c.resource_id) AS active_resources_count
FROM `{dataset}.fact_cost` c
JOIN `{dataset}.dim_region` r ON c.region_id = r.region_id
GROUP BY r.region_name, r.country, r.continent
ORDER BY total_net_cost_usd DESC;

-- view: v_cost_by_department
SELECT
  d.department,
  d.environment,
  SUM(c.list_cost_usd) AS total_list_cost_usd,
  SUM(c.discount_amount_usd) AS total_discounts_usd,
  SUM(c.net_cost_usd) AS total_net_cost_usd,
  COUNT(DISTINCT c.resource_id) AS active_resources_count
FROM `{dataset}.fact_cost` c
JOIN `{dataset}.dim_resource` d ON c.resource_id = d.resource_id
GROUP BY d.department, d.environment
ORDER BY total_net_cost_usd DESC;

-- view: v_usage_summary
SELECT
  AVG(avg_cpu_utilization_pct) AS overall_mean_cpu_pct,
  APPROX_QUANTILES(avg_cpu_utilization_pct, 100)[OFFSET(95)] AS overall_p95_cpu_pct,
  AVG(avg_memory_utilization_pct) AS overall_mean_ram_pct,
  APPROX_QUANTILES(avg_memory_utilization_pct, 100)[OFFSET(95)] AS overall_p95_ram_pct,
  SUM(runtime_hours) AS total_compute_hours,
  SUM(CASE WHEN is_idle THEN runtime_hours ELSE 0 END) AS total_idle_hours
FROM `{dataset}.fact_usage`;

-- view: v_service_utilization
SELECT
  s.service_family,
  AVG(u.avg_cpu_utilization_pct) AS mean_cpu_pct,
  APPROX_QUANTILES(u.avg_cpu_utilization_pct, 100)[OFFSET(95)] AS p95_cpu_pct,
  AVG(u.avg_memory_utilization_pct) AS mean_ram_pct,
  APPROX_QUANTILES(u.avg_memory_utilization_pct, 100)[OFFSET(95)] AS p95_ram_pct,
  SUM(u.runtime_hours) AS total_compute_hours,
  SUM(u.network_egress_gb) AS total_network_egress_gb,
  SUM(u.total_requests) AS total_requests,
  COUNTIF(u.is_idle) AS idle_resource_readings_count
FROM `{dataset}.fact_usage` u
JOIN `{dataset}.dim_service` s ON u.service_id = s.service_id
GROUP BY s.service_family
ORDER BY total_compute_hours DESC;

-- view: v_anomalies_active
SELECT
  a.anomaly_fact_id,
  a.usage_date,
  a.anomaly_type,
  a.severity,
  a.actual_cost_usd,
  a.expected_cost_usd,
  a.deviation_usd,
  a.deviation_pct,
  a.root_cause_description,
  res.resource_name,
  svc.service_name,
  reg.region_name
FROM `{dataset}.fact_anomaly` a
JOIN `{dataset}.dim_resource` res ON a.resource_id = res.resource_id
JOIN `{dataset}.dim_service` svc ON a.service_id = svc.service_id
JOIN `{dataset}.dim_region` reg ON a.region_id = reg.region_id
ORDER BY a.usage_date DESC;

-- view: v_optimization_opportunities
SELECT
  optimization_category,
  resource_id,
  resource_name,
  service_name,
  department,
  active_days,
  current_monthly_spend,
  current_monthly_carbon_kg,
  estimated_monthly_savings_usd,
  estimated_annual_savings_usd,
  estimated_monthly_carbon_saved_kg
FROM `{dataset}.mart_optimization_opportunities`
ORDER BY estimated_monthly_savings_usd DESC;

-- view: v_carbon_summary
-- NOTE: carbon figures are synthetic, modeled estimates (see
-- src/generator/config.py for the PUE/grid-intensity assumptions used to
-- generate them) — they are not official Google Cloud Carbon Footprint data.
SELECT
  SUM(energy_consumed_kwh) AS total_energy_consumed_kwh,
  SUM(scope2_location_based_gco2e) AS total_scope2_operational_gco2e,
  SUM(scope3_embodied_gco2e) AS total_scope3_embodied_gco2e,
  SUM(total_carbon_gco2e) AS total_carbon_gco2e,
  SAFE_DIVIDE(SUM(total_carbon_gco2e), NULLIF((SELECT SUM(net_cost_usd) FROM `{dataset}.fact_cost`), 0))
    AS avg_carbon_intensity_gco2_per_dollar
FROM `{dataset}.fact_carbon`;

-- view: v_carbon_by_region
SELECT
  region_id,
  region_name,
  grid_carbon_intensity_gco2_per_kwh,
  total_net_spend_usd,
  total_energy_kwh,
  scope2_operational_kg,
  scope3_embodied_kg,
  total_carbon_kg,
  carbon_per_dollar_gco2e
FROM `{dataset}.mart_carbon_emissions`
ORDER BY total_carbon_kg DESC;

-- view: v_forecast_inputs
-- Provides the clean daily net-cost time series consumed by the existing
-- Python forecaster (src/ml/forecaster.py reads mart_cost_trends.parquet
-- locally with these exact columns). Forecasting logic itself intentionally
-- remains in Python (Ridge/RandomForest via scikit-learn) — this view does
-- not attempt to reimplement forecasting in SQL.
SELECT
  usage_date,
  total_net_cost_usd,
  rolling_7d_avg_cost,
  rolling_30d_avg_cost,
  daily_growth_pct
FROM `{dataset}.mart_cost_trends`
ORDER BY usage_date;
