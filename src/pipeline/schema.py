"""
CloudSense AI — Data Warehouse & Pipeline Schema Definitions
Defines schemas, data types, primary/foreign keys, and validation rules
for Medallion layers (Bronze, Silver, Gold) and Analytics Marts.
"""

from typing import Dict, List, Any

# Column definitions and expected data types across layers

BRONZE_METADATA_COLS = [
    "_ingested_at",
    "_batch_id",
    "_source_file",
    "_record_hash"
]

DIM_DATE_SCHEMA = {
    "date_key": "int64",            # YYYYMMDD
    "full_date": "string",          # YYYY-MM-DD
    "year": "int64",
    "quarter": "int64",
    "month": "int64",
    "month_name": "string",
    "week_of_year": "int64",
    "day_of_month": "int64",
    "day_of_week": "int64",         # 0=Monday, 6=Sunday
    "day_name": "string",
    "is_weekend": "bool",
    "is_month_end": "bool"
}

DIM_PROVIDER_SCHEMA = {
    "provider_id": "string",        # PK, e.g. "GCP"
    "provider_name": "string",
    "cloud_category": "string",
    "headquarters": "string"
}

DIM_REGION_SCHEMA = {
    "region_id": "string",          # PK, e.g. "us-central1"
    "region_name": "string",
    "country": "string",
    "continent": "string",
    "pue_factor": "float64",
    "grid_carbon_intensity_gco2_per_kwh": "float64",
    "renewable_tier": "string"
}

DIM_SERVICE_SCHEMA = {
    "service_id": "string",          # PK, e.g. "compute-engine-vm"
    "service_name": "string",
    "service_family": "string",
    "pricing_unit": "string",
    "pricing_model": "string"
}

DIM_RESOURCE_SCHEMA = {
    "resource_id": "string",         # PK
    "resource_name": "string",
    "resource_type": "string",
    "project_id": "string",
    "project_name": "string",
    "department": "string",
    "cost_center": "string",
    "environment": "string",
    "service_id": "string",          # FK -> dim_service
    "region_id": "string",           # FK -> dim_region
    "pricing_tier": "string",
    "provisioned_vcpu": "float64",
    "provisioned_memory_gb": "float64",
    "provisioned_storage_gb": "float64"
}

FACT_USAGE_SCHEMA = {
    "usage_fact_id": "string",       # PK
    "date_key": "int64",             # FK -> dim_date
    "usage_date": "string",
    "resource_id": "string",         # FK -> dim_resource
    "service_id": "string",          # FK -> dim_service
    "region_id": "string",           # FK -> dim_region
    "provider_id": "string",         # FK -> dim_provider
    "runtime_hours": "float64",
    "usage_quantity": "float64",
    "pricing_unit": "string",
    "avg_cpu_utilization_pct": "float64",
    "max_cpu_utilization_pct": "float64",
    "avg_memory_utilization_pct": "float64",
    "max_memory_utilization_pct": "float64",
    "disk_read_iops": "float64",
    "disk_write_iops": "float64",
    "network_ingress_gb": "float64",
    "network_egress_gb": "float64",
    "total_requests": "int64",
    "is_idle": "bool"
}

FACT_COST_SCHEMA = {
    "cost_fact_id": "string",        # PK
    "date_key": "int64",             # FK -> dim_date
    "usage_date": "string",
    "resource_id": "string",         # FK -> dim_resource
    "service_id": "string",          # FK -> dim_service
    "region_id": "string",           # FK -> dim_region
    "provider_id": "string",         # FK -> dim_provider
    "pricing_tier": "string",
    "usage_quantity": "float64",
    "list_unit_price_usd": "float64",
    "list_cost_usd": "float64",
    "discount_amount_usd": "float64",
    "net_cost_usd": "float64",
    "effective_hourly_rate": "float64"
}

