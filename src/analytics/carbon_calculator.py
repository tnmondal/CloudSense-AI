"""
CloudSense AI — Carbon & GreenOps Analytics Engine
Estimates electrical energy consumption and greenhouse gas emissions (Scope 2 & Scope 3)
using the Cloud Carbon Footprint (CCF) open standard and SPECpower benchmarks.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from src.analytics.schemas import CarbonAnalyticsOutput, RegionalCarbonRecord


class CarbonCalculator:
    """
    Computes engineering estimates for cloud energy consumption (kWh)
    and greenhouse gas emissions (gCO2e / kg CO2e) under GHG Protocol Scope 2 & 3.
    """

    METHODOLOGY_ASSUMPTIONS = {
        "framework": "Cloud Carbon Footprint (CCF) Open Standard & GHG Protocol Corporate Standard",
        "power_model": "SPECpower server benchmark with dynamic CPU utilization scaling",
        "server_idle_power_watts_per_vcpu": 12.50,
        "server_max_power_watts_per_vcpu": 35.00,
        "ram_power_watts_per_gb": 0.38,
        "storage_ssd_power_watts_per_tb": 1.20,
        "datacenter_pue_factors": {
            "us-central1": 1.10,
            "us-east4": 1.12,
            "europe-west6": 1.08,
            "europe-west1": 1.10,
            "asia-south1": 1.15
        },
        "regional_grid_intensity_gco2e_per_kwh": {
            "us-central1 (Iowa)": 132.0,
            "us-east4 (Virginia)": 339.0,
            "europe-west6 (Zurich)": 15.3,
            "europe-west1 (Belgium)": 167.0,
            "asia-south1 (Mumbai)": 712.0
        },
        "embodied_carbon_chassis_kg_co2e": 1200.0,
        "server_depreciation_lifespan_years": 4.0,
        "qualification": "All carbon figures are scientific estimates and not official cloud-provider billed emissions."
    }

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.gold_dir = data_dir / "gold"
        self._load_datasets()

    def _load_datasets(self):
        self.fact_carbon = pd.read_parquet(self.gold_dir / "fact_carbon.parquet")
        self.fact_cost = pd.read_parquet(self.gold_dir / "fact_cost.parquet")
        self.dim_region = pd.read_parquet(self.gold_dir / "dim_region.parquet")
        self.dim_resource = pd.read_parquet(self.gold_dir / "dim_resource.parquet")
        self.dim_service = pd.read_parquet(self.gold_dir / "dim_service.parquet")

        self.joined = self.fact_carbon.merge(
            self.dim_region[["region_id", "region_name", "grid_carbon_intensity_gco2_per_kwh"]],
            on="region_id",
            how="left"
        ).merge(
            self.fact_cost[["cost_fact_id" if "cost_fact_id" in self.fact_cost.columns else "date_key", "resource_id", "date_key", "net_cost_usd"]],
            on=["date_key", "resource_id"],
            how="left"
        ).merge(
            self.dim_service[["service_id", "service_family"]],
            on="service_id",
            how="left"
        )

    def get_carbon_summary(self) -> Dict[str, Any]:
        """Returns fleet-wide electrical energy and Scope 2/Scope 3 emissions totals."""
        total_kwh = float(self.fact_carbon["energy_consumed_kwh"].sum())
        scope2_kg = float(self.fact_carbon["scope2_location_based_gco2e"].sum() / 1000.0)
        scope3_kg = float(self.fact_carbon["scope3_embodied_gco2e"].sum() / 1000.0)
        total_kg = float(self.fact_carbon["total_carbon_gco2e"].sum() / 1000.0)
        total_spend = float(self.joined["net_cost_usd"].sum())

        return {
            "total_energy_consumed_kwh": round(total_kwh, 2),
            "total_scope2_operational_kg_co2e": round(scope2_kg, 2),
            "total_scope3_embodied_kg_co2e": round(scope3_kg, 2),
            "total_carbon_kg_co2e": round(total_kg, 2),
            "total_carbon_metric_tonnes": round(total_kg / 1000.0, 3),
            "avg_carbon_intensity_gco2_per_dollar": round((total_kg * 1000.0) / max(total_spend, 1.0), 1),
            "scope2_ratio_pct": round((scope2_kg / max(total_kg, 0.001)) * 100.0, 1),
            "scope3_ratio_pct": round((scope3_kg / max(total_kg, 0.001)) * 100.0, 1)
        }

    def get_carbon_by_region(self) -> List[RegionalCarbonRecord]:
        """Calculates carbon footprint and carbon efficiency per dollar spend by region."""
        grouped = self.joined.groupby(
            ["region_id", "region_name", "grid_carbon_intensity_gco2_per_kwh"],
            as_index=False
        ).agg(
            energy=("energy_consumed_kwh", "sum"),
            scope2_g=("scope2_location_based_gco2e", "sum"),
            scope3_g=("scope3_embodied_gco2e", "sum"),
            total_g=("total_carbon_gco2e", "sum"),
            spend=("net_cost_usd", "sum")
        )

        records = []
        for _, row in grouped.iterrows():
            total_kg = row["total_g"] / 1000.0
            efficiency = (row["total_g"] / max(row["spend"], 1.0))
            records.append(RegionalCarbonRecord(
                region_id=str(row["region_id"]),
                region_name=str(row["region_name"]),
                grid_intensity_gco2_per_kwh=round(float(row["grid_carbon_intensity_gco2_per_kwh"]), 1),
                energy_consumed_kwh=round(float(row["energy"]), 2),
                scope2_operational_kg_co2e=round(float(row["scope2_g"] / 1000.0), 2),
                scope3_embodied_kg_co2e=round(float(row["scope3_g"] / 1000.0), 2),
                total_carbon_kg_co2e=round(total_kg, 2),
                carbon_per_dollar_gco2e=round(float(efficiency), 1)
            ))

        return sorted(records, key=lambda r: r.total_carbon_kg_co2e, reverse=True)

    def get_daily_carbon_trend(self) -> List[Dict[str, Any]]:
        """Generates daily historical time-series of Scope 2 and Scope 3 emissions."""
        daily = self.fact_carbon.groupby("usage_date", as_index=False).agg(
            energy_kwh=("energy_consumed_kwh", "sum"),
            scope2_kg=("scope2_location_based_gco2e", lambda x: x.sum() / 1000.0),
            scope3_kg=("scope3_embodied_gco2e", lambda x: x.sum() / 1000.0),
            total_carbon_kg=("total_carbon_gco2e", lambda x: x.sum() / 1000.0)
        ).sort_values("usage_date")

        daily["rolling_7d_carbon"] = daily["total_carbon_kg"].rolling(7, min_periods=1).mean()
        daily = daily.fillna(0.0).round(2)
        return daily.to_dict(orient="records")

    def simulate_green_migration(self, workload_resource_id: str, target_region_id: str = "europe-west6") -> Dict[str, Any]:
        """
        Simulates relocating a specific workload from its current region to an ultra-low carbon region.
        """
        res_rows = self.joined[self.joined["resource_id"] == workload_resource_id]
        if len(res_rows) == 0:
            return {"error": f"Workload {workload_resource_id} not found."}

        current_region = res_rows["region_id"].iloc[0]
        total_kwh = res_rows["energy_consumed_kwh"].sum()
        current_scope2_kg = res_rows["scope2_location_based_gco2e"].sum() / 1000.0

        target_grid_map = {"europe-west6": 15.3, "us-central1": 132.0, "europe-west1": 167.0}
        target_grid = target_grid_map.get(target_region_id, 15.3)

        target_scope2_kg = (total_kwh * target_grid) / 1000.0
        reduction_kg = current_scope2_kg - target_scope2_kg
        reduction_pct = (reduction_kg / max(current_scope2_kg, 0.001)) * 100.0

        return {
            "resource_id": workload_resource_id,
            "current_region": current_region,
            "target_region": target_region_id,
            "total_energy_kwh": round(float(total_kwh), 2),
            "current_scope2_kg_co2e": round(float(current_scope2_kg), 2),
            "simulated_scope2_kg_co2e": round(float(target_scope2_kg), 2),
            "carbon_reduction_kg_co2e": round(float(reduction_kg), 2),
            "carbon_reduction_pct": round(float(reduction_pct), 1),
            "recommendation": f"Relocating {workload_resource_id} to {target_region_id} achieves a {reduction_pct:.1f}% operational carbon reduction."
        }

    def generate_full_report(self) -> CarbonAnalyticsOutput:
        """Builds structured Pydantic carbon report."""
        summary = self.get_carbon_summary()
        return CarbonAnalyticsOutput(
            total_energy_consumed_kwh=summary["total_energy_consumed_kwh"],
            total_scope2_operational_kg_co2e=summary["total_scope2_operational_kg_co2e"],
            total_scope3_embodied_kg_co2e=summary["total_scope3_embodied_kg_co2e"],
            total_carbon_kg_co2e=summary["total_carbon_kg_co2e"],
            avg_carbon_intensity_gco2_per_dollar=summary["avg_carbon_intensity_gco2_per_dollar"],
            carbon_by_region=self.get_carbon_by_region(),
            daily_carbon_trend=self.get_daily_carbon_trend(),
            methodology_assumptions=self.METHODOLOGY_ASSUMPTIONS
        )
