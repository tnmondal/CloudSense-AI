"""
CloudSense AI — API Integration & Contract Test Suite
Tests all REST endpoints across Dashboard, Cost, Usage, Anomalies,
Optimizations, Carbon, Forecasting, and AI Grounding Context.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    """Tests /api/v1/health status."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["analytics_data_loaded"] is True


def test_dashboard_summary_reconciliation(client):
    """Tests that /api/v1/dashboard/summary matches validated analytics values."""
    res = client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200
    data = res.json()

    # Exact reconciliation with validated Gold fact values
    assert data["financial_kpis"]["total_net_spend_usd"] == 726397.32
    assert data["financial_kpis"]["avg_daily_spend_usd"] == 2905.59
    assert data["financial_kpis"]["pricing_consistency_verified"] is True

    assert data["environmental_kpis"]["is_estimate"] is True
    assert data["environmental_kpis"]["total_energy_consumed_kwh"] == 159274.72
    assert data["environmental_kpis"]["total_carbon_kg_co2e"] == 33512.50

    assert data["incident_kpis"]["active_anomalies_count"] == 41
    assert data["incident_kpis"]["total_unbudgeted_dollar_surge_usd"] == 44602.39

    assert data["optimization_kpis"]["total_actionable_recommendations"] == 45
    assert data["optimization_kpis"]["total_potential_annual_savings_usd"] == 20746.32

    assert "Random Forest" in data["forecast_kpis"]["champion_forecasting_model"]
    assert data["forecast_kpis"]["projected_next_30_days_spend_usd"] > 80000.0


def test_cost_endpoints(client):
    """Tests cost summary, breakdowns, trends, and pagination."""
    # 1. Summary
    res = client.get("/api/v1/cost/summary")
    assert res.status_code == 200
    assert res.json()["total_net_cost_usd"] == 726397.32

    # 2. By Service
    res_svc = client.get("/api/v1/cost/by-service")
    assert res_svc.status_code == 200
    services = res_svc.json()
    assert len(services) == 7
    assert services[0]["dimension_value"] == "Analytics"  # Top spend service

    # 3. By Region
    res_reg = client.get("/api/v1/cost/by-region")
    assert res_reg.status_code == 200
    assert len(res_reg.json()) == 5

    # 4. Trends
    res_trd = client.get("/api/v1/cost/trends")
    assert res_trd.status_code == 200
    assert len(res_trd.json()) == 250

    # 5. Resources Pagination
    res_pg = client.get("/api/v1/cost/resources?page=1&page_size=5")
    assert res_pg.status_code == 200
    pg_data = res_pg.json()
    assert pg_data["page"] == 1
    assert pg_data["page_size"] == 5
    assert len(pg_data["items"]) == 5


def test_usage_endpoints(client):
    """Tests utilization metrics and billing correlation."""
    res = client.get("/api/v1/usage/summary")
    assert res.status_code == 200
    data = res.json()
    assert 40.0 < data["overall_mean_cpu_pct"] < 60.0
    assert data["idle_cost_waste_usd"] == 5959.65

    res_corr = client.get("/api/v1/usage/correlations")
    assert res_corr.status_code == 200
    corrs = res_corr.json()
    assert len(corrs) == 3


def test_anomalies_endpoints(client):
    """Tests anomaly listing, severity filtering, and error handling."""
    # List all
    res = client.get("/api/v1/anomalies")
    assert res.status_code == 200
    data = res.json()
    assert data["total_anomalies"] == 41
    assert len(data["items"]) == 41

    first_id = data["items"][0]["anomaly_id"]

    # Filter by severity
    res_crit = client.get("/api/v1/anomalies?severity=Critical")
    assert res_crit.status_code == 200
    assert res_crit.json()["total_anomalies"] == 11

    # Detail by ID
    res_det = client.get(f"/api/v1/anomalies/{first_id}")
    assert res_det.status_code == 200
    assert res_det.json()["anomaly_id"] == first_id

    # 404 on non-existent ID
    res_404 = client.get("/api/v1/anomalies/ANOM-DOES-NOT-EXIST")
    assert res_404.status_code == 404


