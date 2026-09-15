"""
CloudSense AI — Shared Pytest Configuration
Ensures the local DuckDB warehouse views are portable across machines.

The DuckDB warehouse file (`data/cloudsense_warehouse.duckdb`) stores its
Gold/Mart tables as SQL views over external Parquet files. The absolute file
path used to build those views is baked in at the moment the views are
created. If the repository is copied to a different machine (or a different
path on the same machine), those baked-in paths go stale and any direct
DuckDB query against the file fails with a "no files found" error.

`WarehouseManager` already derives these paths dynamically from the current
`data/` directory rather than hardcoding them — so simply instantiating it
before the test session runs re-creates ("CREATE OR REPLACE VIEW") all views
against paths that are valid *for the machine currently running the tests*.
This makes the warehouse self-healing and fully portable, without requiring
any changes to the existing test modules.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="session", autouse=True)
def _ensure_portable_warehouse_views():
    """Refreshes DuckDB warehouse views to point at this machine's Parquet paths."""
    db_path = DATA_DIR / "cloudsense_warehouse.duckdb"
    if db_path.exists():
        from src.pipeline.warehouse import WarehouseManager

        warehouse = WarehouseManager(data_dir=DATA_DIR)
        warehouse.close()
    yield
