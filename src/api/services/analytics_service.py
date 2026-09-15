"""
CloudSense AI — Analytics Service Layer
Acts as the intermediary between API routers and verified analytical outputs.
Provides filtering, pagination, search, and structured context for future Gemini agents.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import HTTPException

from src.api.config import settings


class AnalyticsService:
    """
    Decoupled service layer serving validated analytical metrics.
    Abstracts local JSON/DuckDB storage so BigQuery can replace it seamlessly.
    """

    def __init__(self, summary_path: Optional[Path] = None):
        self.summary_path = summary_path or settings.analytics_summary_path
        self._data: Dict[str, Any] = {}
        self._load_analytics()
        # Lazily constructed on first use by simulate_green_migration() — see
        # that method for why this is cached rather than instantiated fresh
        # on every request.
        self._carbon_calculator = None

    def _load_analytics(self):
        if not self.summary_path.exists():
            raise FileNotFoundError(
                f"Analytics summary not found at {self.summary_path}. Run run_analytics.py first."
            )
        with open(self.summary_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

    # -------------------------------------------------------------------------
    # 1. Dashboard Overview
    # -------------------------------------------------------------------------
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Aggregates high-level executive KPIs across all analytical pillars."""
        cost = self._data["cost_analytics"]
        usage = self._data["utilization_analytics"]
        carbon = self._data["carbon_analytics"]
        anomalies = self._data["anomaly_detection"]
        opt = self._data["optimization_engine"]
        forecast = self._data["forecasting_engine"]

        return {
            "financial_kpis": {
                "total_net_spend_usd": cost["total_net_cost_usd"],
                "total_list_cost_usd": cost["total_list_cost_usd"],
                "total_discounts_usd": cost["total_discounts_usd"],
                "avg_daily_spend_usd": cost["avg_daily_cost_usd"],
                "pricing_consistency_verified": cost["pricing_consistency_verified"],
            },
            "efficiency_kpis": {
                "overall_mean_cpu_pct": usage["overall_mean_cpu_pct"],
                "overall_p95_cpu_pct": usage["overall_p95_cpu_pct"],
                "overall_mean_ram_pct": usage["overall_mean_ram_pct"],
                "overall_p95_ram_pct": usage["overall_p95_ram_pct"],
                "total_compute_hours": usage["total_compute_hours"],
                "idle_hours_wasted": usage["total_idle_hours"],
                "idle_dollar_waste_usd": usage["idle_cost_waste_usd"],
            },
            "environmental_kpis": {
                "is_estimate": True,
                "disclaimer": carbon["disclaimer"],
                "total_energy_consumed_kwh": carbon["total_energy_consumed_kwh"],
                "total_carbon_kg_co2e": carbon["total_carbon_kg_co2e"],
                "total_carbon_metric_tonnes": round(carbon["total_carbon_kg_co2e"] / 1000.0, 3),
                "scope2_operational_kg": carbon["total_scope2_operational_kg_co2e"],
                "scope3_embodied_kg": carbon["total_scope3_embodied_kg_co2e"],
                "carbon_intensity_gco2e_per_dollar": carbon["avg_carbon_intensity_gco2_per_dollar"],
            },
            "incident_kpis": {
                "active_anomalies_count": anomalies["total_anomalies_detected"],
                "anomalies_by_severity": anomalies["anomalies_by_severity"],
                "total_unbudgeted_dollar_surge_usd": anomalies["total_unbudgeted_dollar_impact"],
            },
            "optimization_kpis": {
                "total_actionable_recommendations": opt["total_recommendations_count"],
                "total_potential_monthly_savings_usd": opt["total_potential_monthly_savings_usd"],
                "total_potential_annual_savings_usd": opt["total_potential_annual_savings_usd"],
                "total_monthly_carbon_avoidable_kg": opt["total_potential_monthly_carbon_saved_kg"],
            },
            "forecast_kpis": {
                "champion_forecasting_model": forecast["champion_model"],
                "projected_next_30_days_spend_usd": forecast["projected_monthly_spend_usd"],
            }
        }

    # -------------------------------------------------------------------------
    # 2. Cost Analytics
    # -------------------------------------------------------------------------
    def get_cost_summary(self) -> Dict[str, Any]:
        cost = self._data["cost_analytics"]
        return {
            "total_net_cost_usd": cost["total_net_cost_usd"],
            "total_list_cost_usd": cost["total_list_cost_usd"],
            "total_discounts_usd": cost["total_discounts_usd"],
            "avg_daily_cost_usd": cost["avg_daily_cost_usd"],
            "pricing_consistency_verified": cost["pricing_consistency_verified"],
        }

    def get_cost_by_dimension(self, dimension: str) -> List[Dict[str, Any]]:
        dim_map = {
            "provider": "cost_by_provider",
            "service": "cost_by_service",
            "region": "cost_by_region",
            "department": "cost_by_department",
            "environment": "cost_by_environment",
        }
        if dimension not in dim_map:
            raise HTTPException(status_code=400, detail=f"Invalid dimension '{dimension}'. Valid: {list(dim_map.keys())}")
        return self._data["cost_analytics"][dim_map[dimension]]

    def get_cost_trends(self) -> List[Dict[str, Any]]:
        return self._data["cost_analytics"]["daily_spend_trend"]

    def get_cost_resources(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        department: Optional[str] = None
    ) -> Dict[str, Any]:
        resources = self._data["cost_analytics"]["top_expensive_resources"]
        
        filtered = resources
        if search:
            s = search.lower()
            filtered = [r for r in filtered if s in r["resource_id"].lower() or s in r["resource_name"].lower()]
        if department:
            d = department.lower()
            filtered = [r for r in filtered if d in r.get("department", "").lower()]

        total_items = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = filtered[start_idx:end_idx]

        return {
            "total_items": total_items,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_items + page_size - 1) // page_size if total_items > 0 else 1,
            "items": paginated
        }

    # -------------------------------------------------------------------------
    # 3. Resource Utilization
    # -------------------------------------------------------------------------
    def get_usage_summary(self) -> Dict[str, Any]:
        u = self._data["utilization_analytics"]
        return {
            "overall_mean_cpu_pct": u["overall_mean_cpu_pct"],
            "overall_p95_cpu_pct": u["overall_p95_cpu_pct"],
            "overall_mean_ram_pct": u["overall_mean_ram_pct"],
            "overall_p95_ram_pct": u["overall_p95_ram_pct"],
            "total_compute_hours": u["total_compute_hours"],
            "total_idle_hours": u["total_idle_hours"],
            "idle_cost_waste_usd": u["idle_cost_waste_usd"],
        }

    def get_service_utilization(self) -> List[Dict[str, Any]]:
        return self._data["utilization_analytics"]["service_utilization_breakdown"]

    def get_utilization_correlations(self) -> List[Dict[str, Any]]:
        return self._data["utilization_analytics"]["utilization_vs_cost_correlations"]

    # -------------------------------------------------------------------------
    # 4. Statistical Anomalies
    # -------------------------------------------------------------------------
    def get_anomalies(
        self,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        anom = self._data["anomaly_detection"]
        items = anom["detected_anomalies"]

        if severity:
            s_clean = severity.capitalize()
            items = [a for a in items if a["severity"] == s_clean]

        total_count = len(items)
        paginated = items[offset:offset + limit]

        return {
            "total_anomalies": total_count,
            "total_unbudgeted_dollar_impact": anom["total_unbudgeted_dollar_impact"],
            "anomalies_by_severity": anom["anomalies_by_severity"],
            "items": paginated
        }

    def get_anomaly_by_id(self, anomaly_id: str) -> Dict[str, Any]:
        items = self._data["anomaly_detection"]["detected_anomalies"]
        for a in items:
            if a["anomaly_id"] == anomaly_id:
                return a
        raise HTTPException(status_code=404, detail=f"Anomaly with ID '{anomaly_id}' not found.")

    # -------------------------------------------------------------------------
    # 5. Optimization Opportunities
    # -------------------------------------------------------------------------
    def get_optimizations(
        self,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        opt = self._data["optimization_engine"]
        items = opt["recommendations"]

        if category:
            cat_clean = category.lower()
            items = [r for r in items if r["optimization_category"].lower() == cat_clean]

        total_count = len(items)
        paginated = items[offset:offset + limit]

        return {
            "total_recommendations": total_count,
            "total_potential_monthly_savings_usd": opt["total_potential_monthly_savings_usd"],
            "total_potential_annual_savings_usd": opt["total_potential_annual_savings_usd"],
            "total_potential_monthly_carbon_saved_kg": opt["total_potential_monthly_carbon_saved_kg"],
            "savings_by_category": opt["savings_by_category"],
            "items": paginated
        }

    def get_optimization_by_id(self, recommendation_id: str) -> Dict[str, Any]:
        items = self._data["optimization_engine"]["recommendations"]
        for r in items:
            if r["recommendation_id"] == recommendation_id:
                return r
        raise HTTPException(status_code=404, detail=f"Optimization recommendation '{recommendation_id}' not found.")

    # -------------------------------------------------------------------------
    # 6. Carbon Analytics & Migration Simulator
    # -------------------------------------------------------------------------
    def get_carbon_summary(self) -> Dict[str, Any]:
        c = self._data["carbon_analytics"]
        return {
            "is_estimate": True,
            "disclaimer": c["disclaimer"],
            "total_energy_consumed_kwh": c["total_energy_consumed_kwh"],
            "total_scope2_operational_kg_co2e": c["total_scope2_operational_kg_co2e"],
            "total_scope3_embodied_kg_co2e": c["total_scope3_embodied_kg_co2e"],
            "total_carbon_kg_co2e": c["total_carbon_kg_co2e"],
            "avg_carbon_intensity_gco2_per_dollar": c["avg_carbon_intensity_gco2_per_dollar"],
            "methodology_assumptions": c["methodology_assumptions"],
        }

    def get_carbon_by_region(self) -> List[Dict[str, Any]]:
        return self._data["carbon_analytics"]["carbon_by_region"]

    def get_carbon_trends(self) -> List[Dict[str, Any]]:
        return self._data["carbon_analytics"]["daily_carbon_trend"]

    def simulate_green_migration(self, resource_id: str, target_region_id: str = "europe-west6") -> Dict[str, Any]:
        # The CarbonCalculator is built once and cached on this service
        # instance rather than instantiated fresh on every call — its
        # constructor reads 5 Parquet files from disk and performs a
        # multi-table merge, which is unnecessary repeated I/O for a
        # dataset that doesn't change during the process's lifetime
        # (mirrors the load-once-at-startup pattern used for self._data).
        if self._carbon_calculator is None:
            from src.analytics.carbon_calculator import CarbonCalculator
            self._carbon_calculator = CarbonCalculator(data_dir=settings.data_dir)
        res = self._carbon_calculator.simulate_green_migration(resource_id, target_region_id)
        if "error" in res:
            raise HTTPException(status_code=404, detail=res["error"])
        return res

    # -------------------------------------------------------------------------
    # 7. Forecasting
    # -------------------------------------------------------------------------
    def get_forecast_summary(self) -> Dict[str, Any]:
        fc = self._data["forecasting_engine"]
        return {
            "target_metric": fc["target_metric"],
            "champion_model": fc["champion_model"],
            "train_horizon": fc["train_horizon"],
            "test_horizon": fc["test_horizon"],
            "projected_monthly_spend_usd": fc["projected_monthly_spend_usd"],
        }

    def get_forecast_models(self) -> List[Dict[str, Any]]:
        return self._data["forecasting_engine"]["models_evaluated"]

    def get_forecast_projections(self, horizon_days: int = 30) -> Dict[str, Any]:
        fc = self._data["forecasting_engine"]
        if horizon_days <= 30:
            pts = fc["forecast_30_days"]
        elif horizon_days <= 60:
            pts = fc["forecast_60_days"]
        else:
            pts = fc["forecast_90_days"]

        return {
            "horizon_days": horizon_days,
            "projected_total_usd": round(sum(p["predicted_cost_usd"] for p in pts), 2),
            "predictions": pts
        }

    # -------------------------------------------------------------------------
    # 8. Gemini Grounding Context & Tools Manifest (Zero Numerical Hallucination)
    # -------------------------------------------------------------------------
    def get_gemini_context(self) -> Dict[str, Any]:
        """
        Produces a structured, verified factual context bundle specifically designed
        to be injected into future Gemini prompts. Gemini will reason strictly over these facts.
        """
        dash = self.get_dashboard_summary()
        anomalies = self.get_anomalies(limit=5)["items"]
        top_opts = self.get_optimizations(limit=5)["items"]
        regions = self.get_carbon_by_region()

        return {
            "grounding_instruction": "You are the CloudSense AI FinOps Copilot. You MUST strictly use ONLY the verified facts and numerical figures provided below. Do not compute, invent, or hallucinate numbers.",
            "verified_estate_overview": {
                "total_net_spend_usd": dash["financial_kpis"]["total_net_spend_usd"],
                "average_daily_spend_usd": dash["financial_kpis"]["avg_daily_spend_usd"],
                "total_energy_consumed_kwh": dash["environmental_kpis"]["total_energy_consumed_kwh"],
                "total_carbon_metric_tonnes": dash["environmental_kpis"]["total_carbon_metric_tonnes"],
                "fleet_mean_cpu_pct": dash["efficiency_kpis"]["overall_mean_cpu_pct"],
                "idle_dollar_waste_usd": dash["efficiency_kpis"]["idle_dollar_waste_usd"],
                "total_actionable_annual_savings_usd": dash["optimization_kpis"]["total_potential_annual_savings_usd"],
                "projected_next_month_spend_usd": dash["forecast_kpis"]["projected_next_30_days_spend_usd"],
            },
            "verified_critical_anomalies": anomalies,
            "verified_top_recommendations": top_opts,
            "verified_regional_carbon_profiles": regions,
        }

    def get_gemini_tools_manifest(self) -> List[Dict[str, Any]]:
        """
        Returns JSON-schema tool definitions for future Gemini function calling.
        """
        return [
            {
                "name": "get_cost_summary",
                "description": "Returns verified portfolio spend, discounts, and daily averages.",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "get_cost_by_dimension",
                "description": "Returns spend broken down by service, region, department, or environment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dimension": {"type": "string", "enum": ["service", "region", "department", "environment"]}
                    },
                    "required": ["dimension"]
                }
            },
            {
                "name": "get_anomalies",
                "description": "Returns verified statistical cost anomalies flagged via Z-score and Modified MAD.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["Critical", "High", "Medium", "Low"]}
                    }
                }
            },
            {
                "name": "get_optimizations",
                "description": "Returns prioritized FinOps recommendations (zombies, rightsizing, storage tiering).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": ["idle_zombie", "compute_rightsizing", "storage_lifecycle", "green_migration"]}
                    }
                }
            },
            {
                "name": "simulate_green_migration",
                "description": "Calculates carbon and financial delta from migrating a workload to Zurich or Iowa.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "resource_id": {"type": "string", "description": "Cloud resource identifier"},
                        "target_region_id": {"type": "string", "enum": ["europe-west6", "us-central1", "europe-west1"]}
                    },
                    "required": ["resource_id"]
                }
            }
        ]


# Singleton Service Instance
analytics_service = AnalyticsService()
