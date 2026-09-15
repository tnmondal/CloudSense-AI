# BigQuery Data Warehouse Migration (Phase 6)

This document describes the **additive** BigQuery data warehouse built in
Phase 6. It complements `docs/data_warehouse_and_marts.md` (the local
DuckDB/Parquet warehouse) rather than replacing it — both exist side by
side, and **the running application still uses the local warehouse only.**

> **Synthetic data disclaimer.** Every dollar figure and carbon figure in
> this warehouse originates from CloudSense AI's synthetic, configurable
> data generator (`src/generator/config.py`). Pricing is a synthetic rate
> card, not real Google Cloud list pricing. Carbon figures are modeled
> estimates (PUE + regional grid-intensity assumptions), not official
> Google Cloud Carbon Footprint measurements. This is true whether the data
> is queried locally via DuckDB or from BigQuery — migrating storage engines
> does not change the nature of the underlying numbers.

## 1. Architecture

```
Local Gold/Marts Parquet (data/gold/, data/marts/)
        │
        │  run_bigquery_migration.py  (manual, operator-run only)
        ▼
BigQueryClient (src/pipeline/bigquery_client.py)
        │
        ▼
BigQuery dataset (default: cloudsense_dw)
  ├── 5 dimension tables
  ├── 4 fact tables (partitioned + clustered)
  ├── 6 analytics mart tables
  └── 11 analytical views (sql/bigquery/views.sql)
```

**Critical architectural point:** `AnalyticsService`
(`src/api/services/analytics_service.py`) is **not modified** in this phase
and continues to read `data/analytics_summary.json` exclusively, regardless
of whether a BigQuery warehouse exists or how it's configured. The new
`CLOUDSENSE_DATA_BACKEND` setting is present in `src/api/config.py` for a
**future** phase to consume — it has zero effect on current behavior.

## 2. Dataset Structure

| Layer | Tables | Source |
|---|---|---|
| Dimensions | `dim_date`, `dim_provider`, `dim_region`, `dim_service`, `dim_resource` | `data/gold/*.parquet` |
| Facts | `fact_usage`, `fact_cost`, `fact_carbon`, `fact_anomaly` | `data/gold/*.parquet` |
| Marts | `mart_cost_summary`, `mart_cost_trends`, `mart_resource_utilization`, `mart_anomalies`, `mart_optimization_opportunities`, `mart_carbon_emissions` | `data/marts/*.parquet` |
| Views | 11 views mirroring the API's analytical groupings | `sql/bigquery/views.sql` |

All table schemas are defined once, in `src/pipeline/schema.py`
(`GOLD_TABLE_SCHEMAS`, `MART_TABLE_SCHEMAS`) — this is the single source of
truth for both the local Parquet layer and the BigQuery DDL. No column was
invented for BigQuery that doesn't already exist in the local warehouse.

## 3. Table Descriptions

- **`dim_date`** — calendar attributes (year, quarter, month, day-of-week, weekend flag) for the dataset's 250-day span.
- **`dim_provider`**, **`dim_region`**, **`dim_service`** — small reference dimensions (provider, 5 GCP regions, service catalog).
- **`dim_resource`** — the 200 synthetic cloud resources, with department/environment/project attribution and provisioned sizing.
- **`fact_usage`** — daily utilization telemetry per resource (CPU/RAM %, IOPS, network, requests, idle flag).
- **`fact_cost`** — daily list/discount/net cost per resource.
- **`fact_carbon`** — daily energy consumption and Scope 2/3 carbon estimate per resource.
- **`fact_anomaly`** — detected statistical cost anomalies (Z-score/MAD/IQR consensus).
- **Marts** — pre-aggregated, presentation-ready rollups matching what `run_analytics.py` also independently derives into `analytics_summary.json` (see `docs/data_warehouse_and_marts.md` for the medallion pipeline that produces these).

## 4. Partitioning & Clustering

