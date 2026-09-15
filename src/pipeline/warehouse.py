"""
CloudSense AI — Data Warehouse Adapter & BigQuery Migration Manager
Manages the local DuckDB analytical warehouse over Gold Parquet tables
and provides BigQuery DDL definitions and migration schemas.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import duckdb
import pandas as pd

from src.pipeline.schema import BIGQUERY_SPECS


class WarehouseManager:
    """
    Manages the local analytical warehouse (powered by DuckDB over Parquet)
    and provides unified SQL querying and BigQuery DDL generation.
    """

    def __init__(self, data_dir: Path):
        # Always resolve to an absolute, canonical path derived from the current
        # environment. This guarantees the warehouse is portable across machines:
        # every time a WarehouseManager is instantiated, its views are rebuilt to
        # point at wherever the Gold/Marts Parquet files actually live right now,
        # rather than trusting a path baked in at some prior point in time.
        self.data_dir = Path(data_dir).resolve()
        self.gold_dir = self.data_dir / "gold"
        self.marts_dir = self.data_dir / "marts"
        self.db_path = self.data_dir / "cloudsense_warehouse.duckdb"
        self.conn = duckdb.connect(str(self.db_path))
        self._initialize_warehouse_views()

    def _initialize_warehouse_views(self):
        """
        Creates or replaces views in DuckDB referencing all Gold dimensional tables
        and Analytics Marts directly from Parquet files.
        """
        # Register Gold Tables
        gold_tables = [
            "dim_date", "dim_provider", "dim_region", "dim_service",
            "dim_resource", "fact_usage", "fact_cost", "fact_carbon", "fact_anomaly"
        ]
        for tbl in gold_tables:
            parquet_file = self.gold_dir / f"{tbl}.parquet"
            if parquet_file.exists():
                sql_path = str(parquet_file.resolve()).replace("\\", "/")
                self.conn.execute(f"CREATE OR REPLACE VIEW {tbl} AS SELECT * FROM read_parquet('{sql_path}')")

        # Register Analytics Marts
        marts = [
            "mart_cost_summary", "mart_cost_trends", "mart_resource_utilization",
            "mart_anomalies", "mart_optimization_opportunities", "mart_carbon_emissions"
        ]
        for mart in marts:
            parquet_file = self.marts_dir / f"{mart}.parquet"
            if parquet_file.exists():
                sql_path = str(parquet_file.resolve()).replace("\\", "/")
                self.conn.execute(f"CREATE OR REPLACE VIEW {mart} AS SELECT * FROM read_parquet('{sql_path}')")

    def query(self, sql: str) -> pd.DataFrame:
        """
        Executes a SQL query against the warehouse views and returns a Pandas DataFrame.
        """
        return self.conn.execute(sql).fetchdf()

    def get_table_counts(self) -> Dict[str, int]:
        """
        Returns row counts for all Gold tables and Analytics Marts.
        """
        counts = {}
        tables = [
            "dim_date", "dim_provider", "dim_region", "dim_service", "dim_resource",
            "fact_usage", "fact_cost", "fact_carbon", "fact_anomaly",
            "mart_cost_summary", "mart_cost_trends", "mart_resource_utilization",
            "mart_anomalies", "mart_optimization_opportunities", "mart_carbon_emissions"
        ]
        for tbl in tables:
            try:
                res = self.conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
                counts[tbl] = res[0] if res else 0
            except Exception:
                counts[tbl] = 0
        return counts

    @staticmethod
    def generate_bigquery_ddl() -> str:
        """
        Generates production-grade BigQuery DDL for creating the datasets,
        dimension tables, partitioned fact tables, and clustered views.
        """
        return """-- ============================================================================
-- CloudSense AI: Google BigQuery Production DDL
-- Dataset: cloudsense_dw (Region: US or Multi-Region)
-- Partitioning: usage_date (DAY)
-- Clustering: resource_id, service_id, region_id
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS `cloudsense_dw`
OPTIONS(
  description="CloudSense AI Enterprise FinOps & GreenOps Data Warehouse",
  location="US"
);

-- ----------------------------------------------------------------------------
-- 1. DIMENSION TABLES
-- ----------------------------------------------------------------------------

CREATE OR REPLACE TABLE `cloudsense_dw.dim_date` (
  date_key INT64 NOT NULL,
  full_date DATE NOT NULL,
  year INT64,
  quarter INT64,
  month INT64,
  month_name STRING,
  week_of_year INT64,
  day_of_month INT64,
  day_of_week INT64,
  day_name STRING,
  is_weekend BOOL,
  is_month_end BOOL
)
OPTIONS(description="Conformed Date Dimension with calendar metadata");

CREATE OR REPLACE TABLE `cloudsense_dw.dim_provider` (
  provider_id STRING NOT NULL,
  provider_name STRING,
  cloud_category STRING,
  headquarters STRING
)
OPTIONS(description="Cloud Service Provider Dimension");

