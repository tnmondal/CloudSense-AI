"""
CloudSense AI — Medallion ETL & Transformation Pipeline
Implements Bronze (Raw Ingestion) -> Silver (Clean/Enriched) -> Gold (Dimensional Warehouse)
and builds aggregated Analytics Marts.
"""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Any
import numpy as np
import pandas as pd

from src.pipeline.schema import (
    BRONZE_METADATA_COLS,
    DIM_DATE_SCHEMA,
    DIM_PROVIDER_SCHEMA,
    DIM_REGION_SCHEMA,
    DIM_SERVICE_SCHEMA,
    DIM_RESOURCE_SCHEMA,
    FACT_USAGE_SCHEMA,
    FACT_COST_SCHEMA,
    FACT_CARBON_SCHEMA,
    FACT_ANOMALY_SCHEMA
)


class MedallionETLPipeline:
    """
    Orchestrates the deterministic Medallion ETL transformation
    from raw CSV to Bronze, Silver, Gold dimensional warehouse tables and Analytics Marts.
    """

    def __init__(self, base_data_dir: Path):
        self.base_dir = base_data_dir
        self.bronze_dir = self.base_dir / "bronze"
        self.silver_dir = self.base_dir / "silver"
        self.gold_dir = self.base_dir / "gold"
        self.marts_dir = self.base_dir / "marts"

        # Ensure all layer directories exist
        for d in [self.bronze_dir, self.silver_dir, self.gold_dir, self.marts_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. BRONZE LAYER: Raw Immutable Ingestion
    # -------------------------------------------------------------------------
    def run_bronze_ingestion(self, source_csv_path: Path) -> pd.DataFrame:
        """
        Ingests the raw source CSV immutably, appends ingestion metadata
        (_ingested_at, _batch_id, _source_file, _record_hash), and saves to Parquet.
        """
        print("[Bronze] Ingesting raw immutable dataset...")
        df_raw = pd.read_csv(source_csv_path, low_memory=False)

        batch_id = str(uuid.uuid4())
        ingested_at = datetime.utcnow().isoformat() + "Z"
        source_name = source_csv_path.name

        # Compute deterministic row hashes for lineage
        def compute_hash(row):
            payload = f"{row['record_id']}_{row['usage_date']}_{row['resource_id']}_{row['net_cost_usd']}"
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

        df_bronze = df_raw.copy()
        df_bronze["_ingested_at"] = ingested_at
        df_bronze["_batch_id"] = batch_id
        df_bronze["_source_file"] = source_name
        df_bronze["_record_hash"] = df_bronze.apply(compute_hash, axis=1)

        bronze_output = self.bronze_dir / "bronze_cloud_usage.parquet"
        df_bronze.to_parquet(bronze_output, index=False)
        print(f"[Bronze] Saved {len(df_bronze):,} records to {bronze_output}")
        return df_bronze

    # -------------------------------------------------------------------------
    # 2. SILVER LAYER: Cleaning, Normalization & Business Consistency
    # -------------------------------------------------------------------------
    def run_silver_transformation(self, df_bronze: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans and standardizes records, validates physical and financial bounds,
        deduplicates, and computes standardized silver features.
        """
        print("[Silver] Cleaning, validating, and normalizing records...")
        df = df_bronze.copy()

        # 1. Deduplicate by natural key (usage_date, resource_id)
        init_len = len(df)
        df = df.drop_duplicates(subset=["usage_date", "resource_id"], keep="last")
        if len(df) < init_len:
            print(f"[Silver] Dropped {init_len - len(df)} duplicate records.")

        # 2. Type casting and trimming
        df["usage_date"] = pd.to_datetime(df["usage_date"]).dt.strftime("%Y-%m-%d")
        df["date_key"] = df["usage_date"].str.replace("-", "").astype(np.int64)

        for col in ["project_id", "service_id", "resource_id", "region_id"]:
            df[col] = df[col].astype(str).str.strip()

        # 3. Enforce physical utilization bounds: 0 <= Avg <= Max <= 100
        df["avg_cpu_utilization_pct"] = df["avg_cpu_utilization_pct"].clip(lower=0.0, upper=100.0)
        df["max_cpu_utilization_pct"] = np.maximum(df["avg_cpu_utilization_pct"], df["max_cpu_utilization_pct"].clip(lower=0.0, upper=100.0))
        df["avg_memory_utilization_pct"] = df["avg_memory_utilization_pct"].clip(lower=0.0, upper=100.0)
        df["max_memory_utilization_pct"] = np.maximum(df["avg_memory_utilization_pct"], df["max_memory_utilization_pct"].clip(lower=0.0, upper=100.0))

        # 4. Enforce financial consistency: Net = max(0, List - Discount)
        df["list_cost_usd"] = df["list_cost_usd"].round(4)
        df["discount_amount_usd"] = df["discount_amount_usd"].round(4)
        df["net_cost_usd"] = (df["list_cost_usd"] - df["discount_amount_usd"]).clip(lower=0.0).round(4)

        # 5. Enforce carbon consistency: Total = Scope2 + Scope3
        df["scope2_location_based_gco2e"] = df["scope2_location_based_gco2e"].round(3)
        df["scope3_embodied_gco2e"] = df["scope3_embodied_gco2e"].round(3)
        df["total_carbon_gco2e"] = (df["scope2_location_based_gco2e"] + df["scope3_embodied_gco2e"]).round(3)

        # 6. Silver derived enrichment metrics
        df["cost_per_vcpu_hour"] = np.where(
            df["provisioned_vcpu"] > 0,
            (df["net_cost_usd"] / (df["provisioned_vcpu"] * df["runtime_hours"])).round(4),
            0.0
        )
        df["emissions_per_dollar_usd"] = np.where(
            df["net_cost_usd"] > 0,
            (df["total_carbon_gco2e"] / df["net_cost_usd"]).round(2),
            0.0
        )

        silver_output = self.silver_dir / "silver_cloud_usage.parquet"
        df.to_parquet(silver_output, index=False)
        print(f"[Silver] Saved {len(df):,} cleaned records to {silver_output}")
        return df

    # -------------------------------------------------------------------------
    # 3. GOLD LAYER: Dimensional Star Schema Modeling
    # -------------------------------------------------------------------------
    def run_gold_transformation(self, df_silver: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Decomposes the Silver dataset into Conformed Fact and Dimension tables:
        Dimensions: dim_date, dim_provider, dim_region, dim_service, dim_resource
        Facts: fact_usage, fact_cost, fact_carbon, fact_anomaly
        """
        print("[Gold] Modeling Dimensional Star Schema...")
        gold_tables: Dict[str, pd.DataFrame] = {}

        # --- 3.1 DIM_DATE ---
        unique_dates = pd.to_datetime(df_silver["usage_date"].unique())
        dim_date_records = []
        for dt in unique_dates:
            date_str = dt.strftime("%Y-%m-%d")
            date_key = int(dt.strftime("%Y%m%d"))
            dim_date_records.append({
                "date_key": date_key,
                "full_date": date_str,
                "year": dt.year,
                "quarter": (dt.month - 1) // 3 + 1,
                "month": dt.month,
                "month_name": dt.strftime("%B"),
                "week_of_year": dt.isocalendar()[1],
                "day_of_month": dt.day,
                "day_of_week": dt.weekday(),
                "day_name": dt.strftime("%A"),
                "is_weekend": bool(dt.weekday() >= 5),
                "is_month_end": bool(dt.is_month_end),
            })
        dim_date = pd.DataFrame(dim_date_records).sort_values("date_key").reset_index(drop=True)
        gold_tables["dim_date"] = dim_date

        # --- 3.2 DIM_PROVIDER ---
        dim_provider = pd.DataFrame([{
            "provider_id": "GCP",
            "provider_name": "Google Cloud Platform",
            "cloud_category": "Hyperscaler Public Cloud",
            "headquarters": "Mountain View, California, USA"
        }])
        gold_tables["dim_provider"] = dim_provider

        # --- 3.3 DIM_REGION ---
        dim_region = df_silver[[
            "region_id", "region_name", "pue_factor", "grid_carbon_intensity_gco2_per_kwh"
        ]].drop_duplicates().copy()
        
        # Add static geographic hierarchy
        country_map = {
            "us-central1": ("US", "North America", "High (>80%)"),
            "us-east4": ("US", "North America", "Moderate (40-80%)"),
            "europe-west6": ("CH", "Europe", "High (>80%)"),
            "europe-west1": ("BE", "Europe", "Moderate (40-80%)"),
            "asia-south1": ("IN", "Asia", "Low (<40%)"),
        }
        dim_region["country"] = dim_region["region_id"].map(lambda r: country_map.get(r, ("Unknown", "Unknown", "Unknown"))[0])
        dim_region["continent"] = dim_region["region_id"].map(lambda r: country_map.get(r, ("Unknown", "Unknown", "Unknown"))[1])
        dim_region["renewable_tier"] = dim_region["region_id"].map(lambda r: country_map.get(r, ("Unknown", "Unknown", "Unknown"))[2])
        dim_region = dim_region.sort_values("region_id").reset_index(drop=True)
        gold_tables["dim_region"] = dim_region

        # --- 3.4 DIM_SERVICE ---
        dim_service = df_silver[[
            "service_id", "service_name", "service_family", "pricing_unit"
        ]].drop_duplicates().copy()
        
        pricing_models = {
            "Compute": "Provisioned Core/RAM Allocation",
            "Containers": "Provisioned Cluster Node Pools",
            "Database": "Provisioned Database Instance + Storage",
            "Storage": "Consumptive Storage Volume Tier",
            "Serverless": "Event-Driven Requests + Execution Seconds",
            "Analytics": "On-Demand Query Processing (TB Scanned)",
            "Networking": "Egress Transfer Volume",
        }
        dim_service["pricing_model"] = dim_service["service_family"].map(pricing_models)
        dim_service = dim_service.sort_values("service_id").reset_index(drop=True)
        gold_tables["dim_service"] = dim_service

        # --- 3.5 DIM_RESOURCE ---
        dim_resource = df_silver[[
            "resource_id", "resource_name", "resource_type", "project_id",
            "project_name", "department", "cost_center", "environment",
            "service_id", "region_id", "pricing_tier",
            "provisioned_vcpu", "provisioned_memory_gb", "provisioned_storage_gb"
        ]].drop_duplicates(subset=["resource_id"]).sort_values("resource_id").reset_index(drop=True)
        gold_tables["dim_resource"] = dim_resource

        # --- 3.6 FACT_USAGE ---
        fact_usage = pd.DataFrame({
            "usage_fact_id": [f"f_usg_{i+1:06d}" for i in range(len(df_silver))],
            "date_key": df_silver["date_key"],
            "usage_date": df_silver["usage_date"],
            "resource_id": df_silver["resource_id"],
            "service_id": df_silver["service_id"],
            "region_id": df_silver["region_id"],
            "provider_id": df_silver["cloud_provider"],
            "runtime_hours": df_silver["runtime_hours"],
            "usage_quantity": df_silver["usage_quantity"],
            "pricing_unit": df_silver["pricing_unit"],
            "avg_cpu_utilization_pct": df_silver["avg_cpu_utilization_pct"],
            "max_cpu_utilization_pct": df_silver["max_cpu_utilization_pct"],
            "avg_memory_utilization_pct": df_silver["avg_memory_utilization_pct"],
            "max_memory_utilization_pct": df_silver["max_memory_utilization_pct"],
            "disk_read_iops": df_silver["disk_read_iops"],
            "disk_write_iops": df_silver["disk_write_iops"],
            "network_ingress_gb": df_silver["network_ingress_gb"],
            "network_egress_gb": df_silver["network_egress_gb"],
            "total_requests": df_silver["total_requests"],
            "is_idle": df_silver["is_idle"],
        })
        gold_tables["fact_usage"] = fact_usage

        # --- 3.7 FACT_COST ---
        fact_cost = pd.DataFrame({
            "cost_fact_id": [f"f_cst_{i+1:06d}" for i in range(len(df_silver))],
            "date_key": df_silver["date_key"],
            "usage_date": df_silver["usage_date"],
            "resource_id": df_silver["resource_id"],
            "service_id": df_silver["service_id"],
            "region_id": df_silver["region_id"],
            "provider_id": df_silver["cloud_provider"],
            "pricing_tier": df_silver["pricing_tier"],
            "usage_quantity": df_silver["usage_quantity"],
            "list_unit_price_usd": df_silver["list_unit_price_usd"],
            "list_cost_usd": df_silver["list_cost_usd"],
            "discount_amount_usd": df_silver["discount_amount_usd"],
            "net_cost_usd": df_silver["net_cost_usd"],
            "effective_hourly_rate": np.where(
                df_silver["runtime_hours"] > 0,
                (df_silver["net_cost_usd"] / df_silver["runtime_hours"]).round(4),
                0.0
            ),
        })
        gold_tables["fact_cost"] = fact_cost

        # --- 3.8 FACT_CARBON ---
        fact_carbon = pd.DataFrame({
            "carbon_fact_id": [f"f_crb_{i+1:06d}" for i in range(len(df_silver))],
            "date_key": df_silver["date_key"],
            "usage_date": df_silver["usage_date"],
            "resource_id": df_silver["resource_id"],
            "service_id": df_silver["service_id"],
            "region_id": df_silver["region_id"],
            "provider_id": df_silver["cloud_provider"],
            "runtime_hours": df_silver["runtime_hours"],
            "server_power_avg_watts": df_silver["server_power_avg_watts"],
            "energy_consumed_kwh": df_silver["energy_consumed_kwh"],
            "scope2_location_based_gco2e": df_silver["scope2_location_based_gco2e"],
            "scope3_embodied_gco2e": df_silver["scope3_embodied_gco2e"],
            "total_carbon_gco2e": df_silver["total_carbon_gco2e"],
            "emissions_per_dollar_usd": df_silver["emissions_per_dollar_usd"],
        })
        gold_tables["fact_carbon"] = fact_carbon

        # --- 3.9 FACT_ANOMALY ---
        anom_rows = df_silver[df_silver["anomaly_flag"]].copy()
        
        # Calculate baseline expected cost (median of non-anomaly days for this resource)
        non_anom = df_silver[~df_silver["anomaly_flag"]].groupby("resource_id")["net_cost_usd"].median()
        
        expected_costs = []
        deviations_usd = []
        deviations_pct = []
        severities = []
        root_causes = []

        root_cause_map = {
            "runaway_dev_cluster": "QA load-test cluster provisioned 20 high-spec nodes and omitted auto-shutdown over weekend.",
            "unpartitioned_bigquery_scan": "Ad-hoc query scanned raw audit logs without WHERE partition_date clause.",
            "egress_leak": "Database backup replication dump synced uncompressed cross-region to asia-south1.",
            "storage_log_explosion": "Application deployment set LOG_LEVEL=DEBUG with trace payloads, dumping 85 TB of verbose telemetry.",
            "cpu_spike_dos": "Volumetric layer-7 bot surge saturated serverless endpoints triggering autoscaling concurrency."
        }

        for _, row in anom_rows.iterrows():
            base_exp = non_anom.get(row["resource_id"], row["net_cost_usd"] / 2.0)
            diff_usd = round(row["net_cost_usd"] - base_exp, 4)
            diff_pct = round((diff_usd / max(base_exp, 0.01)) * 100.0, 2)

            if diff_usd > 500 or diff_pct > 300:
                sev = "Critical"
            elif diff_usd > 150 or diff_pct > 150:
                sev = "High"
            else:
                sev = "Medium"

            expected_costs.append(round(base_exp, 4))
            deviations_usd.append(diff_usd)
            deviations_pct.append(diff_pct)
            severities.append(sev)
            root_causes.append(root_cause_map.get(row["anomaly_type"], "Unidentified anomalous operational surge."))

        fact_anomaly = pd.DataFrame({
            "anomaly_fact_id": [f"f_anm_{i+1:04d}" for i in range(len(anom_rows))],
            "date_key": anom_rows["date_key"].values,
            "usage_date": anom_rows["usage_date"].values,
            "resource_id": anom_rows["resource_id"].values,
            "service_id": anom_rows["service_id"].values,
            "region_id": anom_rows["region_id"].values,
            "provider_id": anom_rows["cloud_provider"].values,
            "anomaly_type": anom_rows["anomaly_type"].values,
            "actual_cost_usd": anom_rows["net_cost_usd"].values,
            "expected_cost_usd": expected_costs,
            "deviation_usd": deviations_usd,
            "deviation_pct": deviations_pct,
            "severity": severities,
            "root_cause_description": root_causes,
        })
        gold_tables["fact_anomaly"] = fact_anomaly

        # Save all Gold tables to parquet
        for name, table in gold_tables.items():
            output_path = self.gold_dir / f"{name}.parquet"
            table.to_parquet(output_path, index=False)
            print(f"[Gold] Saved {name} ({len(table):,} rows) -> {output_path}")

        return gold_tables

    # -------------------------------------------------------------------------
    # 4. ANALYTICS MARTS: Pre-Aggregated High-Speed Presentation Marts
    # -------------------------------------------------------------------------
    def run_marts_generation(self, df_silver: pd.DataFrame, gold_tables: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Builds pre-aggregated Analytics Marts for high-speed API serving and dashboarding.
        """
        print("[Marts] Generating Analytics Presentation Marts...")
        marts: Dict[str, pd.DataFrame] = {}

        # --- Mart 1: Cost Summary (by Dept, Project, Service, Region, Environment) ---
        mart_cost_summary = df_silver.groupby(
            ["department", "project_name", "environment", "service_family", "service_name", "region_name"],
            as_index=False
        ).agg(
            total_list_cost_usd=("list_cost_usd", "sum"),
            total_discounts_usd=("discount_amount_usd", "sum"),
            total_net_cost_usd=("net_cost_usd", "sum"),
            avg_daily_net_cost_usd=("net_cost_usd", "mean"),
            total_energy_kwh=("energy_consumed_kwh", "sum"),
            total_carbon_kg=("total_carbon_gco2e", lambda x: x.sum() / 1000.0),
            active_resource_count=("resource_id", "nunique"),
            total_records=("record_id", "count")
        ).round(2)
        marts["mart_cost_summary"] = mart_cost_summary

        # --- Mart 2: Daily Cost Trends (with 7-day & 30-day moving averages) ---
        daily_rollup = df_silver.groupby("usage_date", as_index=False).agg(
            total_net_cost_usd=("net_cost_usd", "sum"),
            total_list_cost_usd=("list_cost_usd", "sum"),
            total_discount_usd=("discount_amount_usd", "sum"),
            total_energy_kwh=("energy_consumed_kwh", "sum"),
            total_carbon_kg=("total_carbon_gco2e", lambda x: x.sum() / 1000.0)
        ).sort_values("usage_date").reset_index(drop=True)

        daily_rollup["rolling_7d_avg_cost"] = daily_rollup["total_net_cost_usd"].rolling(7, min_periods=1).mean().round(2)
        daily_rollup["rolling_30d_avg_cost"] = daily_rollup["total_net_cost_usd"].rolling(30, min_periods=1).mean().round(2)
        daily_rollup["daily_growth_pct"] = (daily_rollup["total_net_cost_usd"].pct_change() * 100.0).fillna(0.0).round(2)
        marts["mart_cost_trends"] = daily_rollup

        # --- Mart 3: Resource Utilization & Rightsizing ---
        mart_utilization = df_silver[df_silver["provisioned_vcpu"] > 0].groupby(
            ["resource_id", "resource_name", "service_name", "resource_type", "department", "environment"],
            as_index=False
        ).agg(
            provisioned_vcpu=("provisioned_vcpu", "first"),
            provisioned_memory_gb=("provisioned_memory_gb", "first"),
            mean_cpu_pct=("avg_cpu_utilization_pct", "mean"),
            p95_cpu_pct=("max_cpu_utilization_pct", lambda x: np.percentile(x, 95)),
            mean_ram_pct=("avg_memory_utilization_pct", "mean"),
            p95_ram_pct=("max_memory_utilization_pct", lambda x: np.percentile(x, 95)),
            total_net_spend_usd=("net_cost_usd", "sum"),
            total_carbon_kg=("total_carbon_gco2e", lambda x: x.sum() / 1000.0),
            idle_days_count=("is_idle", "sum")
        ).round(2)

        mart_utilization["utilization_tier"] = np.where(
            mart_utilization["idle_days_count"] > 100, "Zombie / Abandoned",
            np.where(mart_utilization["p95_cpu_pct"] < 25.0, "Over-Provisioned",
            np.where(mart_utilization["p95_cpu_pct"] > 85.0, "Saturated", "Healthy"))
        )
        marts["mart_resource_utilization"] = mart_utilization

        # --- Mart 4: Anomaly Incidents Summary ---
        fact_anom = gold_tables["fact_anomaly"]
        mart_anomalies = fact_anom.groupby(
            ["anomaly_type", "severity", "root_cause_description"],
            as_index=False
        ).agg(
            incident_days_count=("anomaly_fact_id", "count"),
            affected_resources_count=("resource_id", "nunique"),
            total_actual_cost_usd=("actual_cost_usd", "sum"),
            total_expected_cost_usd=("expected_cost_usd", "sum"),
            total_deviation_usd=("deviation_usd", "sum"),
            avg_deviation_pct=("deviation_pct", "mean"),
            earliest_detected=("usage_date", "min"),
            latest_detected=("usage_date", "max")
        ).round(2)
        marts["mart_anomalies"] = mart_anomalies

        # --- Mart 5: Optimization Opportunities & Savings Potential ---
        opt_candidates = df_silver[df_silver["optimization_category"] != "None"].groupby(
            ["optimization_category", "resource_id", "resource_name", "service_name", "department"],
            as_index=False
        ).agg(
            active_days=("record_id", "count"),
            current_monthly_spend=("net_cost_usd", lambda x: x.sum() / (len(x) / 30.0)),
            current_monthly_carbon_kg=("total_carbon_gco2e", lambda x: (x.sum() / 1000.0) / (len(x) / 30.0)),
        ).round(2)

        savings_ratio = {
            "idle_zombie": 1.00,           # 100% savings from termination
            "compute_rightsizing": 0.50,   # ~50% savings downsizing to next tier
            "storage_lifecycle": 0.65,     # ~65% savings Standard -> Nearline/Coldline
            "green_migration": 0.00        # Neutral cost, 90%+ carbon reduction
        }
        carbon_savings_ratio = {
            "idle_zombie": 1.00,
            "compute_rightsizing": 0.45,
            "storage_lifecycle": 0.20,
            "green_migration": 0.90
        }

        opt_candidates["estimated_monthly_savings_usd"] = (
            opt_candidates["current_monthly_spend"] * opt_candidates["optimization_category"].map(savings_ratio)
        ).round(2)
        opt_candidates["estimated_annual_savings_usd"] = (opt_candidates["estimated_monthly_savings_usd"] * 12.0).round(2)
        opt_candidates["estimated_monthly_carbon_saved_kg"] = (
            opt_candidates["current_monthly_carbon_kg"] * opt_candidates["optimization_category"].map(carbon_savings_ratio)
        ).round(2)

        marts["mart_optimization_opportunities"] = opt_candidates

        # --- Mart 6: Carbon Emissions by Region & Energy Efficiency ---
        mart_carbon = df_silver.groupby(["region_id", "region_name", "grid_carbon_intensity_gco2_per_kwh"], as_index=False).agg(
            total_net_spend_usd=("net_cost_usd", "sum"),
            total_energy_kwh=("energy_consumed_kwh", "sum"),
            scope2_operational_kg=("scope2_location_based_gco2e", lambda x: x.sum() / 1000.0),
            scope3_embodied_kg=("scope3_embodied_gco2e", lambda x: x.sum() / 1000.0),
            total_carbon_kg=("total_carbon_gco2e", lambda x: x.sum() / 1000.0),
        ).round(2)

        mart_carbon["carbon_per_dollar_gco2e"] = (
            (mart_carbon["total_carbon_kg"] * 1000.0) / mart_carbon["total_net_spend_usd"]
        ).round(1)
        marts["mart_carbon_emissions"] = mart_carbon

        # Save all Marts to Parquet
        for name, mart_df in marts.items():
            output_path = self.marts_dir / f"{name}.parquet"
            mart_df.to_parquet(output_path, index=False)
            print(f"[Marts] Saved {name} ({len(mart_df):,} rows) -> {output_path}")

        return marts
