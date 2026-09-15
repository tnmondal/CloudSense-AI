-- ============================================================================
-- CloudSense AI — Example Analytical Queries (BigQuery Standard SQL)
-- ============================================================================
-- These are illustrative, ad-hoc queries for exploring the warehouse
-- directly in the BigQuery console — they are NOT executed automatically by
-- any part of the application. Replace `{dataset}` with your actual
-- `project.dataset` (e.g. `my-gcp-project.cloudsense_dw`).
--
-- Reminder: all pricing and carbon figures are synthetic (see
-- src/generator/config.py) — these queries illustrate warehouse structure
-- and partition/cluster-aware query patterns, not real-world FinOps figures.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Top 10 most expensive resources in the last 30 days of the dataset
--    (demonstrates partition pruning on fact_cost.usage_date)
-- ----------------------------------------------------------------------------
SELECT
  r.resource_name,
  s.service_name,
  reg.region_name,
  SUM(c.net_cost_usd) AS total_net_cost_usd
FROM `{dataset}.fact_cost` c
JOIN `{dataset}.dim_resource` r ON c.resource_id = r.resource_id
JOIN `{dataset}.dim_service` s ON c.service_id = s.service_id
JOIN `{dataset}.dim_region` reg ON c.region_id = reg.region_id
WHERE c.usage_date >= DATE_SUB((SELECT MAX(usage_date) FROM `{dataset}.fact_cost`), INTERVAL 30 DAY)
GROUP BY r.resource_name, s.service_name, reg.region_name
ORDER BY total_net_cost_usd DESC
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 2. Daily cost trend with 7-day moving average, computed directly in SQL
--    (cross-check against the pre-computed mart_cost_trends table)
-- ----------------------------------------------------------------------------
SELECT
  usage_date,
  SUM(net_cost_usd) AS daily_net_cost_usd,
  AVG(SUM(net_cost_usd)) OVER (
    ORDER BY usage_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) AS rolling_7d_avg_cost
FROM `{dataset}.fact_cost`
GROUP BY usage_date
ORDER BY usage_date;

-- ----------------------------------------------------------------------------
-- 3. Cost concentration by department and environment
--    (demonstrates clustering benefit on mart_cost_summary)
-- ----------------------------------------------------------------------------
SELECT
  department,
  environment,
  SUM(total_net_cost_usd) AS total_net_cost_usd,
  SAFE_DIVIDE(SUM(total_net_cost_usd), SUM(SUM(total_net_cost_usd)) OVER ()) * 100 AS pct_of_total_spend
FROM `{dataset}.mart_cost_summary`
GROUP BY department, environment
ORDER BY total_net_cost_usd DESC;

-- ----------------------------------------------------------------------------
-- 4. Anomaly financial impact by severity and service
--    (demonstrates clustering benefit on fact_anomaly)
-- ----------------------------------------------------------------------------
SELECT
  a.severity,
  s.service_name,
  COUNT(*) AS anomaly_count,
  SUM(a.deviation_usd) AS total_unbudgeted_dollar_impact
FROM `{dataset}.fact_anomaly` a
JOIN `{dataset}.dim_service` s ON a.service_id = s.service_id
GROUP BY a.severity, s.service_name
ORDER BY total_unbudgeted_dollar_impact DESC;

-- ----------------------------------------------------------------------------
-- 5. Carbon intensity vs. spend by region (GreenOps migration candidates)
-- ----------------------------------------------------------------------------
SELECT
  region_name,
  grid_carbon_intensity_gco2_per_kwh,
  total_net_spend_usd,
  carbon_per_dollar_gco2e
FROM `{dataset}.mart_carbon_emissions`
ORDER BY grid_carbon_intensity_gco2_per_kwh DESC;

-- ----------------------------------------------------------------------------
-- 6. Top optimization opportunities by estimated annual savings
-- ----------------------------------------------------------------------------
SELECT
  optimization_category,
  resource_name,
  department,
  estimated_monthly_savings_usd,
  estimated_annual_savings_usd
FROM `{dataset}.mart_optimization_opportunities`
ORDER BY estimated_annual_savings_usd DESC
LIMIT 20;