FACT_CARBON_SCHEMA = {
    "carbon_fact_id": "string",      # PK
    "date_key": "int64",             # FK -> dim_date
    "usage_date": "string",
    "resource_id": "string",         # FK -> dim_resource
    "service_id": "string",          # FK -> dim_service
    "region_id": "string",           # FK -> dim_region
    "provider_id": "string",         # FK -> dim_provider
    "runtime_hours": "float64",
    "server_power_avg_watts": "float64",
    "energy_consumed_kwh": "float64",
    "scope2_location_based_gco2e": "float64",
    "scope3_embodied_gco2e": "float64",
    "total_carbon_gco2e": "float64",
    "emissions_per_dollar_usd": "float64"
}

FACT_ANOMALY_SCHEMA = {
    "anomaly_fact_id": "string",     # PK
    "date_key": "int64",             # FK -> dim_date
    "usage_date": "string",
    "resource_id": "string",         # FK -> dim_resource
    "service_id": "string",          # FK -> dim_service
    "region_id": "string",           # FK -> dim_region
    "provider_id": "string",         # FK -> dim_provider
    "anomaly_type": "string",
    "actual_cost_usd": "float64",
    "expected_cost_usd": "float64",
    "deviation_usd": "float64",
    "deviation_pct": "float64",
    "severity": "string",
    "root_cause_description": "string"
}

# Analytics Mart schemas — column names/types mirror exactly what
# etl.py::run_marts_generation() actually writes to data/marts/*.parquet
# (verified against the generated Parquet dtypes). No columns are invented.

MART_COST_SUMMARY_SCHEMA = {
    "department": "string",
    "project_name": "string",
    "environment": "string",
    "service_family": "string",
    "service_name": "string",
    "region_name": "string",
    "total_list_cost_usd": "float64",
    "total_discounts_usd": "float64",
    "total_net_cost_usd": "float64",
    "avg_daily_net_cost_usd": "float64",
    "total_energy_kwh": "float64",
    "total_carbon_kg": "float64",
    "active_resource_count": "int64",
    "total_records": "int64"
}

MART_COST_TRENDS_SCHEMA = {
    "usage_date": "string",
    "total_net_cost_usd": "float64",
    "total_list_cost_usd": "float64",
    "total_discount_usd": "float64",
    "total_energy_kwh": "float64",
    "total_carbon_kg": "float64",
    "rolling_7d_avg_cost": "float64",
    "rolling_30d_avg_cost": "float64",
    "daily_growth_pct": "float64"
}

MART_RESOURCE_UTILIZATION_SCHEMA = {
    "resource_id": "string",
    "resource_name": "string",
    "service_name": "string",
    "resource_type": "string",
    "department": "string",
    "environment": "string",
    "provisioned_vcpu": "float64",
    "provisioned_memory_gb": "float64",
    "mean_cpu_pct": "float64",
    "p95_cpu_pct": "float64",
    "mean_ram_pct": "float64",
    "p95_ram_pct": "float64",
    "total_net_spend_usd": "float64",
    "total_carbon_kg": "float64",
    "idle_days_count": "int64",
    "utilization_tier": "string"
}

MART_ANOMALIES_SCHEMA = {
    "anomaly_type": "string",
    "severity": "string",
    "root_cause_description": "string",
    "incident_days_count": "int64",
    "affected_resources_count": "int64",
    "total_actual_cost_usd": "float64",
    "total_expected_cost_usd": "float64",
    "total_deviation_usd": "float64",
    "avg_deviation_pct": "float64",
    "earliest_detected": "string",
    "latest_detected": "string"
}

MART_OPTIMIZATION_OPPORTUNITIES_SCHEMA = {
    "optimization_category": "string",
    "resource_id": "string",
    "resource_name": "string",
    "service_name": "string",
    "department": "string",
    "active_days": "int64",
    "current_monthly_spend": "float64",
    "current_monthly_carbon_kg": "float64",
    "estimated_monthly_savings_usd": "float64",
    "estimated_annual_savings_usd": "float64",
    "estimated_monthly_carbon_saved_kg": "float64"
}

