"""
CloudSense AI — Resource Utilization Analytics Engine
Computes utilization distributions across CPU, RAM, IOPS, Egress, and Requests,
and uncovers empirical relationships between physical load and financial cost.
"""

from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import pandas as pd
from scipy import stats

from src.analytics.schemas import (
    UtilizationAnalyticsOutput,
    ServiceUtilizationMetric,
    UtilizationCostCorrelation
)


class UsageAnalyzer:
    """
    Analyzes physical resource utilization telemetry, correlates utilization with spend,
    and quantifies operational waste from idle or saturated infrastructure.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.gold_dir = data_dir / "gold"
        self._load_datasets()

    def _load_datasets(self):
        self.fact_usage = pd.read_parquet(self.gold_dir / "fact_usage.parquet")
        self.fact_cost = pd.read_parquet(self.gold_dir / "fact_cost.parquet")
        self.dim_service = pd.read_parquet(self.gold_dir / "dim_service.parquet")
        self.dim_resource = pd.read_parquet(self.gold_dir / "dim_resource.parquet")

        # Joined view of usage + cost
        self.joined = self.fact_usage.merge(
            self.fact_cost[["cost_fact_id", "usage_fact_id" if "usage_fact_id" in self.fact_cost.columns else "date_key", "resource_id", "net_cost_usd"]],
            on=["date_key", "resource_id"],
            how="left"
        ).merge(
            self.dim_service[["service_id", "service_family", "pricing_model"]],
            on="service_id",
            how="left"
        ).merge(
            self.dim_resource[["resource_id", "provisioned_vcpu", "provisioned_memory_gb", "provisioned_storage_gb", "department", "environment"]],
            on="resource_id",
            how="left"
        )

    def get_overall_utilization(self) -> Dict[str, float]:
        """Calculates global mean and 95th percentile CPU and RAM metrics."""
        compute_rows = self.joined[self.joined["provisioned_vcpu"] > 0]
        idle_rows = self.joined[self.joined["is_idle"]]

        return {
            "overall_mean_cpu_pct": round(float(compute_rows["avg_cpu_utilization_pct"].mean()), 2),
            "overall_p95_cpu_pct": round(float(np.percentile(compute_rows["max_cpu_utilization_pct"], 95)), 2),
            "overall_mean_ram_pct": round(float(compute_rows["avg_memory_utilization_pct"].mean()), 2),
            "overall_p95_ram_pct": round(float(np.percentile(compute_rows["max_memory_utilization_pct"], 95)), 2),
            "total_compute_hours": round(float(compute_rows["runtime_hours"].sum()), 1),
            "total_idle_hours": round(float(idle_rows["runtime_hours"].sum()), 1),
            "idle_cost_waste_usd": round(float(idle_rows["net_cost_usd"].sum()), 2),
        }

    def get_service_utilization_breakdown(self) -> List[ServiceUtilizationMetric]:
        """Computes utilization profiles grouped by cloud service family."""
        grouped = self.joined.groupby("service_family", as_index=False).agg(
            mean_cpu=("avg_cpu_utilization_pct", "mean"),
            p95_cpu=("max_cpu_utilization_pct", lambda x: np.percentile(x, 95)),
            mean_ram=("avg_memory_utilization_pct", "mean"),
            p95_ram=("max_memory_utilization_pct", lambda x: np.percentile(x, 95)),
            total_hours=("runtime_hours", "sum"),
            total_storage=("provisioned_storage_gb", "sum"),
            total_egress=("network_egress_gb", "sum"),
            total_reqs=("total_requests", "sum"),
            idle_count=("is_idle", "sum")
        )

        metrics = []
        for _, row in grouped.iterrows():
            metrics.append(ServiceUtilizationMetric(
                service_family=str(row["service_family"]),
                mean_cpu_pct=round(float(row["mean_cpu"]), 2),
                p95_cpu_pct=round(float(row["p95_cpu"]), 2),
                mean_ram_pct=round(float(row["mean_ram"]), 2),
                p95_ram_pct=round(float(row["p95_ram"]), 2),
                total_compute_hours=round(float(row["total_hours"]), 1),
                total_storage_gb=round(float(row["total_storage"]), 1),
                total_network_egress_gb=round(float(row["total_egress"]), 1),
                total_requests=int(row["total_reqs"]),
                idle_resources_count=int(row["idle_count"])
            ))

        return metrics

    def get_utilization_vs_cost_correlations(self) -> List[UtilizationCostCorrelation]:
        """
        Demonstrates the fundamental FinOps principle:
        - Provisioned VMs exhibit zero correlation between CPU load and cost (fixed billing model).
        - Consumptive / Serverless workloads exhibit high correlation between load and cost.
        """
        results = []

        # 1. Provisioned VMs (Compute Engine)
        vm_data = self.joined[self.joined["service_family"] == "Compute"]
        if len(vm_data) > 10:
            p_corr, _ = stats.pearsonr(vm_data["avg_cpu_utilization_pct"], vm_data["net_cost_usd"])
            s_corr, _ = stats.spearmanr(vm_data["avg_cpu_utilization_pct"], vm_data["net_cost_usd"])
            results.append(UtilizationCostCorrelation(
                workload_type="Provisioned Virtual Machines (Compute Engine)",
                pearson_correlation=round(float(p_corr), 3),
                spearman_correlation=round(float(s_corr), 3),
                interpretation="Near-zero correlation: Billing is decoupled from load. Idle VMs cost the same as 100% utilized VMs."
            ))

        # 2. Serverless (Cloud Run)
        cr_data = self.joined[self.joined["service_family"] == "Serverless"]
        if len(cr_data) > 10:
            p_corr, _ = stats.pearsonr(cr_data["total_requests"], cr_data["net_cost_usd"])
            s_corr, _ = stats.spearmanr(cr_data["total_requests"], cr_data["net_cost_usd"])
            results.append(UtilizationCostCorrelation(
                workload_type="Serverless Invocations (Cloud Run)",
                pearson_correlation=round(float(p_corr), 3),
                spearman_correlation=round(float(s_corr), 3),
                interpretation="High positive correlation: Costs scale directly with incoming transaction volume."
            ))

        # 3. BigQuery Analytics (TB Scanned vs Cost)
        bq_data = self.joined[self.joined["service_family"] == "Analytics"]
        if len(bq_data) > 10:
            p_corr, _ = stats.pearsonr(bq_data["usage_quantity"], bq_data["net_cost_usd"])
            s_corr, _ = stats.spearmanr(bq_data["usage_quantity"], bq_data["net_cost_usd"])
            results.append(UtilizationCostCorrelation(
                workload_type="Analytical Querying (BigQuery TB Scanned)",
                pearson_correlation=round(float(p_corr), 3),
                spearman_correlation=round(float(s_corr), 3),
                interpretation="Perfect linear correlation (r=1.0): Cost is directly determined by data volume scanned per query."
            ))

        return results

    def generate_full_report(self) -> UtilizationAnalyticsOutput:
        """Builds structured Pydantic utilization report."""
        overall = self.get_overall_utilization()
        return UtilizationAnalyticsOutput(
            overall_mean_cpu_pct=overall["overall_mean_cpu_pct"],
            overall_p95_cpu_pct=overall["overall_p95_cpu_pct"],
            overall_mean_ram_pct=overall["overall_mean_ram_pct"],
            overall_p95_ram_pct=overall["overall_p95_ram_pct"],
            total_compute_hours=overall["total_compute_hours"],
            total_idle_hours=overall["total_idle_hours"],
            idle_cost_waste_usd=overall["idle_cost_waste_usd"],
            service_utilization_breakdown=self.get_service_utilization_breakdown(),
            utilization_vs_cost_correlations=self.get_utilization_vs_cost_correlations()
        )
