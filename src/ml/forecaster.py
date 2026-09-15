"""
CloudSense AI — Cost Forecasting Engine
Implements chronological time-series forecasting comparing an interpretable
statistical baseline against machine learning regressors (Ridge & Random Forest),
evaluated via out-of-sample MAE, RMSE, and MAPE.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

from src.analytics.schemas import (
    ForecastingOutput,
    ModelEvaluationMetrics,
    ForecastPoint
)


class CostForecaster:
    """
    Builds and evaluates daily time-series forecasting models
    with strict chronological train/test splitting and confidence intervals.
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.marts_dir = data_dir / "marts"
        self._load_dataset()

    def _load_dataset(self):
        # Load daily trend time series (250 days)
        self.daily_df = pd.read_parquet(self.marts_dir / "mart_cost_trends.parquet")
        self.daily_df["usage_date"] = pd.to_datetime(self.daily_df["usage_date"])
        self.daily_df = self.daily_df.sort_values("usage_date").reset_index(drop=True)

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates autoregressive lag features, rolling statistics, and calendar encodings.
        """
        data = df.copy()
        target = "total_net_cost_usd"

        # Lags
        data["lag_1"] = data[target].shift(1)
        data["lag_2"] = data[target].shift(2)
        data["lag_7"] = data[target].shift(7)
        data["lag_14"] = data[target].shift(14)

        # Rolling Statistics (lagged to prevent leakage)
        data["rolling_mean_7"] = data[target].shift(1).rolling(7).mean()
        data["rolling_std_7"] = data[target].shift(1).rolling(7).std()
        data["rolling_mean_14"] = data[target].shift(1).rolling(14).mean()

        # Calendar Features
        data["day_of_week"] = data["usage_date"].dt.dayofweek
        data["is_weekend"] = (data["day_of_week"] >= 5).astype(int)
        data["day_of_month"] = data["usage_date"].dt.day
        data["is_month_end"] = data["usage_date"].dt.is_month_end.astype(int)

        # Cyclic Day of Month Encoding
        data["dom_sin"] = np.sin(2 * np.pi * data["day_of_month"] / 31.0)
        data["dom_cos"] = np.cos(2 * np.pi * data["day_of_month"] / 31.0)

        # Day of week one-hot
        for dow in range(7):
            data[f"dow_{dow}"] = (data["day_of_week"] == dow).astype(int)

        return data.dropna().reset_index(drop=True)

    def evaluate_models(self) -> Tuple[List[ModelEvaluationMetrics], Any, List[str]]:
        """
        Performs strict chronological evaluation:
        - Train set: First 190 days
        - Validation/Test set: Final 30 days
        Compares Baseline (7-Day Seasonal MA) vs Ridge Regression vs Random Forest.
        """
        feat_df = self.prepare_features(self.daily_df)
        
        feature_cols = [
            "lag_1", "lag_2", "lag_7", "lag_14",
            "rolling_mean_7", "rolling_std_7", "rolling_mean_14",
            "is_weekend", "is_month_end", "dom_sin", "dom_cos",
            "dow_0", "dow_1", "dow_2", "dow_3", "dow_4", "dow_5", "dow_6"
        ]
        target_col = "total_net_cost_usd"

        # Chronological Split (Last 30 days as test set)
        test_size = 30
        train_df = feat_df.iloc[:-test_size].copy()
        test_df = feat_df.iloc[-test_size:].copy()

        X_train = train_df[feature_cols]
        y_train = train_df[target_col].values
        X_test = test_df[feature_cols]
        y_test = test_df[target_col].values

        metrics_list: List[ModelEvaluationMetrics] = []
        trained_models = {}

        # ---------------------------------------------------------------------
        # 1. Baseline Model: 7-Day Seasonal Moving Average
        # ---------------------------------------------------------------------
        # Uses lag_7 as the seasonal baseline prediction
        y_pred_base = test_df["lag_7"].values
        mae_base = float(np.mean(np.abs(y_test - y_pred_base)))
        rmse_base = float(np.sqrt(np.mean((y_test - y_pred_base) ** 2)))
        mape_base = float(np.mean(np.abs((y_test - y_pred_base) / y_test)) * 100.0)

        metrics_list.append(ModelEvaluationMetrics(
            model_name="Baseline (7-Day Seasonal Moving Average)",
            mae=round(mae_base, 2),
            rmse=round(rmse_base, 2),
            mape_pct=round(mape_base, 2),
            train_samples=len(train_df),
            test_samples=len(test_df)
        ))

        # ---------------------------------------------------------------------
        # 2. ML Model 1: Regularized Ridge Regression
        # ---------------------------------------------------------------------
        ridge = Ridge(alpha=10.0, random_state=42)
        ridge.fit(X_train, y_train)
        y_pred_ridge = ridge.predict(X_test)

        mae_ridge = float(np.mean(np.abs(y_test - y_pred_ridge)))
        rmse_ridge = float(np.sqrt(np.mean((y_test - y_pred_ridge) ** 2)))
        mape_ridge = float(np.mean(np.abs((y_test - y_pred_ridge) / y_test)) * 100.0)

        metrics_list.append(ModelEvaluationMetrics(
            model_name="Regularized Ridge Regression",
            mae=round(mae_ridge, 2),
            rmse=round(rmse_ridge, 2),
            mape_pct=round(mape_ridge, 2),
            train_samples=len(train_df),
            test_samples=len(test_df)
        ))
        trained_models["Regularized Ridge Regression"] = (ridge, rmse_ridge)

        # ---------------------------------------------------------------------
        # 3. ML Model 2: Random Forest Regressor
        # ---------------------------------------------------------------------
        rf = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
        rf.fit(X_train, y_train)
        y_pred_rf = rf.predict(X_test)

        mae_rf = float(np.mean(np.abs(y_test - y_pred_rf)))
        rmse_rf = float(np.sqrt(np.mean((y_test - y_pred_rf) ** 2)))
        mape_rf = float(np.mean(np.abs((y_test - y_pred_rf) / y_test)) * 100.0)

        metrics_list.append(ModelEvaluationMetrics(
            model_name="Random Forest Regressor",
            mae=round(mae_rf, 2),
            rmse=round(rmse_rf, 2),
            mape_pct=round(mape_rf, 2),
            train_samples=len(train_df),
            test_samples=len(test_df)
        ))
        trained_models["Random Forest Regressor"] = (rf, rmse_rf)

        # Select champion model based on lowest RMSE
        best_model_name = min(trained_models, key=lambda k: trained_models[k][1])
        champion_model = trained_models[best_model_name][0]

        return metrics_list, champion_model, feature_cols

    def generate_multistep_forecast(
        self,
        model: Any,
        feature_cols: List[str],
        horizon_days: int = 90
    ) -> List[ForecastPoint]:
        """
        Produces recursive multi-step daily forecasts with 80% and 95% confidence intervals.
        """
        feat_df = self.prepare_features(self.daily_df)
        history = self.daily_df["total_net_cost_usd"].tolist()
        dates = self.daily_df["usage_date"].tolist()

        last_date = dates[-1]
        forecast_points: List[ForecastPoint] = []

        # Residual std dev for empirical confidence bounds
        test_size = 30
        train_df = feat_df.iloc[:-test_size]
        residuals = train_df["total_net_cost_usd"] - model.predict(train_df[feature_cols])
        residual_std = float(np.std(residuals))

        for step in range(1, horizon_days + 1):
            next_date = last_date + timedelta(days=step)
            dow = next_date.weekday()
            dom = next_date.day
            is_weekend = 1 if dow >= 5 else 0
            is_month_end = 1 if next_date.is_month_end else 0

            # Construct dynamic lag feature vector
            row_dict = {
                "lag_1": history[-1],
                "lag_2": history[-2],
                "lag_7": history[-7],
                "lag_14": history[-14],
                "rolling_mean_7": float(np.mean(history[-7:])),
                "rolling_std_7": float(np.std(history[-7:])),
                "rolling_mean_14": float(np.mean(history[-14:])),
                "is_weekend": is_weekend,
                "is_month_end": is_month_end,
                "dom_sin": np.sin(2 * np.pi * dom / 31.0),
                "dom_cos": np.cos(2 * np.pi * dom / 31.0),
            }
            for d in range(7):
                row_dict[f"dow_{d}"] = 1 if dow == d else 0

            feat_vector = pd.DataFrame([row_dict])[feature_cols]
            pred = float(model.predict(feat_vector)[0])
            pred = max(100.0, pred)  # Physical non-negative lower bound
            history.append(pred)

            # Confidence cones expand slightly with horizon step h: sigma_h = sigma * sqrt(1 + 0.01*h)
            h_std = residual_std * np.sqrt(1.0 + 0.015 * step)
            z_80 = 1.282
            z_95 = 1.960

            forecast_points.append(ForecastPoint(
                date=next_date.strftime("%Y-%m-%d"),
                predicted_cost_usd=round(pred, 2),
                lower_bound_80_usd=round(max(0.0, pred - z_80 * h_std), 2),
                upper_bound_80_usd=round(pred + z_80 * h_std, 2),
                lower_bound_95_usd=round(max(0.0, pred - z_95 * h_std), 2),
                upper_bound_95_usd=round(pred + z_95 * h_std, 2)
            ))

        return forecast_points

    def generate_full_report(self) -> ForecastingOutput:
        """Runs evaluation and generates 30, 60, and 90-day cost forecasts."""
        metrics, champion, features = self.evaluate_models()
        best_name = min(metrics, key=lambda m: m.rmse).model_name

        fc_90 = self.generate_multistep_forecast(champion, features, horizon_days=90)
        fc_30 = fc_90[:30]
        fc_60 = fc_90[:60]

        last_30_hist = self.daily_df.tail(30)[["usage_date", "total_net_cost_usd"]].copy()
        last_30_hist["date"] = last_30_hist["usage_date"].dt.strftime("%Y-%m-%d")
        hist_records = last_30_hist[["date", "total_net_cost_usd"]].to_dict(orient="records")

        # Projected 30-day forward monthly spend
        proj_monthly = sum(p.predicted_cost_usd for p in fc_30)

        return ForecastingOutput(
            champion_model=best_name,
            train_horizon="Day 1 to 220 (220 days)",
            test_horizon="Day 221 to 250 (Last 30 days holdout)",
            models_evaluated=metrics,
            historical_last_30_days=hist_records,
            forecast_30_days=fc_30,
            forecast_60_days=fc_60,
            forecast_90_days=fc_90,
            projected_monthly_spend_usd=round(proj_monthly, 2)
        )