MART_CARBON_EMISSIONS_SCHEMA = {
    "region_id": "string",
    "region_name": "string",
    "grid_carbon_intensity_gco2_per_kwh": "float64",
    "total_net_spend_usd": "float64",
    "total_energy_kwh": "float64",
    "scope2_operational_kg": "float64",
    "scope3_embodied_kg": "float64",
    "total_carbon_kg": "float64",
    "carbon_per_dollar_gco2e": "float64"
}

# Registry mapping table name -> schema dict, used by bigquery_client.py to
# generate DDL and validate loaded data without duplicating column lists.
GOLD_TABLE_SCHEMAS = {
    "dim_date": DIM_DATE_SCHEMA,
    "dim_provider": DIM_PROVIDER_SCHEMA,
    "dim_region": DIM_REGION_SCHEMA,
    "dim_service": DIM_SERVICE_SCHEMA,
    "dim_resource": DIM_RESOURCE_SCHEMA,
    "fact_usage": FACT_USAGE_SCHEMA,
    "fact_cost": FACT_COST_SCHEMA,
    "fact_carbon": FACT_CARBON_SCHEMA,
    "fact_anomaly": FACT_ANOMALY_SCHEMA,
}

MART_TABLE_SCHEMAS = {
    "mart_cost_summary": MART_COST_SUMMARY_SCHEMA,
    "mart_cost_trends": MART_COST_TRENDS_SCHEMA,
    "mart_resource_utilization": MART_RESOURCE_UTILIZATION_SCHEMA,
    "mart_anomalies": MART_ANOMALIES_SCHEMA,
    "mart_optimization_opportunities": MART_OPTIMIZATION_OPPORTUNITIES_SCHEMA,
    "mart_carbon_emissions": MART_CARBON_EMISSIONS_SCHEMA,
}

# BigQuery physical specifications
#
# Facts are date-grained at the transaction/telemetry level and benefit from
# DAY partitioning on usage_date plus clustering on the dimensions most
# commonly filtered/joined on. Marts are already pre-aggregated (one row per
# dimension combination, not one row per day-resource), so most of them are
# small enough that clustering (not partitioning) on their primary grouping
# columns is sufficient — over-partitioning a small, non-date-grained table
# wastes metadata overhead for no pruning benefit. mart_cost_trends is the
# one mart that IS daily-grained, so it is partitioned like the facts.
BIGQUERY_SPECS = {
    # --- Fact tables (unchanged from original spec) ---
    "fact_usage": {
        "partition_field": "usage_date",
        "cluster_fields": ["resource_id", "service_id", "region_id"]
    },
    "fact_cost": {
        "partition_field": "usage_date",
        "cluster_fields": ["resource_id", "service_id", "region_id"]
    },
    "fact_carbon": {
        "partition_field": "usage_date",
        "cluster_fields": ["region_id", "service_id"]
    },
    "fact_anomaly": {
        "partition_field": "usage_date",
        "cluster_fields": ["severity", "anomaly_type", "service_id"]
    },

    # --- Analytics marts (new in Phase 6) ---
    "mart_cost_trends": {
        # The only mart with one row per calendar day — same partitioning
        # rationale as the facts.
        "partition_field": "usage_date",
        "cluster_fields": None
    },
    "mart_cost_summary": {
        # Rolled up by org/service dimensions, not by date. No partition field.
        "partition_field": None,
        "cluster_fields": ["department", "service_family"]
    },
    "mart_resource_utilization": {
        "partition_field": None,
        "cluster_fields": ["department", "environment"]
    },
    "mart_anomalies": {
        "partition_field": None,
        "cluster_fields": ["severity", "anomaly_type"]
    },
    "mart_optimization_opportunities": {
        "partition_field": None,
        "cluster_fields": ["optimization_category", "department"]
    },
    "mart_carbon_emissions": {
        "partition_field": None,
        "cluster_fields": ["region_id"]
    },
}