def test_optimizations_endpoints(client):
    """Tests optimization listing, category filtering, and detail endpoint."""
    res = client.get("/api/v1/optimizations")
    assert res.status_code == 200
    data = res.json()
    assert data["total_recommendations"] == 45

    # Filter by category
    res_zomb = client.get("/api/v1/optimizations?category=idle_zombie")
    assert res_zomb.status_code == 200
    assert res_zomb.json()["total_recommendations"] == 3

    # Detail by ID
    first_id = data["items"][0]["recommendation_id"]
    res_det = client.get(f"/api/v1/optimizations/{first_id}")
    assert res_det.status_code == 200
    assert res_det.json()["recommendation_id"] == first_id


def test_carbon_endpoints(client):
    """Tests carbon summary, regional profiles, trends, and migration simulator."""
    res_sum = client.get("/api/v1/carbon/summary")
    assert res_sum.status_code == 200
    assert res_sum.json()["is_estimate"] is True
    assert res_sum.json()["total_carbon_kg_co2e"] == 33512.50

    # Regional profile
    res_reg = client.get("/api/v1/carbon/by-region")
    assert res_reg.status_code == 200
    assert len(res_reg.json()) == 5

    # Simulate migration
    sim_payload = {
        "resource_id": "vm-checkout-e2-micro-003",
        "target_region_id": "europe-west6"
    }
    res_sim = client.post("/api/v1/carbon/simulate-migration", json=sim_payload)
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert sim_data["carbon_reduction_pct"] > 50.0


def test_simulate_migration_reuses_cached_carbon_calculator(client):
    """
    Regression test (Phase 7): simulate_green_migration() previously
    constructed a brand-new CarbonCalculator (5 Parquet reads + a merge) on
    every single request. It must now be built once, lazily, and reused —
    verified here by confirming the same object identity is cached on
    AnalyticsService across two separate requests.
    """
    from src.api.services.analytics_service import analytics_service

    payload = {"resource_id": "vm-checkout-e2-micro-003", "target_region_id": "europe-west6"}

    client.post("/api/v1/carbon/simulate-migration", json=payload)
    first_instance = analytics_service._carbon_calculator
    assert first_instance is not None, "CarbonCalculator should be constructed and cached after first use"

    client.post("/api/v1/carbon/simulate-migration", json={**payload, "target_region_id": "us-central1"})
    second_instance = analytics_service._carbon_calculator
    assert second_instance is first_instance, "CarbonCalculator must be reused, not reconstructed, on subsequent calls"


def test_forecasting_endpoints(client):
    """Tests forecasting models, evaluation comparison, and multi-step projections."""
    res_sum = client.get("/api/v1/forecast/summary")
    assert res_sum.status_code == 200
    assert "Random Forest" in res_sum.json()["champion_model"]

    res_models = client.get("/api/v1/forecast/models")
    assert res_models.status_code == 200
    assert len(res_models.json()) >= 3

    # 30-day projection
    res_p30 = client.get("/api/v1/forecast/projections?horizon_days=30")
    assert res_p30.status_code == 200
    assert len(res_p30.json()["predictions"]) == 30


def test_ai_context_and_tools_manifest(client):
    """Tests structured context endpoints prepared for future Gemini Copilot."""
    res_ctx = client.get("/api/v1/ai/context")
    assert res_ctx.status_code == 200
    ctx = res_ctx.json()
    assert "grounding_instruction" in ctx
    assert ctx["verified_estate_overview"]["total_net_spend_usd"] == 726397.32
    assert len(ctx["verified_critical_anomalies"]) > 0

    res_tools = client.get("/api/v1/ai/tools-manifest")
    assert res_tools.status_code == 200
    tools = res_tools.json()["tools"]
    assert len(tools) >= 5
    tool_names = [t["name"] for t in tools]
    assert "get_cost_summary" in tool_names
    assert "simulate_green_migration" in tool_names
