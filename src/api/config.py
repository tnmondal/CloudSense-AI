"""
CloudSense AI — API Configuration Management
Loads application settings and environment variables using Pydantic Settings.
"""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "CloudSense AI — Cloud Cost, Usage & Carbon Intelligence API"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"
    environment: str = "production"
    debug: bool = False
    cors_origins: List[str] = ["*"]
    
    # Data & Warehouse Paths
    data_dir: Path = REPO_ROOT / "data"
    analytics_summary_path: Path = REPO_ROOT / "data" / "analytics_summary.json"
    warehouse_db_path: Path = REPO_ROOT / "data" / "cloudsense_warehouse.duckdb"

    # --- Phase 6: BigQuery data-backend configuration (all optional, additive) ---
    # These settings exist so a FUTURE phase can switch AnalyticsService to
    # read from BigQuery instead of the local analytics_summary.json, without
    # requiring another config-schema change. They have NO effect in the
    # current codebase: AnalyticsService always reads the local JSON file
    # regardless of these values. Defaulting `data_backend` to "local" means
    # the application behaves exactly as it did before Phase 6 when these
    # variables are left unset.
    data_backend: str = "local"  # "local" (default) | "bigquery" (reserved for a future phase)
    gcp_project_id: str = ""
    bigquery_dataset: str = "cloudsense_dw"

    model_config = SettingsConfigDict(env_prefix="CLOUDSENSE_", case_sensitive=False)


settings = Settings()