| Table | Partition | Cluster | Rationale |
|---|---|---|---|
| `fact_usage` | `usage_date` (DAY) | `resource_id, service_id, region_id` | Daily telemetry; most queries filter by date range and slice by resource/service/region. |
| `fact_cost` | `usage_date` (DAY) | `resource_id, service_id, region_id` | Same access pattern as usage; this is the highest-traffic fact table. |
| `fact_carbon` | `usage_date` (DAY) | `region_id, service_id` | Carbon analysis is typically sliced by region (grid intensity) before service. |
| `fact_anomaly` | `usage_date` (DAY) | `severity, anomaly_type, service_id` | Anomaly triage filters by severity/type first. |
| `mart_cost_trends` | `usage_date` (DAY) | — | The only mart that is daily-grained (one row per day); partitioned like the facts. |
| `mart_cost_summary` | none | `department, service_family` | Pre-aggregated by org dimension, not by date; too small to benefit from date partitioning. |
| `mart_resource_utilization` | none | `department, environment` | Per-resource rollup, not date-grained. |
| `mart_anomalies` | none | `severity, anomaly_type` | Small, pre-aggregated by incident category. |
| `mart_optimization_opportunities` | none | `optimization_category, department` | Small, pre-aggregated by recommendation type. |
| `mart_carbon_emissions` | none | `region_id` | Small, one row per region. |
| Dimensions | none | none | Deliberately **not** partitioned/clustered — these are small reference tables (a handful to a few hundred rows); partitioning/clustering would add metadata overhead with no pruning benefit. |

These decisions are encoded in `src/pipeline/schema.py::BIGQUERY_SPECS` and
consumed programmatically by `bigquery_client.py::generate_full_schema_ddl()`
— the table above is a human-readable description of that same source of
truth, not a separate, potentially-drifting specification.

## 5. Authentication

BigQuery access uses standard **Google Application Default Credentials
(ADC)** — no credentials are ever hardcoded, generated, or stored in this
repository.

Two supported ways to authenticate locally:

```bash
# Option A — interactive user credentials (simplest for local development)
gcloud auth application-default login

# Option B — service-account key file (kept OUTSIDE this repository)
export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/outside/this/repo/key.json
```

`.gitignore` at the repository root excludes `*.env`, `*service-account*.json`,
`*credentials*.json`, `*.pem`, and `*.key` patterns so a credential file
placed anywhere in the repo by mistake is never committed.

## 6. Required Google Cloud Configuration

| Environment variable | Required for migration? | Default | Purpose |
|---|---|---|---|
| `CLOUDSENSE_GCP_PROJECT_ID` | **Yes** | _(empty)_ | Target GCP project. `run_bigquery_migration.py` refuses to run without it. |
| `CLOUDSENSE_BIGQUERY_DATASET` | No | `cloudsense_dw` | Target BigQuery dataset name. |
| `CLOUDSENSE_DATA_BACKEND` | No | `local` | Reserved for a future phase; has no effect today. |
| `GOOGLE_APPLICATION_CREDENTIALS` | No (if using `gcloud auth application-default login`) | _(unset)_ | Path to a service-account key file, if not using interactive ADC login. |

The GCP project also needs the **BigQuery API enabled** and the
authenticated principal needs `roles/bigquery.dataEditor` (or broader) on
the target project/dataset.

## 7. Installing BigQuery Dependencies

```bash
pip install -r requirements.txt          # unchanged, no BigQuery dependency
pip install -r requirements-bigquery.txt  # adds google-cloud-bigquery only
```

The default `requirements.txt` install (used by the API, frontend, and the
main test suite) is completely unaffected — `google-cloud-bigquery` is only
required for the migration script, `bigquery_validation.py`, and the live
tests in `tests/test_bigquery_integration.py`.

## 8. Dataset Creation & Migration Command

```bash
export CLOUDSENSE_GCP_PROJECT_ID=your-gcp-project-id
export CLOUDSENSE_BIGQUERY_DATASET=cloudsense_dw   # optional, this is the default

python3 run_bigquery_migration.py
```

