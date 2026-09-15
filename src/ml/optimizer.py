"""
CloudSense AI — Infrastructure Optimization Engine
Implements rule-based, deterministic FinOps optimization detectors
for idle zombies, over-provisioned compute, cold storage lifecycle, and green migration.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from src.analytics.schemas import OptimizationOutput, OptimizationRecommendation


class OptimizationEngine:
    """
    Evaluates cloud estate telemetry against configurable efficiency rules
    and computes quantified monthly and annual ROI for each recommendation.
    """

    DEFAULT_THRESHOLDS = {
        "idle_cpu_threshold_pct": 3.0,
        "idle_ram_threshold_pct": 8.0,
        "idle_min_days": 7,
        "rightsizing_p95_cpu_threshold_pct": 25.0,
        "rightsizing_p95_ram_threshold_pct": 40.0,
        "stale_storage_read_iops_threshold": 0.5,
        "high_carbon_intensity_threshold": 300.0,
    }

    def __init__(self, data_dir: Path, thresholds: Optional[Dict[str, Any]] = None):
        self.data_dir = data_dir
        self.gold_dir = data_dir / "gold"
        self.marts_dir = data_dir / "marts"
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._load_datasets()

    def _load_datasets(self):
        self.fact_cost = pd.read_parquet(self.gold_dir / "fact_cost.parquet")
        self.fact_usage = pd.read_parquet(self.gold_dir / "fact_usage.parquet")
        self.fact_carbon = pd.read_parquet(self.gold_dir / "fact_carbon.parquet")
        self.dim_resource = pd.read_parquet(self.gold_dir / "dim_resource.parquet")
        self.dim_service = pd.read_parquet(self.gold_dir / "dim_service.parquet")
        self.dim_region = pd.read_parquet(self.gold_dir / "dim_region.parquet")

    def generate_recommendations(self) -> List[OptimizationRecommendation]:
        """Scans all resources and evaluates optimization rules."""
        recommendations: List[OptimizationRecommendation] = []
        rec_idx = 1

        # Aggregate resource-level statistics over the full time horizon
        res_summary = self.fact_usage.groupby("resource_id", as_index=False).agg(
            mean_cpu=("avg_cpu_utilization_pct", "mean"),
            p95_cpu=("max_cpu_utilization_pct", lambda x: np.percentile(x, 95)),
            mean_ram=("avg_memory_utilization_pct", "mean"),
            p95_ram=("max_memory_utilization_pct", lambda x: np.percentile(x, 95)),
            total_egress=("network_egress_gb", "sum"),
            mean_read_iops=("disk_read_iops", "mean"),
            idle_days=("is_idle", "sum"),
            total_days=("date_key", "nunique")
        ).merge(
            self.dim_resource, on="resource_id", how="left"
        ).merge(
            self.dim_service[["service_id", "service_family"]], on="service_id", how="left"
        ).merge(
            self.dim_region[["region_id", "region_name", "grid_carbon_intensity_gco2_per_kwh"]], on="region_id", how="left"
        )

        # Merge cost & carbon aggregates
        cost_agg = self.fact_cost.groupby("resource_id")["net_cost_usd"].sum().to_dict()
        carb_agg = self.fact_carbon.groupby("resource_id")["total_carbon_gco2e"].sum().to_dict()

        for _, row in res_summary.iterrows():
            res_id = str(row["resource_id"])
            total_cost = cost_agg.get(res_id, 0.0)
            total_carb_kg = carb_agg.get(res_id, 0.0) / 1000.0
            days = max(row["total_days"], 1)
            
            # Monthly run-rates (normalized to 30 days)
            monthly_cost = (total_cost / days) * 30.0
            monthly_carb = (total_carb_kg / days) * 30.0

            # -----------------------------------------------------------------
            # Rule 1: Idle Zombie Resource Termination
            # -----------------------------------------------------------------
            if row["idle_days"] >= self.thresholds["idle_min_days"] and row["mean_cpu"] < self.thresholds["idle_cpu_threshold_pct"]:
                monthly_savings = round(monthly_cost, 2)  # 100% saved
                annual_savings = round(monthly_savings * 12.0, 2)
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"REC-ZOMBIE-{rec_idx:03d}",
                    rule_triggered="RULE_IDLE_ZOMBIE_TERMINATION",
                    optimization_category="idle_zombie",
                    affected_resource=res_id,
                    resource_name=str(row["resource_name"]),
                    department=str(row["department"]),
                    current_monthly_cost_usd=round(monthly_cost, 2),
                    estimated_optimized_monthly_cost_usd=0.0,
                    estimated_monthly_saving_usd=monthly_savings,
                    estimated_annual_saving_usd=annual_savings,
                    estimated_monthly_carbon_saved_kg=round(monthly_carb, 2),
                    confidence="High (Deterministic)",
                    reason=f"Resource has been idle for {int(row['idle_days'])} days with mean CPU of {row['mean_cpu']:.1f}%.",
                    action_item=f"Terminate or snapshot and delete zombie resource {res_id}."
                ))
                rec_idx += 1
                continue

            # -----------------------------------------------------------------
            # Rule 2: Compute Rightsizing
            # -----------------------------------------------------------------
            if (row["provisioned_vcpu"] >= 4 and 
                row["p95_cpu"] < self.thresholds["rightsizing_p95_cpu_threshold_pct"] and 
                row["p95_ram"] < self.thresholds["rightsizing_p95_ram_threshold_pct"]):
                
                # Downsizing to half core capacity saves ~50%
                monthly_savings = round(monthly_cost * 0.50, 2)
                annual_savings = round(monthly_savings * 12.0, 2)
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"REC-RIGHTSIZE-{rec_idx:03d}",
                    rule_triggered="RULE_COMPUTE_RIGHTSIZING",
                    optimization_category="compute_rightsizing",
                    affected_resource=res_id,
                    resource_name=str(row["resource_name"]),
                    department=str(row["department"]),
                    current_monthly_cost_usd=round(monthly_cost, 2),
                    estimated_optimized_monthly_cost_usd=round(monthly_cost - monthly_savings, 2),
                    estimated_monthly_saving_usd=monthly_savings,
                    estimated_annual_saving_usd=annual_savings,
                    estimated_monthly_carbon_saved_kg=round(monthly_carb * 0.45, 2),
                    confidence="High (P95 Telemetry)",
                    reason=f"P95 peak CPU is only {row['p95_cpu']:.1f}% and RAM is {row['p95_ram']:.1f}% on {int(row['provisioned_vcpu'])} vCPUs.",
                    action_item=f"Downsize {res_id} from {row['resource_type']} to next smaller instance tier."
                ))
                rec_idx += 1
                continue

            # -----------------------------------------------------------------
            # Rule 3: Storage Lifecycle Transition
            # -----------------------------------------------------------------
            if (row["service_family"] == "Storage" and 
                row["resource_type"] == "standard-storage" and 
                row["mean_read_iops"] < self.thresholds["stale_storage_read_iops_threshold"] and 
                row["total_egress"] < 5.0):
                
                # Nearline / Coldline saves ~65%
                monthly_savings = round(monthly_cost * 0.65, 2)
                annual_savings = round(monthly_savings * 12.0, 2)
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"REC-STORAGE-{rec_idx:03d}",
                    rule_triggered="RULE_STORAGE_LIFECYCLE_TIER",
                    optimization_category="storage_lifecycle",
                    affected_resource=res_id,
                    resource_name=str(row["resource_name"]),
                    department=str(row["department"]),
                    current_monthly_cost_usd=round(monthly_cost, 2),
                    estimated_optimized_monthly_cost_usd=round(monthly_cost - monthly_savings, 2),
                    estimated_monthly_saving_usd=monthly_savings,
                    estimated_annual_saving_usd=annual_savings,
                    estimated_monthly_carbon_saved_kg=round(monthly_carb * 0.20, 2),
                    confidence="High (Zero Read Access)",
                    reason=f"Standard storage bucket has near-zero read IOPS ({row['mean_read_iops']:.2f}) and minimal egress.",
                    action_item=f"Configure Object Lifecycle Management on {res_id} to auto-transition to Nearline/Coldline."
                ))
                rec_idx += 1
                continue

            # -----------------------------------------------------------------
            # Rule 4: Green Workload Migration
            # -----------------------------------------------------------------
            if (row["grid_carbon_intensity_gco2_per_kwh"] > self.thresholds["high_carbon_intensity_threshold"] and 
                row["environment"] in ["development", "staging"]):
                
                # Relocating to Zurich (15.3g) or Iowa (132g) eliminates 90%+ carbon at equal or lower cost
                carbon_saved = monthly_carb * 0.90
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"REC-GREEN-{rec_idx:03d}",
                    rule_triggered="RULE_GREEN_WORKLOAD_MIGRATION",
                    optimization_category="green_migration",
                    affected_resource=res_id,
                    resource_name=str(row["resource_name"]),
                    department=str(row["department"]),
                    current_monthly_cost_usd=round(monthly_cost, 2),
                    estimated_optimized_monthly_cost_usd=round(monthly_cost, 2),
                    estimated_monthly_saving_usd=0.0,
                    estimated_annual_saving_usd=0.0,
                    estimated_monthly_carbon_saved_kg=round(carbon_saved, 2),
                    confidence="High (Carbon Arbitrage)",
                    reason=f"Non-production workload hosted in {row['region_name']} with high carbon grid ({row['grid_carbon_intensity_gco2_per_kwh']} g/kWh).",
                    action_item=f"Migrate {res_id} to europe-west6 (Zurich) or us-central1 (Iowa) to eliminate ~90% operational carbon."
                ))
                rec_idx += 1

        return recommendations

    def generate_full_report(self) -> OptimizationOutput:
        """Builds structured Pydantic optimization output."""
        recs = self.generate_recommendations()

        total_mo = sum(r.estimated_monthly_saving_usd for r in recs)
        total_yr = sum(r.estimated_annual_saving_usd for r in recs)
        total_carb = sum(r.estimated_monthly_carbon_saved_kg for r in recs)

        cat_savings = {}
        for r in recs:
            cat_savings[r.optimization_category] = round(
                cat_savings.get(r.optimization_category, 0.0) + r.estimated_monthly_saving_usd, 2
            )

        return OptimizationOutput(
            total_recommendations_count=len(recs),
            total_potential_monthly_savings_usd=round(total_mo, 2),
            total_potential_annual_savings_usd=round(total_yr, 2),
            total_potential_monthly_carbon_saved_kg=round(total_carb, 2),
            savings_by_category=cat_savings,
            recommendations=recs
        )
