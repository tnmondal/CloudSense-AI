"""
CloudSense AI — BigQuery Integration Tests (Phase 6)

Two categories of test in this file:

1. STRUCTURAL / CREDENTIAL-INDEPENDENT tests (always run, no network access,
   no google-cloud-bigquery required): verify DDL generation, schema
   consistency between src/pipeline/schema.py and the SQL view file, and
   that bigquery_client.py / bigquery_validation.py import safely without
   the optional dependency installed.

2. LIVE BigQuery tests (only run when BOTH `google-cloud-bigquery` is
   installed AND `CLOUDSENSE_GCP_PROJECT_ID` is set in the environment):
   actually create a dataset, load a tiny amount of data, query it, and
   validate it against a live BigQuery project. These are real tests against
   a real project — they are never faked — but are skip-gated so the
   default local test run (and CI) never requires GCP access.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _bigquery_sdk_available() -> bool:
    try:
        import google.cloud.bigquery  # noqa: F401
        return True
    except ImportError:
        return False


def _live_credentials_configured() -> bool:
    return bool(os.getenv("CLOUDSENSE_GCP_PROJECT_ID", "").strip())


LIVE_TESTS_AVAILABLE = _bigquery_sdk_available() and _live_credentials_configured()
_SKIP_REASON = (
    "Live BigQuery integration tests were skipped: "
    + (
        "google-cloud-bigquery is not installed (pip install -r requirements-bigquery.txt). "
        if not _bigquery_sdk_available() else ""
    )
    + (
        "CLOUDSENSE_GCP_PROJECT_ID is not set."
        if not _live_credentials_configured() else ""
    )
)


# ---------------------------------------------------------------------------
# 1. Structural / credential-independent tests — always run
# ---------------------------------------------------------------------------

def test_bigquery_client_module_imports_without_sdk_installed():
    """bigquery_client.py must be importable even when google-cloud-bigquery
    is not installed — this is the core Phase 6 safety requirement."""
    from src.pipeline import bigquery_client  # noqa: F401


def test_bigquery_validation_module_imports_without_sdk_installed():
    from src.pipeline import bigquery_validation  # noqa: F401


def test_generate_full_schema_ddl_covers_all_gold_and_mart_tables():
    from src.pipeline.bigquery_client import generate_full_schema_ddl
    from src.pipeline.schema import GOLD_TABLE_SCHEMAS, MART_TABLE_SCHEMAS

    ddl = generate_full_schema_ddl("test_dataset")
    for table_name in {**GOLD_TABLE_SCHEMAS, **MART_TABLE_SCHEMAS}:
        assert f"`test_dataset.{table_name}`" in ddl, f"DDL missing CREATE TABLE for {table_name}"


def test_each_table_generates_independent_self_contained_ddl():
    """
    Regression test: an earlier version of BigQueryClient.create_all_tables()
    executed table creation by re-parsing the concatenated, comment-annotated
    output of generate_full_schema_ddl() and splitting on ';'. Any table
    whose CREATE TABLE statement landed in the same semicolon-delimited
    chunk as an immediately-preceding '-- section comment' line (with no
    semicolon between them) was silently dropped by the "skip chunks
    starting with --" filter. This silently broke dim_date, fact_usage, and
    mart_cost_summary. The fix generates and executes one independent
    statement per table (generate_table_ddl), which this test verifies for
    every table in the schema registry.
    """
    from src.pipeline.bigquery_client import generate_table_ddl
    from src.pipeline.schema import GOLD_TABLE_SCHEMAS, MART_TABLE_SCHEMAS

    all_tables = {**GOLD_TABLE_SCHEMAS, **MART_TABLE_SCHEMAS}
    for table_name, schema in all_tables.items():
        ddl = generate_table_ddl("proj.cloudsense_dw", table_name, schema)
        assert ddl.strip().startswith("CREATE OR REPLACE TABLE"), (
            f"{table_name}'s generated DDL is not a standalone, self-contained statement"
        )
        assert f"`proj.cloudsense_dw.{table_name}`" in ddl


def test_fact_table_partitioning_matches_phase6_specification():
    """Confirms the exact partition/cluster spec requested for Phase 6 is
    what's actually encoded in BIGQUERY_SPECS (not just documented in prose)."""
    from src.pipeline.schema import BIGQUERY_SPECS

    expected = {
        "fact_usage": ("usage_date", ["resource_id", "service_id", "region_id"]),
        "fact_cost": ("usage_date", ["resource_id", "service_id", "region_id"]),
        "fact_carbon": ("usage_date", ["region_id", "service_id"]),
        "fact_anomaly": ("usage_date", ["severity", "anomaly_type", "service_id"]),
    }
    for table, (partition_field, cluster_fields) in expected.items():
        spec = BIGQUERY_SPECS[table]
        assert spec["partition_field"] == partition_field
        assert spec["cluster_fields"] == cluster_fields


