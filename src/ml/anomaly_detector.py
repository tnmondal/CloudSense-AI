"""
CloudSense AI — Statistical Anomaly Detection Engine
Implements interpretable, multi-tiered statistical anomaly detection
using Rolling Z-Score, Modified MAD, and Interquartile Range (IQR) fences.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from src.analytics.schemas import AnomalyDetectionOutput, AnomalyEvent


class AnomalyDetector:
    """
    Detects unbudgeted cost surges and abnormal workload spikes
    using rolling statistical baselines and robust non-parametric screening.
    """

    # Configurable detection thresholds
    DEFAULT_CONFIG = {
        "rolling_window_days": 14,
        "zscore_threshold": 3.0,
        "modified_mad_threshold": 3.5,
        "iqr_multiplier": 2.0,
        "min_dollar_deviation_usd": 40.0,
    }

    def __init__(self, data_dir: Path, config: Optional[Dict[str, Any]] = None):
        self.data_dir = data_dir
        self.gold_dir = data_dir / "gold"
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._load_datasets()

    def _load_datasets(self):
        self.fact_cost = pd.read_parquet(self.gold_dir / "fact_cost.parquet")
        self.fact_usage = pd.read_parquet(self.gold_dir / "fact_usage.parquet")
        self.dim_resource = pd.read_parquet(self.gold_dir / "dim_resource.parquet")
        self.dim_service = pd.read_parquet(self.gold_dir / "dim_service.parquet")

        self.enriched = self.fact_cost.merge(
            self.dim_resource[["resource_id", "resource_name", "department", "environment"]],
            on="resource_id",
            how="left"
        ).merge(
            self.dim_service[["service_id", "service_name", "service_family"]],
            on="service_id",
            how="left"
        )

    def detect_resource_cost_anomalies(self) -> List[AnomalyEvent]:
        """
        Runs rolling statistical screening (Z-Score, Modified MAD, IQR)
        on daily spend for each individual cloud resource.
        """
        anomalies: List[AnomalyEvent] = []
        w = self.config["rolling_window_days"]
        z_thresh = self.config["zscore_threshold"]
        mad_thresh = self.config["modified_mad_threshold"]
        iqr_mult = self.config["iqr_multiplier"]
        min_usd = self.config["min_dollar_deviation_usd"]

        resources = self.enriched["resource_id"].unique()

        for res_id in resources:
            res_df = self.enriched[self.enriched["resource_id"] == res_id].sort_values("usage_date").reset_index(drop=True)
            if len(res_df) < w + 2:
                continue

            costs = res_df["net_cost_usd"].values
            dates = res_df["usage_date"].values
            srv_name = res_df["service_name"].iloc[0]

            for t in range(w, len(res_df)):
                current_cost = costs[t]
                history = costs[t - w:t]

                mean_hist = float(np.mean(history))
                std_hist = float(np.std(history))
                median_hist = float(np.median(history))
                mad_hist = float(np.median(np.abs(history - median_hist)))
                q1 = float(np.percentile(history, 25))
                q3 = float(np.percentile(history, 75))
                iqr = q3 - q1

                # 1. Z-Score Test
                z_score = (current_cost - mean_hist) / std_hist if std_hist > 0.001 else 0.0

                # 2. Modified MAD Test
                mod_mad = (0.6745 * (current_cost - median_hist)) / mad_hist if mad_hist > 0.001 else 0.0

                # 3. IQR Test
                iqr_fence = q3 + (iqr_mult * iqr)
                iqr_flag = (current_cost > iqr_fence)

                dollar_diff = current_cost - median_hist

                # Voting gate: Flag if at least 2 methods trigger and dollar surge >= threshold
                method_votes = sum([z_score > z_thresh, mod_mad > mad_thresh, iqr_flag])

                if method_votes >= 2 and dollar_diff >= min_usd:
                    # Determine primary detection method and severity
                    if mod_mad > mad_thresh:
                        primary_method = "Rolling Modified MAD"
                        score = mod_mad
                    else:
                        primary_method = "Rolling Z-Score"
                        score = z_score

                    pct_surge = (dollar_diff / max(median_hist, 0.01)) * 100.0

                    if dollar_diff > 500.0 or pct_surge > 300.0:
                        severity = "Critical"
                    elif dollar_diff > 150.0 or pct_surge > 150.0:
                        severity = "High"
                    else:
                        severity = "Medium"

                    expl = (
                        f"Daily cost surged to ${current_cost:.2f} (baseline: ${median_hist:.2f}), "
                        f"representing a +{pct_surge:.1f}% deviation (+${dollar_diff:.2f}) "
                        f"flagged by {primary_method} (score: {score:.2f})."
                    )

                    anomalies.append(AnomalyEvent(
                        anomaly_id=f"ANOM-{dates[t].replace('-', '')}-{len(anomalies) + 1:03d}",
                        target_type="resource",
                        target_id=res_id,
                        service_name=srv_name,
                        timestamp=dates[t],
                        metric_name="daily_net_cost_usd",
                        observed_value=round(float(current_cost), 2),
                        expected_value=round(float(median_hist), 2),
                        anomaly_score=round(float(score), 2),
                        detection_method=primary_method,
                        severity=severity,
                        financial_impact_usd=round(float(dollar_diff), 2),
                        explanation=expl
                    ))

        return anomalies

    def generate_full_report(self) -> AnomalyDetectionOutput:
        """Executes full anomaly detection and aggregates impact metrics."""
        anomalies = self.detect_resource_cost_anomalies()

        severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        method_counts = {}
        total_surge = 0.0

        for a in anomalies:
            severity_counts[a.severity] = severity_counts.get(a.severity, 0) + 1
            method_counts[a.detection_method] = method_counts.get(a.detection_method, 0) + 1
            total_surge += a.financial_impact_usd

        return AnomalyDetectionOutput(
            total_anomalies_detected=len(anomalies),
            anomalies_by_severity=severity_counts,
            anomalies_by_method=method_counts,
            total_unbudgeted_dollar_impact=round(total_surge, 2),
            detected_anomalies=anomalies
        )
