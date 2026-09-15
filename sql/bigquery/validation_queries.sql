-- ============================================================================
-- CloudSense AI — BigQuery Validation Queries (Reference)
-- ============================================================================
-- These queries are the SQL reference for the checks implemented
-- programmatically in src/pipeline/bigquery_validation.py. They are kept
-- here for transparency/manual inspection — bigquery_validation.py issues
-- equivalent queries via BigQueryClient.run_query() and compares the
-- results against the local Gold/Mart Parquet files.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Row counts per table (compare against local Parquet row counts)
-- ----------------------------------------------------------------------------
SELECT 'fact_cost' AS table_name, COUNT(*) AS row_count FROM `{dataset}.fact_cost`
UNION ALL
SELECT 'fact_usage', COUNT(*) FROM `{dataset}.fact_usage`
UNION ALL
SELECT 'fact_carbon', COUNT(*) FROM `{dataset}.fact_carbon`
UNION ALL
SELECT 'fact_anomaly', COUNT(*) FROM `{dataset}.fact_anomaly`
UNION ALL
SELECT 'dim_resource', COUNT(*) FROM `{dataset}.dim_resource`;

-- ----------------------------------------------------------------------------
-- Null constraint checks on primary/foreign keys (should always return 0 rows)
-- ----------------------------------------------------------------------------
SELECT COUNT(*) AS null_resource_id_count
FROM `{dataset}.fact_cost`
WHERE resource_id IS NULL;

SELECT COUNT(*) AS null_usage_date_count
FROM `{dataset}.fact_cost`
WHERE usage_date IS NULL;

-- ----------------------------------------------------------------------------
-- Duplicate business-key check on fact_cost
-- (one cost record per resource per day is expected)
-- ----------------------------------------------------------------------------
SELECT resource_id, usage_date, COUNT(*) AS record_count
FROM `{dataset}.fact_cost`
GROUP BY resource_id, usage_date
HAVING COUNT(*) > 1;

-- ----------------------------------------------------------------------------
-- Non-negative cost validity check
-- ----------------------------------------------------------------------------
SELECT COUNT(*) AS negative_cost_rows
FROM `{dataset}.fact_cost`
WHERE list_cost_usd < 0 OR discount_amount_usd < 0 OR net_cost_usd < 0;

-- ----------------------------------------------------------------------------
-- Numeric validity: net cost should equal list cost minus discount
-- (allowing for floating-point tolerance)
-- ----------------------------------------------------------------------------
SELECT COUNT(*) AS pricing_inconsistency_rows
FROM `{dataset}.fact_cost`
WHERE ABS(net_cost_usd - (list_cost_usd - discount_amount_usd)) > 0.01;

-- ----------------------------------------------------------------------------
-- Referential integrity: every fact_cost.resource_id must exist in dim_resource
-- ----------------------------------------------------------------------------
SELECT COUNT(*) AS orphaned_cost_rows
FROM `{dataset}.fact_cost` c
LEFT JOIN `{dataset}.dim_resource` r ON c.resource_id = r.resource_id
WHERE r.resource_id IS NULL;

-- ----------------------------------------------------------------------------
-- Referential integrity: every fact_cost.region_id must exist in dim_region
-- ----------------------------------------------------------------------------
SELECT COUNT(*) AS orphaned_region_rows
FROM `{dataset}.fact_cost` c
LEFT JOIN `{dataset}.dim_region` r ON c.region_id = r.region_id
WHERE r.region_id IS NULL;

-- ----------------------------------------------------------------------------
-- Date range sanity check
-- ----------------------------------------------------------------------------
SELECT MIN(usage_date) AS earliest_date, MAX(usage_date) AS latest_date, COUNT(DISTINCT usage_date) AS distinct_days
FROM `{dataset}.fact_cost`;

-- ----------------------------------------------------------------------------
-- Anomaly ground-truth count (cross-check against fact_anomaly / mart_anomalies)
-- ----------------------------------------------------------------------------
SELECT
  (SELECT COUNT(*) FROM `{dataset}.fact_anomaly`) AS fact_anomaly_row_count,
  (SELECT SUM(incident_days_count) FROM `{dataset}.mart_anomalies`) AS mart_anomaly_incident_days_sum;
