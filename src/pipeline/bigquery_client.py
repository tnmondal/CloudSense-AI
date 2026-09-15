"""
CloudSense AI — BigQuery Adapter
Provides an additive, optional Google BigQuery client for creating the
cloud data warehouse, loading Gold/Mart Parquet data, creating analytical
views, and running validation/analytical queries.

IMPORTANT — this module is entirely additive:
- It is never imported by the running FastAPI application or AnalyticsService.
- It has no effect on local mode (CLOUDSENSE_DATA_BACKEND=local, the default).
- `google-cloud-bigquery` is an OPTIONAL dependency (see requirements-bigquery.txt).
  Importing this module never fails just because that package is missing —
  the import is deferred until a BigQueryClient is actually instantiated, so
  `pip install -r requirements.txt` (without the BigQuery extra) and the
  full local test suite are completely unaffected.

Authentication uses standard Google Application Default Credentials (ADC) —
either `GOOGLE_APPLICATION_CREDENTIALS` pointing at a service-account key
file, or `gcloud auth application-default login` for interactive use. No
credentials are ever hardcoded, generated, or read from this repository.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.pipeline.schema import (
    BIGQUERY_SPECS,
    GOLD_TABLE_SCHEMAS,
    MART_TABLE_SCHEMAS,
)

# Column types that map cleanly and unambiguously between the internal
# schema definitions (schema.py) and BigQuery Standard SQL types.
_TYPE_MAP = {
    "int64": "INT64",
    "float64": "FLOAT64",
    "string": "STRING",
    "bool": "BOOL",
}

# Tables whose primary date column should be physically typed as DATE in
# BigQuery (it is stored as a plain string in the local Parquet layer).
_DATE_COLUMNS_BY_TABLE = {
    "fact_usage": "usage_date",
    "fact_cost": "usage_date",
    "fact_carbon": "usage_date",
    "fact_anomaly": "usage_date",
    "mart_cost_trends": "usage_date",
}


class BigQueryDependencyError(RuntimeError):
    """Raised when BigQuery operations are attempted without the optional
    google-cloud-bigquery dependency installed."""


def _require_bigquery_sdk():
    """
    Imports google.cloud.bigquery lazily so this module can always be
    imported safely, even in environments that never installed
    requirements-bigquery.txt.
    """
    try:
        from google.cloud import bigquery  # noqa: F401
        return bigquery
    except ImportError as exc:
        raise BigQueryDependencyError(
            "google-cloud-bigquery is not installed. Install the optional "
            "BigQuery extra with:\n\n    pip install -r requirements-bigquery.txt\n\n"
            "This is only required for BigQuery migration/validation — the "
            "local application (API, frontend, tests) does not need it."
        ) from exc


def _column_ddl(schema: Dict[str, str], table_name: str) -> List[str]:
    """Builds `column_name TYPE` fragments for a CREATE TABLE statement."""
    date_col = _DATE_COLUMNS_BY_TABLE.get(table_name)
    lines = []
    for col, dtype in schema.items():
        bq_type = "DATE" if col == date_col else _TYPE_MAP[dtype]
        lines.append(f"  {col} {bq_type}")
    return lines


def generate_table_ddl(dataset_id: str, table_name: str, schema: Dict[str, str]) -> str:
    """
    Generates a single `CREATE OR REPLACE TABLE` statement for one Gold or
    Mart table, applying the partitioning/clustering spec from
    BIGQUERY_SPECS when one exists for that table.
    """
    columns_sql = ",\n".join(_column_ddl(schema, table_name))
    spec = BIGQUERY_SPECS.get(table_name, {})
    partition_field = spec.get("partition_field")
    cluster_fields = spec.get("cluster_fields")

    ddl = f"CREATE OR REPLACE TABLE `{dataset_id}.{table_name}` (\n{columns_sql}\n)"
    if partition_field:
        ddl += f"\nPARTITION BY {partition_field}"
    if cluster_fields:
        ddl += f"\nCLUSTER BY {', '.join(cluster_fields)}"
    ddl += f"\nOPTIONS(description=\"CloudSense AI — {table_name}\");"
    return ddl


def generate_full_schema_ddl(dataset_id: str = "cloudsense_dw") -> str:
    """
    Generates DDL for the dataset plus every Gold dimension/fact table and
    every Analytics Mart table, driven entirely by the schema definitions in
    src/pipeline/schema.py (GOLD_TABLE_SCHEMAS, MART_TABLE_SCHEMAS,
    BIGQUERY_SPECS) — there is no separate, competing schema definition here.
    """
    statements = [
        f'-- ============================================================================\n'
        f'-- CloudSense AI: Google BigQuery Schema DDL (generated from src/pipeline/schema.py)\n'
        f'-- Dataset: {dataset_id}\n'
        f'-- ============================================================================\n',
        f'CREATE SCHEMA IF NOT EXISTS `{dataset_id}`\n'
        f'OPTIONS(\n'
        f'  description="CloudSense AI Enterprise FinOps & GreenOps Data Warehouse",\n'
        f'  location="US"\n'
        f');\n',
        "-- ----------------------------------------------------------------------------\n"
        "-- DIMENSION TABLES\n"
        "-- ----------------------------------------------------------------------------\n",
    ]
    for table_name, schema in GOLD_TABLE_SCHEMAS.items():
        if table_name.startswith("dim_"):
            statements.append(generate_table_ddl(dataset_id, table_name, schema))

    statements.append(
        "\n-- ----------------------------------------------------------------------------\n"
        "-- FACT TABLES (Partitioned & Clustered)\n"
        "-- ----------------------------------------------------------------------------\n"
    )
    for table_name, schema in GOLD_TABLE_SCHEMAS.items():
        if table_name.startswith("fact_"):
            statements.append(generate_table_ddl(dataset_id, table_name, schema))

    statements.append(
        "\n-- ----------------------------------------------------------------------------\n"
        "-- ANALYTICS MART TABLES (Pre-Aggregated Presentation Layer)\n"
        "-- ----------------------------------------------------------------------------\n"
    )
    for table_name, schema in MART_TABLE_SCHEMAS.items():
        statements.append(generate_table_ddl(dataset_id, table_name, schema))

    return "\n\n".join(statements)


class BigQueryClient:
    """
    Thin, focused wrapper around google-cloud-bigquery for the operations
    the Phase 6 migration needs: dataset/table creation, Parquet loading,
    view creation, validation, and ad-hoc querying.

    This class is never instantiated by the running API — it is only used by
    `run_bigquery_migration.py` and `src/pipeline/bigquery_validation.py`,
    both of which are run manually and separately from the application.
    """

    def __init__(self, project_id: str, dataset_id: str, location: str = "US"):
        if not project_id:
            raise ValueError("A GCP project_id is required to use BigQueryClient.")
        if not dataset_id:
            raise ValueError("A BigQuery dataset_id is required to use BigQueryClient.")

        bigquery = _require_bigquery_sdk()
        self._bigquery = bigquery
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.location = location
        self.dataset_ref = f"{project_id}.{dataset_id}"

        # Uses Application Default Credentials — no key material is read
        # from or written to this repository.
        self.client = bigquery.Client(project=project_id)

    # -------------------------------------------------------------------
    # Dataset & Table Management
    # -------------------------------------------------------------------
    def ensure_dataset(self) -> None:
        """Creates the BigQuery dataset if it does not already exist."""
        bigquery = self._bigquery
        dataset = bigquery.Dataset(self.dataset_ref)
        dataset.location = self.location
        dataset.description = "CloudSense AI Enterprise FinOps & GreenOps Data Warehouse"
        self.client.create_dataset(dataset, exists_ok=True)

    def create_all_tables(self) -> List[str]:
        """
        Creates (or replaces) every Gold and Mart table using DDL generated
        from src/pipeline/schema.py. Returns the list of table names created.

        Each table's DDL is generated and executed individually (via
        generate_table_ddl()) rather than by re-parsing the concatenated,
        comment-annotated output of generate_full_schema_ddl() and splitting
        on ";" — an earlier version of this method did that, and a
        semicolon-split chunk that happened to start with a "-- section
        comment" line immediately followed by a real CREATE TABLE statement
        (with no semicolon between them) was silently discarded by the
        "skip chunks starting with --" filter, dropping real tables
        (dim_date, fact_usage, and mart_cost_summary were lost this way).
        Executing one well-formed statement per table sidesteps that class
        of bug entirely.
        """
        created: List[str] = []
        for table_name, schema in {**GOLD_TABLE_SCHEMAS, **MART_TABLE_SCHEMAS}.items():
            ddl = generate_table_ddl(self.dataset_ref, table_name, schema)
            self.client.query(ddl).result()
            created.append(table_name)
        return created

    # -------------------------------------------------------------------
    # Data Loading
    # -------------------------------------------------------------------
    def load_parquet(self, table_name: str, parquet_path: Path) -> int:
        """
        Loads a single Parquet file into an existing BigQuery table,
        truncating and replacing its contents. Returns the number of rows loaded.
        """
        bigquery = self._bigquery
        parquet_path = Path(parquet_path)
        if not parquet_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

        table_ref = f"{self.dataset_ref}.{table_name}"
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.PARQUET,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        with open(parquet_path, "rb") as source_file:
            load_job = self.client.load_table_from_file(
                source_file, table_ref, job_config=job_config
            )
        load_job.result()  # Waits for the job to complete, raises on failure.
        table = self.client.get_table(table_ref)
        return table.num_rows

    # -------------------------------------------------------------------
    # Views
    # -------------------------------------------------------------------
    def create_view(self, view_name: str, select_sql: str) -> None:
        """Creates or replaces a single BigQuery view from a SELECT statement."""
        ddl = f"CREATE OR REPLACE VIEW `{self.dataset_ref}.{view_name}` AS\n{select_sql}"
        self.client.query(ddl).result()

    def create_views_from_file(self, sql_file_path: Path) -> List[str]:
        """
        Parses `sql/bigquery/views.sql` (statements separated by a
        `-- view: <name>` marker at the START OF A LINE) and creates each
        view in turn. Returns the list of view names created.

        Only markers anchored at the beginning of a line are treated as
        real view boundaries — this deliberately avoids false-positive
        splits if the literal phrase "-- view:" ever appears elsewhere,
        e.g. inside a header comment describing this convention.
        """
        import re

        sql_file_path = Path(sql_file_path)
        content = sql_file_path.read_text(encoding="utf-8")

        marker_pattern = re.compile(r"^-- view:[ \t]*(\S+)[ \t]*$", re.MULTILINE)
        matches = list(marker_pattern.finditer(content))

        created = []
        for i, match in enumerate(matches):
            view_name = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            select_sql = content[start:end].strip().rstrip(";")
            select_sql = select_sql.format(dataset=self.dataset_ref)
            self.create_view(view_name, select_sql)
            created.append(view_name)
        return created

    # -------------------------------------------------------------------
    # Querying & Introspection
    # -------------------------------------------------------------------
    def run_query(self, sql: str) -> List[Dict[str, Any]]:
        """Executes a SQL query and returns rows as a list of dicts."""
        result = self.client.query(sql).result()
        return [dict(row.items()) for row in result]

    def table_exists(self, table_name: str) -> bool:
        try:
            self.client.get_table(f"{self.dataset_ref}.{table_name}")
            return True
        except Exception:
            return False

    def get_row_count(self, table_name: str) -> int:
        table = self.client.get_table(f"{self.dataset_ref}.{table_name}")
        return table.num_rows

    def get_schema_fields(self, table_name: str) -> List[str]:
        table = self.client.get_table(f"{self.dataset_ref}.{table_name}")
        return [field.name for field in table.schema]
