"""
CloudSense AI — BigQuery Data Validation
Compares a live BigQuery warehouse against the local Gold/Mart Parquet
datasets that were used to populate it, and runs a set of data-quality
checks equivalent to sql/bigquery/validation_queries.sql.

This module is only ever invoked manually (via run_bigquery_migration.py or
directly), never by the running API. It requires a BigQueryClient (and
therefore the optional google-cloud-bigquery dependency) to do anything
useful — see bigquery_client.py for the lazy-import discipline that keeps
this module safe to import without that dependency installed.

Every check in this module actually executes a query/comparison and reports
a concrete pass/fail result with the observed values — it never reports
"validation succeeded" without having compared real numbers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.pipeline.bigquery_client import BigQueryClient
from src.pipeline.schema import GOLD_TABLE_SCHEMAS, MART_TABLE_SCHEMAS


def _local_row_count(processed_dir: Path, table_name: str) -> Optional[int]:
    """Reads the local Gold/Mart Parquet file's row count for comparison.
    Returns None (not 0) if the file doesn't exist, so callers can
    distinguish "file missing" from "file has zero rows"."""
    for subdir in ("gold", "marts"):
        candidate = Path(processed_dir) / subdir / f"{table_name}.parquet"
        if candidate.exists():
            return len(pd.read_parquet(candidate, columns=[]))
    return None


def validate_table_row_counts(
    client: BigQueryClient, data_dir: Path
) -> Dict[str, Any]:
    """
    For every Gold + Mart table, compares BigQuery's row count against the
    local Parquet file's row count. This is the most important validation
    per the Phase 6 requirements — it does not just check that BigQuery
    queries execute, it verifies the loaded data is complete.
    """
    results = []
    all_tables = {**GOLD_TABLE_SCHEMAS, **MART_TABLE_SCHEMAS}

    for table_name in all_tables:
        local_count = _local_row_count(data_dir, table_name)
        bq_exists = client.table_exists(table_name)
        bq_count = client.get_row_count(table_name) if bq_exists else None

        match = (local_count is not None and bq_count is not None and local_count == bq_count)
        results.append({
            "table": table_name,
            "local_parquet_row_count": local_count,
            "bigquery_row_count": bq_count,
            "bigquery_table_exists": bq_exists,
            "match": match,
        })

    all_match = all(r["match"] for r in results)
    return {
        "check": "table_row_counts",
        "passed": all_match,
        "tables": results,
    }


def validate_table_schemas(client: BigQueryClient) -> Dict[str, Any]:
    """Confirms every expected column exists in the corresponding BigQuery
    table (does not require exact type-string equality, since BigQuery's
    reported type names differ from our internal schema.py type strings —
    but a missing column is a hard failure)."""
    results = []
    all_tables = {**GOLD_TABLE_SCHEMAS, **MART_TABLE_SCHEMAS}

    for table_name, expected_schema in all_tables.items():
        if not client.table_exists(table_name):
            results.append({
                "table": table_name, "passed": False,
                "reason": "Table does not exist in BigQuery.",
            })
            continue

        actual_fields = set(client.get_schema_fields(table_name))
        expected_fields = set(expected_schema.keys())
        missing = sorted(expected_fields - actual_fields)
        extra = sorted(actual_fields - expected_fields)

        results.append({
            "table": table_name,
            "passed": len(missing) == 0,
            "missing_columns": missing,
            "extra_columns": extra,
        })

    all_passed = all(r["passed"] for r in results)
    return {"check": "table_schemas", "passed": all_passed, "tables": results}


def validate_null_constraints(client: BigQueryClient, dataset_ref: str) -> Dict[str, Any]:
    """Checks that key/date columns in fact_cost contain no NULLs."""
    checks = []
    for column in ("resource_id", "usage_date", "service_id", "region_id"):
        rows = client.run_query(f"SELECT COUNT(*) AS n FROM `{dataset_ref}.fact_cost` WHERE {column} IS NULL")
        null_count = rows[0]["n"] if rows else None
        checks.append({"column": column, "null_count": null_count, "passed": null_count == 0})
    return {"check": "null_constraints", "passed": all(c["passed"] for c in checks), "columns": checks}


def validate_duplicate_business_keys(client: BigQueryClient, dataset_ref: str) -> Dict[str, Any]:
    """fact_cost should have exactly one row per (resource_id, usage_date)."""
    rows = client.run_query(f"""
        SELECT COUNT(*) AS duplicate_key_groups FROM (
            SELECT resource_id, usage_date
            FROM `{dataset_ref}.fact_cost`
            GROUP BY resource_id, usage_date
            HAVING COUNT(*) > 1
        )
    """)
    duplicate_groups = rows[0]["duplicate_key_groups"] if rows else None
    return {
        "check": "duplicate_business_keys",
        "passed": duplicate_groups == 0,
        "duplicate_key_groups_found": duplicate_groups,
    }


def validate_non_negative_costs(client: BigQueryClient, dataset_ref: str) -> Dict[str, Any]:
    rows = client.run_query(f"""
        SELECT COUNT(*) AS negative_rows FROM `{dataset_ref}.fact_cost`
        WHERE list_cost_usd < 0 OR discount_amount_usd < 0 OR net_cost_usd < 0
    """)
    negative_rows = rows[0]["negative_rows"] if rows else None
    return {"check": "non_negative_costs", "passed": negative_rows == 0, "negative_rows_found": negative_rows}


def validate_pricing_consistency(client: BigQueryClient, dataset_ref: str) -> Dict[str, Any]:
    """net_cost_usd should equal list_cost_usd - discount_amount_usd (within tolerance)."""
    rows = client.run_query(f"""
        SELECT COUNT(*) AS inconsistent_rows FROM `{dataset_ref}.fact_cost`
        WHERE ABS(net_cost_usd - (list_cost_usd - discount_amount_usd)) > 0.01
    """)
    inconsistent_rows = rows[0]["inconsistent_rows"] if rows else None
    return {
        "check": "pricing_consistency",
        "passed": inconsistent_rows == 0,
        "inconsistent_rows_found": inconsistent_rows,
    }


def validate_referential_integrity(client: BigQueryClient, dataset_ref: str) -> Dict[str, Any]:
    checks = []
    joins = [
        ("resource_id", "dim_resource"),
        ("service_id", "dim_service"),
        ("region_id", "dim_region"),
        ("provider_id", "dim_provider"),
    ]
    for fk_col, dim_table in joins:
        rows = client.run_query(f"""
            SELECT COUNT(*) AS orphaned_rows
            FROM `{dataset_ref}.fact_cost` c
            LEFT JOIN `{dataset_ref}.{dim_table}` d ON c.{fk_col} = d.{fk_col}
            WHERE d.{fk_col} IS NULL
        """)
        orphaned = rows[0]["orphaned_rows"] if rows else None
        checks.append({"foreign_key": fk_col, "dimension_table": dim_table, "orphaned_rows": orphaned, "passed": orphaned == 0})
    return {"check": "referential_integrity", "passed": all(c["passed"] for c in checks), "foreign_keys": checks}


def validate_date_ranges(client: BigQueryClient, dataset_ref: str) -> Dict[str, Any]:
    rows = client.run_query(f"""
        SELECT MIN(usage_date) AS earliest_date, MAX(usage_date) AS latest_date,
               COUNT(DISTINCT usage_date) AS distinct_days
        FROM `{dataset_ref}.fact_cost`
    """)
    result = rows[0] if rows else {}
    # A passing check simply means the query returned a sensible, non-null range;
    # the actual expected span (e.g. 250 days) is confirmed by the caller
    # against data_quality_report.md if desired — this function reports facts,
    # it does not assume what the "correct" span should be.
    passed = bool(result.get("earliest_date") and result.get("latest_date") and result.get("distinct_days", 0) > 0)
    return {"check": "date_ranges", "passed": passed, **result}


def validate_anomaly_ground_truth(client: BigQueryClient, dataset_ref: str) -> Dict[str, Any]:
    """Cross-checks fact_anomaly's row count against mart_anomalies' aggregated
    incident-days figure — both are derived from the same underlying anomaly
    labels, so they should be mutually consistent (mart incident-days should
    be <= fact row count, since a mart groups by anomaly_type/severity)."""
    rows = client.run_query(f"""
        SELECT
          (SELECT COUNT(*) FROM `{dataset_ref}.fact_anomaly`) AS fact_anomaly_row_count,
          (SELECT SUM(incident_days_count) FROM `{dataset_ref}.mart_anomalies`) AS mart_incident_days_sum
    """)
    result = rows[0] if rows else {}
    fact_count = result.get("fact_anomaly_row_count")
    mart_sum = result.get("mart_incident_days_sum")
    # incident_days_count in the mart counts distinct days per anomaly group,
    # so it should never exceed the raw fact row count.
    passed = fact_count is not None and mart_sum is not None and mart_sum <= fact_count
    return {"check": "anomaly_ground_truth_consistency", "passed": passed, **result}


def run_full_validation(client: BigQueryClient, data_dir: Path) -> Dict[str, Any]:
    """
    Runs every validation check and returns a single aggregated report.
    This is the function run_bigquery_migration.py calls after loading data.
    """
    dataset_ref = client.dataset_ref
    checks = [
        validate_table_row_counts(client, data_dir),
        validate_table_schemas(client),
        validate_null_constraints(client, dataset_ref),
        validate_duplicate_business_keys(client, dataset_ref),
        validate_non_negative_costs(client, dataset_ref),
        validate_pricing_consistency(client, dataset_ref),
        validate_referential_integrity(client, dataset_ref),
        validate_date_ranges(client, dataset_ref),
        validate_anomaly_ground_truth(client, dataset_ref),
    ]
    return {
        "overall_passed": all(c["passed"] for c in checks),
        "checks": checks,
    }
