#!/usr/bin/env python3
"""
CloudSense AI — BigQuery Migration Script (Phase 6)
=====================================================

Manually-executed, one-shot script that provisions a BigQuery data warehouse
mirroring the local Gold/Mart Parquet layer and validates the load.

THIS SCRIPT IS NEVER RUN AUTOMATICALLY. It is not imported by, or invoked
from, the FastAPI application, the test suite, or any startup path. It must
be run explicitly by an operator from the command line.

It does NOT change how the running application serves data — AnalyticsService
continues to read data/analytics_summary.json regardless of whether this
script has ever been run (see docs/bigquery_migration.md).

Usage:
    pip install -r requirements.txt
    pip install -r requirements-bigquery.txt
    gcloud auth application-default login   # or set GOOGLE_APPLICATION_CREDENTIALS
    export CLOUDSENSE_GCP_PROJECT_ID=your-gcp-project-id
    export CLOUDSENSE_BIGQUERY_DATASET=cloudsense_dw   # optional, this is the default
    python3 run_bigquery_migration.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from src.api.config import settings  # noqa: E402


def _fail(message: str) -> None:
    print(f"\n[MIGRATION ABORTED] {message}\n")
    sys.exit(1)


def main() -> None:
    print("=" * 78)
    print("CloudSense AI — BigQuery Migration (Phase 6)")
    print("=" * 78)

    # ------------------------------------------------------------------
    # 1. Validate required configuration BEFORE importing google-cloud-bigquery,
    #    so a misconfigured environment fails with a clear message instead of
    #    an unrelated import error.
    # ------------------------------------------------------------------
    project_id = settings.gcp_project_id.strip()
    dataset_id = settings.bigquery_dataset.strip() or "cloudsense_dw"

    if not project_id:
        _fail(
            "CLOUDSENSE_GCP_PROJECT_ID is not set. Set it to your target Google "
            "Cloud project ID before running this migration, e.g.:\n\n"
            "    export CLOUDSENSE_GCP_PROJECT_ID=your-gcp-project-id"
        )

    print(f"Target project:  {project_id}")
    print(f"Target dataset:  {dataset_id}")
    print(f"Local data dir:  {settings.data_dir}")

    gold_dir = settings.data_dir / "gold"
    marts_dir = settings.data_dir / "marts"
    if not gold_dir.exists() or not marts_dir.exists():
        _fail(
            f"Expected Gold/Marts Parquet directories not found under {settings.data_dir}. "
            f"Run `python3 run_pipeline.py` first to generate the local warehouse."
        )

    # ------------------------------------------------------------------
    # 2. Import the BigQuery client now (lazy import — gives a clean error
    #    if requirements-bigquery.txt hasn't been installed).
    # ------------------------------------------------------------------
    try:
        from src.pipeline.bigquery_client import BigQueryClient, GOLD_TABLE_SCHEMAS, MART_TABLE_SCHEMAS
        from src.pipeline.bigquery_validation import run_full_validation
    except Exception as exc:  # BigQueryDependencyError or import error
        _fail(str(exc))
        return

    try:
        client = BigQueryClient(project_id=project_id, dataset_id=dataset_id)
    except Exception as exc:
        _fail(f"Failed to initialize BigQuery client (check authentication / project access): {exc}")
        return

    # ------------------------------------------------------------------
    # 3. Create the dataset if needed
    # ------------------------------------------------------------------
    print("\n[1/6] Ensuring BigQuery dataset exists...")
    try:
        client.ensure_dataset()
        print(f"      Dataset ready: {client.dataset_ref}")
    except Exception as exc:
        _fail(f"Failed to create/verify dataset: {exc}")
        return

    # ------------------------------------------------------------------
    # 4. Create tables (Gold dims/facts + Marts)
    # ------------------------------------------------------------------
    print("\n[2/6] Creating BigQuery tables (schema from src/pipeline/schema.py)...")
    try:
        created_tables = client.create_all_tables()
        print(f"      Created/verified {len(created_tables)} tables.")
    except Exception as exc:
        _fail(f"Failed to create tables: {exc}")
        return

    # ------------------------------------------------------------------
    # 5. Load Gold Parquet files
    # ------------------------------------------------------------------
    print("\n[3/6] Loading Gold Parquet files...")
    load_results = []
    for table_name in GOLD_TABLE_SCHEMAS:
        parquet_path = gold_dir / f"{table_name}.parquet"
        if not parquet_path.exists():
            print(f"      SKIP {table_name}: {parquet_path} not found.")
            load_results.append({"table": table_name, "status": "skipped_missing_file"})
            continue
        try:
            rows_loaded = client.load_parquet(table_name, parquet_path)
            print(f"      Loaded {table_name}: {rows_loaded:,} rows")
            load_results.append({"table": table_name, "status": "loaded", "rows": rows_loaded})
        except Exception as exc:
            print(f"      FAILED {table_name}: {exc}")
            load_results.append({"table": table_name, "status": "failed", "error": str(exc)})

    # ------------------------------------------------------------------
    # 6. Load Mart Parquet files
    # ------------------------------------------------------------------
    print("\n[4/6] Loading Analytics Mart Parquet files...")
    for table_name in MART_TABLE_SCHEMAS:
        parquet_path = marts_dir / f"{table_name}.parquet"
        if not parquet_path.exists():
            print(f"      SKIP {table_name}: {parquet_path} not found.")
            load_results.append({"table": table_name, "status": "skipped_missing_file"})
            continue
        try:
            rows_loaded = client.load_parquet(table_name, parquet_path)
            print(f"      Loaded {table_name}: {rows_loaded:,} rows")
            load_results.append({"table": table_name, "status": "loaded", "rows": rows_loaded})
        except Exception as exc:
            print(f"      FAILED {table_name}: {exc}")
            load_results.append({"table": table_name, "status": "failed", "error": str(exc)})

    # ------------------------------------------------------------------
    # 7. Create analytical views
    # ------------------------------------------------------------------
    print("\n[5/6] Creating analytical views (sql/bigquery/views.sql)...")
    views_sql_path = REPO_ROOT / "sql" / "bigquery" / "views.sql"
    try:
        created_views = client.create_views_from_file(views_sql_path)
        print(f"      Created {len(created_views)} views: {', '.join(created_views)}")
    except Exception as exc:
        print(f"      FAILED to create views: {exc}")
        created_views = []

    # ------------------------------------------------------------------
    # 8. Run validation
    # ------------------------------------------------------------------
    print("\n[6/6] Running data validation (comparing BigQuery vs. local Parquet)...")
    try:
        validation_report = run_full_validation(client, settings.data_dir)
    except Exception as exc:
        _fail(f"Validation failed to execute: {exc}")
        return

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("MIGRATION SUMMARY")
    print("=" * 78)
    print(f"Project:  {project_id}")
    print(f"Dataset:  {dataset_id}")
    print(f"Tables created: {len(created_tables)}")
    print(f"Views created:  {len(created_views)}")
    print("\nLoad results:")
    for r in load_results:
        status = r["status"]
        if status == "loaded":
            print(f"  [OK]      {r['table']:<40} {r['rows']:,} rows")
        elif status == "skipped_missing_file":
            print(f"  [SKIPPED] {r['table']:<40} local Parquet file not found")
        else:
            print(f"  [FAILED]  {r['table']:<40} {r.get('error', 'unknown error')}")

    print("\nValidation results:")
    for check in validation_report["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"  [{status}] {check['check']}")

    overall = "PASSED" if validation_report["overall_passed"] else "FAILED"
    print(f"\nOverall validation: {overall}")
    print("=" * 78)

    if not validation_report["overall_passed"]:
        print(
            "\nOne or more validation checks failed. Review the details above "
            "before relying on this BigQuery dataset. The local application "
            "(API/frontend) is UNAFFECTED by this migration — it continues to "
            "read data/analytics_summary.json."
        )
        sys.exit(1)

    print(
        "\nMigration complete. NOTE: the running CloudSense AI API/frontend is "
        "UNCHANGED by this script — it continues to serve data from "
        "data/analytics_summary.json (CLOUDSENSE_DATA_BACKEND=local). Switching "
        "the live backend to BigQuery is out of scope for Phase 6."
    )


if __name__ == "__main__":
    main()
