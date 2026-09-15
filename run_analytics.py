"""
CloudSense AI — Master Analytics & ML Runner Script
Executes all core analytical engines, statistical anomaly detection,
rule-based optimization, and time-series forecasting.
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from src.analytics.cost_analyzer import CostAnalyzer
from src.analytics.usage_analyzer import UsageAnalyzer
from src.analytics.carbon_calculator import CarbonCalculator
from src.ml.anomaly_detector import AnomalyDetector
from src.ml.optimizer import OptimizationEngine
from src.ml.forecaster import CostForecaster


def main():
    print("=" * 80)
    print("CloudSense AI — Step 4: Core Analytics, Carbon Modeling, Anomalies & ML Forecasting")
    print("=" * 80)

    data_dir = REPO_ROOT / "data"
    output_json = data_dir / "analytics_summary.json"

    # 1. Cost Analytics
    print("\n[1/6] Running Cost Analytics Engine...")
    cost_engine = CostAnalyzer(data_dir=data_dir)
    cost_res = cost_engine.generate_full_report()
    print(f"  • Total Net Cloud Spend: ${cost_res.total_net_cost_usd:,.2f} USD")
    print(f"  • Total Discounts Realized: ${cost_res.total_discounts_usd:,.2f} USD")
    print(f"  • Average Daily Spend: ${cost_res.avg_daily_cost_usd:,.2f} USD / day")
    print(f"  • Pricing Consistency Verified: {cost_res.pricing_consistency_verified}")

    # 2. Resource Utilization Analytics
    print("\n[2/6] Running Resource Utilization Analytics Engine...")
    usage_engine = UsageAnalyzer(data_dir=data_dir)
    usage_res = usage_engine.generate_full_report()
    print(f"  • Fleet Mean CPU: {usage_res.overall_mean_cpu_pct:.1f}% | P95 Peak: {usage_res.overall_p95_cpu_pct:.1f}%")
    print(f"  • Fleet Mean RAM: {usage_res.overall_mean_ram_pct:.1f}% | P95 Peak: {usage_res.overall_p95_ram_pct:.1f}%")
    print(f"  • Total Idle Hours: {usage_res.total_idle_hours:,.1f} hrs")
    print(f"  • Direct Idle Cost Waste: ${usage_res.idle_cost_waste_usd:,.2f} USD")

    # 3. Carbon Analytics Engine
    print("\n[3/6] Running Carbon & GreenOps Analytics Engine...")
    carbon_engine = CarbonCalculator(data_dir=data_dir)
    carbon_res = carbon_engine.generate_full_report()
    print(f"  • Total Facility Energy: {carbon_res.total_energy_consumed_kwh:,.2f} kWh")
    print(f"  • Total Carbon Footprint: {carbon_res.total_carbon_kg_co2e:,.2f} kg CO2e ({carbon_res.total_carbon_kg_co2e / 1000.0:.2f} Metric Tonnes)")
    print(f"  • Scope 2 Operational: {carbon_res.total_scope2_operational_kg_co2e:,.2f} kg CO2e")
    print(f"  • Scope 3 Embodied: {carbon_res.total_scope3_embodied_kg_co2e:,.2f} kg CO2e")
    print(f"  • Fleet Carbon Efficiency: {carbon_res.avg_carbon_intensity_gco2_per_dollar:.1f} gCO2e / $ spend")

    # 4. Statistical Anomaly Detection
    print("\n[4/6] Running Statistical Anomaly Detection Engine (Z-Score, MAD, IQR)...")
    anomaly_engine = AnomalyDetector(data_dir=data_dir)
    anomaly_res = anomaly_engine.generate_full_report()
    print(f"  • Total Anomalies Flagged: {anomaly_res.total_anomalies_detected}")
    print(f"  • Severities: {anomaly_res.anomalies_by_severity}")
    print(f"  • Unbudgeted Dollar Surge: ${anomaly_res.total_unbudgeted_dollar_impact:,.2f} USD")

    # 5. Infrastructure Optimization Engine
    print("\n[5/6] Running Infrastructure Optimization Engine...")
    opt_engine = OptimizationEngine(data_dir=data_dir)
    opt_res = opt_engine.generate_full_report()
    print(f"  • Total Actionable Recommendations: {opt_res.total_recommendations_count}")
    print(f"  • Potential Monthly Savings: ${opt_res.total_potential_monthly_savings_usd:,.2f} USD / mo")
    print(f"  • Potential Annual Savings: ${opt_res.total_potential_annual_savings_usd:,.2f} USD / yr")
    print(f"  • Potential Monthly Carbon Reduction: {opt_res.total_potential_monthly_carbon_saved_kg:,.2f} kg CO2e / mo")

    # 6. Cost Forecasting Engine
    print("\n[6/6] Running Time-Series Cost Forecasting Engine...")
    forecast_engine = CostForecaster(data_dir=data_dir)
    forecast_res = forecast_engine.generate_full_report()
    print(f"  • Champion Model Selected: {forecast_res.champion_model}")
    print("\n  Model Evaluation Comparison (Holdout Test Horizon):")
    for m in forecast_res.models_evaluated:
        print(f"    - {m.model_name:<42} | MAE: ${m.mae:>6.2f} | RMSE: ${m.rmse:>6.2f} | MAPE: {m.mape_pct:>5.2f}%")

    print(f"\n  • Projected 30-Day Forward Spend: ${forecast_res.projected_monthly_spend_usd:,.2f} USD")

    # Save full machine-readable analytics bundle
    summary_bundle = {
        "cost_analytics": cost_res.model_dump(),
        "utilization_analytics": usage_res.model_dump(),
        "carbon_analytics": carbon_res.model_dump(),
        "anomaly_detection": anomaly_res.model_dump(),
        "optimization_engine": opt_res.model_dump(),
        "forecasting_engine": forecast_res.model_dump()
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(summary_bundle, f, indent=2)

    print("\n" + "=" * 80)
    print(f"SUCCESS: Analytics & ML pipeline completed! Full bundle saved to: {output_json}")
    print("=" * 80)


if __name__ == "__main__":
    main()