This single command performs, in order: config validation → dataset
creation → table creation (all 15 Gold+Mart tables) → Gold Parquet load →
Mart Parquet load → view creation (all 11 views) → full validation → a
printed summary. It is a **manual, operator-run script** — it is never
invoked by the API, the frontend, or the test suite.

## 9. Validation Command

Validation runs automatically as the final step of the migration script
above. To re-run validation independently against an already-migrated
dataset:

```bash
python3 -c "
from src.pipeline.bigquery_client import BigQueryClient
from src.pipeline.bigquery_validation import run_full_validation
from src.api.config import settings

client = BigQueryClient(project_id=settings.gcp_project_id, dataset_id=settings.bigquery_dataset)
report = run_full_validation(client, settings.data_dir)
import json; print(json.dumps(report, indent=2, default=str))
"
```

Validation checks performed (`src/pipeline/bigquery_validation.py`,
mirrored in `sql/bigquery/validation_queries.sql` for manual inspection):

- Table existence for all 9 Gold tables and 6 Mart tables
- **Row-count comparison between BigQuery and the local Gold/Mart Parquet files** (not just "the query ran")
- Schema completeness (every expected column present)
- Null constraints on key columns (`resource_id`, `usage_date`, etc.)
- Duplicate business-key detection (`resource_id` + `usage_date` in `fact_cost`)
- Non-negative cost validity
- Pricing consistency (`net = list − discount`, within floating-point tolerance)
- Referential integrity (every fact row's foreign keys resolve in the dimension tables)
- Date range sanity
- Anomaly ground-truth consistency between `fact_anomaly` and `mart_anomalies`

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `BigQueryDependencyError: google-cloud-bigquery is not installed` | Optional dependency not installed | `pip install -r requirements-bigquery.txt` |
| `CLOUDSENSE_GCP_PROJECT_ID is not set` | Migration script run without configuration | `export CLOUDSENSE_GCP_PROJECT_ID=...` |
| `403 Forbidden` / permission denied from BigQuery | ADC not authenticated, or principal lacks BigQuery permissions | Run `gcloud auth application-default login`; verify IAM role `roles/bigquery.dataEditor` or higher |
| `Expected Gold/Marts Parquet directories not found` | Local pipeline hasn't been run yet | `python3 run_pipeline.py` first |
| Validation reports `match: false` for row counts | Partial/failed load, or local data changed since last migration | Re-run `run_bigquery_migration.py` (it uses `WRITE_TRUNCATE`, so re-running is always safe and idempotent) |
| `404 Not Found` when creating views | Tables not created/loaded yet | Run the full migration script in order; don't call `create_views_from_file()` standalone before `create_all_tables()` |

## 11. Returning to Local Mode

**There is nothing to "return" from** — the running CloudSense AI
application never left local mode. `AnalyticsService` reads
`data/analytics_summary.json` unconditionally in this phase, and
`CLOUDSENSE_DATA_BACKEND` defaults to `"local"` and has no code path that
changes that behavior yet. Running `run_bigquery_migration.py` populates a
BigQuery project for validation/demonstration purposes only; it does not
modify `data/analytics_summary.json`, the local DuckDB warehouse, or any
file the API actually reads. You can run the migration script, inspect the
resulting BigQuery dataset in the console, and the local application's
behavior is completely unaffected before, during, and after.

If you want to remove a migrated BigQuery dataset:

```bash
bq rm -r -d your-project-id:cloudsense_dw
```

## 12. What This Phase Does NOT Do

- Does not change any FastAPI route, response schema, or the frontend.
- Does not switch `AnalyticsService` to read from BigQuery.
- Does not deploy anything to Cloud Run or any other compute service.
- Does not run automatically — every BigQuery operation is manually
  initiated via `run_bigquery_migration.py` or direct Python calls.