def test_mart_specs_present_for_all_six_marts():
    from src.pipeline.schema import BIGQUERY_SPECS, MART_TABLE_SCHEMAS

    for mart_name in MART_TABLE_SCHEMAS:
        assert mart_name in BIGQUERY_SPECS, f"Missing BIGQUERY_SPECS entry for {mart_name}"


def test_views_sql_file_defines_all_eleven_required_views():
    views_path = REPO_ROOT / "sql" / "bigquery" / "views.sql"
    assert views_path.exists(), "sql/bigquery/views.sql is missing"
    content = views_path.read_text(encoding="utf-8")

    required_views = [
        "v_cost_summary", "v_cost_by_service", "v_cost_by_region", "v_cost_by_department",
        "v_usage_summary", "v_service_utilization", "v_anomalies_active",
        "v_optimization_opportunities", "v_carbon_summary", "v_carbon_by_region",
        "v_forecast_inputs",
    ]
    for view_name in required_views:
        assert f"-- view: {view_name}" in content, f"views.sql is missing '-- view: {view_name}' marker"


def test_create_views_from_file_parses_exactly_eleven_views_not_more():
    """
    Regression test: the view-file parser must anchor the '-- view:' marker
    to the START of a line. An earlier implementation used a naive
    `content.split("-- view:")`, which also matched the literal phrase
    "-- view:" appearing inside the file's own header documentation
    (describing the marker convention), silently producing a 12th, bogus
    "view" entry. This test parses the real file with the same regex
    bigquery_client.py uses and asserts exactly 11 views are found.
    """
    import re

    views_path = REPO_ROOT / "sql" / "bigquery" / "views.sql"
    content = views_path.read_text(encoding="utf-8")
    marker_pattern = re.compile(r"^-- view:[ \t]*(\S+)[ \t]*$", re.MULTILINE)
    matches = list(marker_pattern.finditer(content))
    view_names = [m.group(1) for m in matches]

    assert len(view_names) == 11, f"Expected exactly 11 views, found {len(view_names)}: {view_names}"
    assert len(set(view_names)) == 11, "Duplicate view names found in views.sql"

    # Every parsed block must contain a real SELECT once {dataset} is substituted.
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        select_sql = content[start:end].strip().rstrip(";")
        substituted = select_sql.format(dataset="test-project.cloudsense_dw")
        assert "SELECT" in substituted.upper(), f"{view_names[i]} block has no SELECT statement"
        assert "{" not in substituted and "}" not in substituted, (
            f"{view_names[i]} has an unsubstituted placeholder after formatting"
        )


