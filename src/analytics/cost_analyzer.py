"""
CloudSense AI — Cost Analytics Engine
Provides multi-dimensional cloud cost calculations, unit economics,
spend breakdowns, time-series trends, and pricing consistency validation.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from src.analytics.schemas import CostAnalyticsOutput, CostSummaryRecord


class CostAnalyzer:
    """
    Analyzes historical and current cloud infrastructure costs,
    validating calculations against established pricing catalogs.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.gold_dir = data_dir / "gold"
        self._load_datasets()

    def _load_datasets(self):
        self.fact_cost = pd.read_parquet(self.gold_dir / "fact_cost.parquet")
        self.dim_resource = pd.read_parquet(self.gold_dir / "dim_resource.parquet")
        self.dim_service = pd.read_parquet(self.gold_dir / "dim_service.parquet")
        self.dim_region = pd.read_parquet(self.gold_dir / "dim_region.parquet")
        self.dim_date = pd.read_parquet(self.gold_dir / "dim_date.parquet")

        # Create enriched cost view
        self.enriched = self.fact_cost.merge(
            self.dim_resource[[
                "resource_id", "resource_name", "resource_type", "department",
                "cost_center", "environment", "project_id", "project_name"
            ]],
            on="resource_id",
            how="left"
        ).merge(
            self.dim_service[["service_id", "service_name", "service_family"]],
            on="service_id",
            how="left"
        ).merge(
            self.dim_region[["region_id", "region_name", "country"]],
            on="region_id",
            how="left"
        )

    def get_total_cost(self) -> Dict[str, float]:
        """Returns total portfolio gross list cost, realized discounts, and net spend."""
        list_spend = float(self.fact_cost["list_cost_usd"].sum())
        discounts = float(self.fact_cost["discount_amount_usd"].sum())
        net_spend = float(self.fact_cost["net_cost_usd"].sum())
        unique_days = self.fact_cost["usage_date"].nunique()

        return {
            "total_list_cost_usd": round(list_spend, 2),
            "total_discounts_usd": round(discounts, 2),
            "total_net_cost_usd": round(net_spend, 2),
            "avg_daily_cost_usd": round(net_spend / max(unique_days, 1), 2),
            "effective_discount_pct": round((discounts / max(list_spend, 1.0)) * 100.0, 2)
        }

    def get_cost_breakdown(self, dimension: str) -> List[CostSummaryRecord]:
        """
        Groups spend by dimension ('provider_id', 'service_family', 'region_name', 'department', 'environment').
        """
        total_net = self.fact_cost["net_cost_usd"].sum()

        grouped = self.enriched.groupby(dimension, as_index=False).agg(
            list_cost=("list_cost_usd", "sum"),
            discount=("discount_amount_usd", "sum"),
            net_cost=("net_cost_usd", "sum"),
            active_resources=("resource_id", "nunique")
        )

        records = []
        for _, row in grouped.iterrows():
            spend = float(row["net_cost"])
            share = (spend / total_net * 100.0) if total_net > 0 else 0.0
            records.append(CostSummaryRecord(
                dimension_key=dimension,
                dimension_value=str(row[dimension]),
                list_cost_usd=round(float(row["list_cost"]), 2),
                discount_amount_usd=round(float(row["discount"]), 2),
                net_cost_usd=round(spend, 2),
                spend_share_pct=round(share, 2),
                active_resources_count=int(row["active_resources"])
            ))

        return sorted(records, key=lambda r: r.net_cost_usd, reverse=True)

    def get_top_resources(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Returns the highest spend individual resources across the fleet."""
        res_spend = self.enriched.groupby(
            ["resource_id", "resource_name", "service_name", "department", "environment", "region_name"],
            as_index=False
        ).agg(
            total_net_spend_usd=("net_cost_usd", "sum"),
            avg_daily_spend_usd=("net_cost_usd", "mean"),
            active_days=("usage_date", "nunique")
        ).sort_values("total_net_spend_usd", ascending=False).head(limit)

        return res_spend.round(2).to_dict(orient="records")

    def get_daily_trend(self) -> List[Dict[str, Any]]:
        """Computes daily spend timeline with 7-day and 30-day rolling averages."""
        daily = self.fact_cost.groupby("usage_date", as_index=False)["net_cost_usd"].sum().sort_values("usage_date")
        daily["rolling_7d"] = daily["net_cost_usd"].rolling(7, min_periods=1).mean()
        daily["rolling_30d"] = daily["net_cost_usd"].rolling(30, min_periods=1).mean()
        daily["mom_pct"] = daily["net_cost_usd"].pct_change(30) * 100.0

        daily = daily.fillna(0.0).round(2)
        return daily.to_dict(orient="records")

    def verify_pricing_consistency(self) -> bool:
        """Verifies that Net = List - Discount holds for 100% of line items."""
        diff = (self.fact_cost["list_cost_usd"] - self.fact_cost["discount_amount_usd"]) - self.fact_cost["net_cost_usd"]
        return bool((diff.abs() < 0.001).all())

    def generate_full_report(self) -> CostAnalyticsOutput:
        """Builds structured Pydantic cost analytics output."""
        totals = self.get_total_cost()
        return CostAnalyticsOutput(
            total_list_cost_usd=totals["total_list_cost_usd"],
            total_discounts_usd=totals["total_discounts_usd"],
            total_net_cost_usd=totals["total_net_cost_usd"],
            avg_daily_cost_usd=totals["avg_daily_cost_usd"],
            cost_by_provider=self.get_cost_breakdown("provider_id"),
            cost_by_service=self.get_cost_breakdown("service_family"),
            cost_by_region=self.get_cost_breakdown("region_name"),
            cost_by_department=self.get_cost_breakdown("department"),
            cost_by_environment=self.get_cost_breakdown("environment"),
            top_expensive_resources=self.get_top_resources(15),
            daily_spend_trend=self.get_daily_trend(),
            pricing_consistency_verified=self.verify_pricing_consistency()
        )
