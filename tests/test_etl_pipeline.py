"""
CloudSense AI — Unit & Integration Test Suite for Medallion ETL & Warehouse
Validates data transformations, dimensional integrity, and mart reconciliations.
"""

from pathlib import Path
import pytest
import pandas as pd
import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(scope="module")
def data_paths():
    return {
        "bronze": DATA_DIR / "bronze" / "bronze_cloud_usage.parquet",
        "silver": DATA_DIR / "silver" / "silver_cloud_usage.parquet",
        "gold": DATA_DIR / "gold",
        "marts": DATA_DIR / "marts",
        "warehouse_db": DATA_DIR / "cloudsense_warehouse.duckdb"
    }


def test_bronze_metadata_columns(data_paths):
    """Asserts Bronze table has required ingestion metadata."""
    df_bronze = pd.read_parquet(data_paths["bronze"])
    assert len(df_bronze) == 50000
    for col in ["_ingested_at", "_batch_id", "_source_file", "_record_hash"]:
        assert col in df_bronze.columns
        assert df_bronze[col].isnull().sum() == 0


def test_silver_data_consistency(data_paths):
    """Asserts Silver dataset enforces bounds and financial invariants."""
    df_silver = pd.read_parquet(data_paths["silver"])
    assert len(df_silver) == 50000

    # CPU/RAM bounds
    assert (df_silver["avg_cpu_utilization_pct"] >= 0.0).all()
    assert (df_silver["max_cpu_utilization_pct"] <= 100.0).all()
    assert (df_silver["max_cpu_utilization_pct"] >= df_silver["avg_cpu_utilization_pct"]).all()

    # Cost equation: Net = List - Discount
    cost_diff = (df_silver["list_cost_usd"] - df_silver["discount_amount_usd"]) - df_silver["net_cost_usd"]
    assert (cost_diff.abs() < 0.001).all()

    # Carbon equation: Total = Scope2 + Scope3
    carb_diff = (df_silver["scope2_location_based_gco2e"] + df_silver["scope3_embodied_gco2e"]) - df_silver["total_carbon_gco2e"]
    assert (carb_diff.abs() < 0.002).all()


def test_gold_dimension_primary_keys(data_paths):
    """Asserts uniqueness and non-null on all dimension primary keys."""
    gold_dir = data_paths["gold"]
    
    dim_date = pd.read_parquet(gold_dir / "dim_date.parquet")
    assert dim_date["date_key"].nunique() == len(dim_date) == 250
    assert dim_date["date_key"].isnull().sum() == 0

    dim_provider = pd.read_parquet(gold_dir / "dim_provider.parquet")
    assert dim_provider["provider_id"].nunique() == len(dim_provider) == 1

    dim_region = pd.read_parquet(gold_dir / "dim_region.parquet")
    assert dim_region["region_id"].nunique() == len(dim_region) == 5

    dim_service = pd.read_parquet(gold_dir / "dim_service.parquet")
    assert dim_service["service_id"].nunique() == len(dim_service) == 7

    dim_resource = pd.read_parquet(gold_dir / "dim_resource.parquet")
    assert dim_resource["resource_id"].nunique() == len(dim_resource) == 200


def test_gold_fact_grains_and_keys(data_paths):
    """Asserts row counts and primary key uniqueness on all fact tables."""
    gold_dir = data_paths["gold"]

    fact_usage = pd.read_parquet(gold_dir / "fact_usage.parquet")
    assert len(fact_usage) == 50000
    assert fact_usage["usage_fact_id"].nunique() == 50000

    fact_cost = pd.read_parquet(gold_dir / "fact_cost.parquet")
    assert len(fact_cost) == 50000
    assert fact_cost["cost_fact_id"].nunique() == 50000

    fact_carbon = pd.read_parquet(gold_dir / "fact_carbon.parquet")
    assert len(fact_carbon) == 50000
    assert fact_carbon["carbon_fact_id"].nunique() == 50000

    fact_anomaly = pd.read_parquet(gold_dir / "fact_anomaly.parquet")
    assert len(fact_anomaly) == 18
    assert fact_anomaly["anomaly_fact_id"].nunique() == 18


def test_gold_referential_integrity(data_paths):
    """Asserts foreign key integrity from facts to dimensions."""
    gold_dir = data_paths["gold"]

    dim_res = set(pd.read_parquet(gold_dir / "dim_resource.parquet")["resource_id"])
    dim_srv = set(pd.read_parquet(gold_dir / "dim_service.parquet")["service_id"])
    dim_reg = set(pd.read_parquet(gold_dir / "dim_region.parquet")["region_id"])
    dim_dt = set(pd.read_parquet(gold_dir / "dim_date.parquet")["date_key"])

    for fact_file in ["fact_usage.parquet", "fact_cost.parquet", "fact_carbon.parquet"]:
        fact = pd.read_parquet(gold_dir / fact_file)
        assert set(fact["resource_id"]).issubset(dim_res)
        assert set(fact["service_id"]).issubset(dim_srv)
        assert set(fact["region_id"]).issubset(dim_reg)
        assert set(fact["date_key"]).issubset(dim_dt)


def test_marts_financial_reconciliation(data_paths):
    """Asserts Analytics Marts spend totals reconcile with Fact table totals."""
    fact_cost = pd.read_parquet(data_paths["gold"] / "fact_cost.parquet")
    mart_trends = pd.read_parquet(data_paths["marts"] / "mart_cost_trends.parquet")
    mart_summary = pd.read_parquet(data_paths["marts"] / "mart_cost_summary.parquet")

    fact_total = fact_cost["net_cost_usd"].sum()
    trends_total = mart_trends["total_net_cost_usd"].sum()
    summary_total = mart_summary["total_net_cost_usd"].sum()

    assert abs(fact_total - trends_total) < 0.10
    assert abs(fact_total - summary_total) < 0.10


def test_duckdb_warehouse_queries(data_paths):
    """Asserts SQL query execution against DuckDB views."""
    conn = duckdb.connect(str(data_paths["warehouse_db"]))
    
    # Query total cost by service family
    query = """
    SELECT 
        s.service_family,
        COUNT(*) as row_count,
        ROUND(SUM(c.net_cost_usd), 2) as total_spend
    FROM fact_cost c
    JOIN dim_service s ON c.service_id = s.service_id
    GROUP BY s.service_family
    ORDER BY total_spend DESC
    """
    res = conn.execute(query).fetchdf()
    assert len(res) == 7
    assert res["total_spend"].sum() > 700000.0
    conn.close()