CREATE OR REPLACE TABLE `cloudsense_dw.dim_region` (
  region_id STRING NOT NULL,
  region_name STRING,
  country STRING,
  continent STRING,
  pue_factor FLOAT64,
  grid_carbon_intensity_gco2_per_kwh FLOAT64,
  renewable_tier STRING
)
OPTIONS(description="Geographic Data Center & Grid Emission Factor Dimension");

CREATE OR REPLACE TABLE `cloudsense_dw.dim_service` (
  service_id STRING NOT NULL,
  service_name STRING,
  service_family STRING,
  pricing_unit STRING,
  pricing_model STRING
)
OPTIONS(description="Cloud Service Taxonomy & Pricing Model Dimension");

CREATE OR REPLACE TABLE `cloudsense_dw.dim_resource` (
  resource_id STRING NOT NULL,
  resource_name STRING,
  resource_type STRING,
  project_id STRING,
  project_name STRING,
  department STRING,
  cost_center STRING,
  environment STRING,
  service_id STRING,
  region_id STRING,
  pricing_tier STRING,
  provisioned_vcpu FLOAT64,
  provisioned_memory_gb FLOAT64,
  provisioned_storage_gb FLOAT64
)
OPTIONS(description="Cloud Asset & Organizational Ownership Dimension");

-- ----------------------------------------------------------------------------
-- 2. FACT TABLES (Partitioned & Clustered for Query Performance)
-- ----------------------------------------------------------------------------

CREATE OR REPLACE TABLE `cloudsense_dw.fact_usage` (
  usage_fact_id STRING NOT NULL,
  date_key INT64,
  usage_date DATE NOT NULL,
  resource_id STRING,
  service_id STRING,
  region_id STRING,
  provider_id STRING,
  runtime_hours FLOAT64,
  usage_quantity FLOAT64,
  pricing_unit STRING,
  avg_cpu_utilization_pct FLOAT64,
  max_cpu_utilization_pct FLOAT64,
  avg_memory_utilization_pct FLOAT64,
  max_memory_utilization_pct FLOAT64,
  disk_read_iops FLOAT64,
  disk_write_iops FLOAT64,
  network_ingress_gb FLOAT64,
  network_egress_gb FLOAT64,
  total_requests INT64,
  is_idle BOOL
)
PARTITION BY usage_date
CLUSTER BY resource_id, service_id, region_id
OPTIONS(description="Daily Infrastructure Usage & Telemetry Fact Table");

CREATE OR REPLACE TABLE `cloudsense_dw.fact_cost` (
  cost_fact_id STRING NOT NULL,
  date_key INT64,
  usage_date DATE NOT NULL,
  resource_id STRING,
  service_id STRING,
  region_id STRING,
  provider_id STRING,
  pricing_tier STRING,
  usage_quantity FLOAT64,
  list_unit_price_usd FLOAT64,
  list_cost_usd FLOAT64,
  discount_amount_usd FLOAT64,
  net_cost_usd FLOAT64,
  effective_hourly_rate FLOAT64
)
PARTITION BY usage_date
CLUSTER BY resource_id, service_id, region_id
OPTIONS(description="Daily Billing & Financial Line Item Fact Table");

CREATE OR REPLACE TABLE `cloudsense_dw.fact_carbon` (
  carbon_fact_id STRING NOT NULL,
  date_key INT64,
  usage_date DATE NOT NULL,
  resource_id STRING,
  service_id STRING,
  region_id STRING,
  provider_id STRING,
  runtime_hours FLOAT64,
  server_power_avg_watts FLOAT64,
  energy_consumed_kwh FLOAT64,
  scope2_location_based_gco2e FLOAT64,
  scope3_embodied_gco2e FLOAT64,
  total_carbon_gco2e FLOAT64,
  emissions_per_dollar_usd FLOAT64
)
PARTITION BY usage_date
CLUSTER BY region_id, service_id
OPTIONS(description="Daily SPECpower & GHG Protocol Scope 2/3 Carbon Fact Table");

CREATE OR REPLACE TABLE `cloudsense_dw.fact_anomaly` (
  anomaly_fact_id STRING NOT NULL,
  date_key INT64,
  usage_date DATE NOT NULL,
  resource_id STRING,
  service_id STRING,
  region_id STRING,
  provider_id STRING,
  anomaly_type STRING,
  actual_cost_usd FLOAT64,
  expected_cost_usd FLOAT64,
  deviation_usd FLOAT64,
  deviation_pct FLOAT64,
  severity STRING,
  root_cause_description STRING
)
PARTITION BY usage_date
CLUSTER BY severity, anomaly_type, service_id
OPTIONS(description="Operational FinOps Incident & Anomaly Fact Table");
"""

    def close(self):
        """Closes the DuckDB connection."""
        self.conn.close()
