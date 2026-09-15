"""
CloudSense AI — Unit & Integration Tests for Analytics & ML Engines
Tests CostAnalyzer, UsageAnalyzer, CarbonCalculator, AnomalyDetector,
OptimizationEngine, and CostForecaster.
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.analytics.cost_analyzer import CostAnalyzer
from src.analytics.usage_analyzer import UsageAnalyzer
from src.analytics.carbon_calculator import CarbonCalculator
from src.ml.anomaly_detector import AnomalyDetector
from src.ml.optimizer import OptimizationEngine
from src.ml.forecaster import CostForecaster
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def engines():
    return {
        "cost": CostAnalyzer(data_dir=DATA_DIR),
        "usage": UsageAnalyzer(data_dir=DATA_DIR),
        "carbon": CarbonCalculator(data_dir=DATA_DIR),
        "anomaly": AnomalyDetector(data_dir=DATA_DIR),
        "opt": OptimizationEngine(data_dir=DATA_DIR),
        "forecast": CostForecaster(data_dir=DATA_DIR)
    }


def test_cost_analyzer_integrity(engines):
    """Tests cost breakdown reconciliation and pricing consistency."""
    cost_engine = engines["cost"]
    report = cost_engine.generate_full_report()

    assert report.total_net_cost_usd > 700000.0
    assert report.total_list_cost_usd > report.total_net_cost_usd
    assert report.pricing_consistency_verified is True

    # Check breakdown reconciliation
    service_sum = sum(r.net_cost_usd for r in report.cost_by_service)
    region_sum = sum(r.net_cost_usd for r in report.cost_by_region)
    assert abs(service_sum - report.total_net_cost_usd) < 1.0
    assert abs(region_sum - report.total_net_cost_usd) < 1.0


def test_usage_analyzer_metrics_and_correlations(engines):
    """Tests utilization bounds and load-to-cost empirical correlations."""
    usage_engine = engines["usage"]
    report = usage_engine.generate_full_report()

    assert 0.0 <= report.overall_mean_cpu_pct <= report.overall_p95_cpu_pct <= 100.0
    assert 0.0 <= report.overall_mean_ram_pct <= report.overall_p95_ram_pct <= 100.0
    assert report.total_idle_hours > 0.0
    assert report.idle_cost_waste_usd > 0.0

    # Assert that serverless/BigQuery has higher load-cost correlation than provisioned VMs
    vm_corr = next(c for c in report.utilization_vs_cost_correlations if "Virtual Machines" in c.workload_type)
    serverless_corr = next(c for c in report.utilization_vs_cost_correlations if "Serverless" in c.workload_type)
    assert abs(vm_corr.pearson_correlation) < abs(serverless_corr.pearson_correlation)


def test_carbon_calculator_methodology(engines):
    """Tests Scope 2 & 3 carbon accounting and green migration simulator."""
    carbon_engine = engines["carbon"]
    report = carbon_engine.generate_full_report()

    assert report.is_estimate is True
    assert "SPECpower" in report.disclaimer
    assert report.total_energy_consumed_kwh > 0.0
    assert abs((report.total_scope2_operational_kg_co2e + report.total_scope3_embodied_kg_co2e) - report.total_carbon_kg_co2e) < 0.1

    # Regional carbon order: Zurich (europe-west6) must have lower carbon intensity than Mumbai (asia-south1)
    ch_reg = next(r for r in report.carbon_by_region if r.region_id == "europe-west6")
    in_reg = next(r for r in report.carbon_by_region if r.region_id == "asia-south1")
    assert ch_reg.carbon_per_dollar_gco2e < in_reg.carbon_per_dollar_gco2e

    # Green migration simulation test
    sim = carbon_engine.simulate_green_migration(workload_resource_id="vm-checkout-e2-micro-003", target_region_id="europe-west6")
    assert sim["carbon_reduction_pct"] > 50.0


def test_statistical_anomaly_detection(engines):
    """Tests statistical anomaly scoring and explainability."""
    anomaly_engine = engines["anomaly"]
    report = anomaly_engine.generate_full_report()

    assert report.total_anomalies_detected > 0
    assert report.total_unbudgeted_dollar_impact > 0.0

    for anom in report.detected_anomalies[:5]:
        assert anom.anomaly_score > 0.0
        assert anom.observed_value > anom.expected_value
        assert anom.severity in ["Low", "Medium", "High", "Critical"]
        assert len(anom.explanation) > 15


def test_optimization_recommendations(engines):
    """Tests optimization rules, confidence, and annual ROI calculations."""
    opt_engine = engines["opt"]
    report = opt_engine.generate_full_report()

    assert report.total_recommendations_count > 0
    assert report.total_potential_annual_savings_usd > report.total_potential_monthly_savings_usd

    for rec in report.recommendations:
        assert rec.estimated_monthly_saving_usd >= 0.0
        assert abs(rec.estimated_annual_saving_usd - (rec.estimated_monthly_saving_usd * 12.0)) < 0.05
        assert rec.rule_triggered in [
            "RULE_IDLE_ZOMBIE_TERMINATION", "RULE_COMPUTE_RIGHTSIZING",
            "RULE_STORAGE_LIFECYCLE_TIER", "RULE_GREEN_WORKLOAD_MIGRATION"
        ]


def test_forecasting_pipeline(engines):
    """Tests time-series evaluation metrics and prediction intervals."""
    forecast_engine = engines["forecast"]
    report = forecast_engine.generate_full_report()

    assert len(report.models_evaluated) >= 2
    for m in report.models_evaluated:
        assert m.mae > 0.0
        assert m.rmse > 0.0
        assert 0.0 < m.mape_pct < 25.0

    assert len(report.forecast_30_days) == 30
    assert len(report.forecast_90_days) == 90

    for pt in report.forecast_30_days:
        assert pt.lower_bound_80_usd <= pt.predicted_cost_usd <= pt.upper_bound_80_usd
        assert pt.lower_bound_95_usd <= pt.lower_bound_80_usd
        assert pt.upper_bound_80_usd <= pt.upper_bound_95_usd