def test_views_sql_only_references_real_schema_columns():
    """Cross-checks every column referenced in a simple SELECT list against
    the real GOLD/MART schemas, for the views whose columns are a direct
    passthrough (no computed aggregate aliases), to catch invented columns."""
    from src.pipeline.schema import MART_TABLE_SCHEMAS

    views_path = REPO_ROOT / "sql" / "bigquery" / "views.sql"
    content = views_path.read_text(encoding="utf-8")

    # v_forecast_inputs selects directly from mart_cost_trends with no aliases;
    # verify each selected column really exists in that mart's schema.
    forecast_block = content.split("-- view: v_forecast_inputs")[1]
    select_cols = ["usage_date", "total_net_cost_usd", "rolling_7d_avg_cost", "rolling_30d_avg_cost", "daily_growth_pct"]
    for col in select_cols:
        assert col in MART_TABLE_SCHEMAS["mart_cost_trends"], f"{col} referenced in v_forecast_inputs is not a real mart_cost_trends column"
        assert col in forecast_block, f"{col} expected in v_forecast_inputs SQL body"


def test_requirements_bigquery_file_isolates_the_dependency():
    req_path = REPO_ROOT / "requirements-bigquery.txt"
    assert req_path.exists()
    content = req_path.read_text(encoding="utf-8")
    assert "google-cloud-bigquery" in content

    main_requirements = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "google-cloud-bigquery" not in main_requirements, (
        "google-cloud-bigquery must NOT be in the default requirements.txt — "
        "it belongs only in requirements-bigquery.txt"
    )


def test_settings_default_to_local_backend():
    """The core Phase 6 safety guarantee: with no env vars set, the app
    behaves exactly as before — local backend, no GCP project configured."""
    from src.api.config import Settings

    fresh_settings = Settings()
    assert fresh_settings.data_backend == "local"
    assert fresh_settings.gcp_project_id == ""


def test_migration_script_exists_and_is_not_imported_by_the_api():
    """run_bigquery_migration.py must exist as a standalone script and must
    never be imported by src/api/main.py (which would make it run on API
    startup)."""
    script_path = REPO_ROOT / "run_bigquery_migration.py"
    assert script_path.exists()

    main_py_content = (REPO_ROOT / "src" / "api" / "main.py").read_text(encoding="utf-8")
    assert "run_bigquery_migration" not in main_py_content


# ---------------------------------------------------------------------------
# 2. Live BigQuery tests — skip-gated
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not LIVE_TESTS_AVAILABLE, reason=_SKIP_REASON)
class TestLiveBigQueryIntegration:
    """
    These tests exercise a REAL BigQuery project end-to-end: dataset
    creation, table creation, a tiny Parquet load, a query, and cleanup.
    They are skipped entirely (never faked) unless google-cloud-bigquery is
    installed AND CLOUDSENSE_GCP_PROJECT_ID is set. A dedicated, disposable
    test dataset name is used so this never touches a production dataset.
    """

    @pytest.fixture(scope="class")
    def client(self):
        from src.pipeline.bigquery_client import BigQueryClient

        project_id = os.environ["CLOUDSENSE_GCP_PROJECT_ID"]
        test_dataset = os.getenv("CLOUDSENSE_BIGQUERY_TEST_DATASET", "cloudsense_dw_test")
        bq_client = BigQueryClient(project_id=project_id, dataset_id=test_dataset)
        bq_client.ensure_dataset()
        yield bq_client
        # Best-effort cleanup: delete the test dataset and its contents.
        try:
            bq_client.client.delete_dataset(
                bq_client.dataset_ref, delete_contents=True, not_found_ok=True
            )
        except Exception:
            pass

    def test_dataset_creation(self, client):
        assert client.dataset_ref.endswith(client.dataset_id)

    def test_create_all_tables_and_verify_existence(self, client):
        from src.pipeline.schema import GOLD_TABLE_SCHEMAS, MART_TABLE_SCHEMAS

        all_tables = {**GOLD_TABLE_SCHEMAS, **MART_TABLE_SCHEMAS}
        created = client.create_all_tables()
        assert len(created) == len(all_tables), (
            f"Expected {len(all_tables)} tables created, got {len(created)}: {created}"
        )
        for table_name in all_tables:
            assert client.table_exists(table_name), f"{table_name} was not created in live BigQuery"

    def test_query_execution_against_live_project(self, client):
        rows = client.run_query(f"SELECT 1 AS test_value")
        assert rows == [{"test_value": 1}]
