# CloudSense AI — 50,000-Row Benchmark Dataset

This directory houses the foundational synthetic benchmark dataset for the **CloudSense AI** intelligence platform.

## Overview
- **File**: `cloudsense_50k.csv`
- **Total Records**: Exactly **50,000** rows
- **Columns**: **43** typed columns
- **Time Horizon**: **250 Days** (2025-09-01 to 2026-05-08)
- **Resource Inventory**: **200 distinct cloud assets** tracked continuously
- **Cloud Provider**: Google Cloud Platform (GCP)
- **Random Seed**: `42` (Bitwise reproducible across environments)

---

## Schema & Column Definitions

| Column Name | Data Type | Physical Unit | Description |
|---|---|---|---|
| `record_id` | String | Unique ID | Primary key formatted as `rec_YYYYMMDD_XXXXX` |
| `usage_date` | String | YYYY-MM-DD | Daily observation date |
| `cloud_provider` | String | Categorical | Cloud provider (`GCP`) |
| `project_id` | String | Categorical | GCP Project identifier |
| `project_name` | String | Text | Project display name |
| `department` | String | Categorical | Business unit (`Engineering`, `Data & AI`, `Operations`, etc.) |
| `cost_center` | String | Code | Accounting cost center (`CC-1001` through `CC-5005`) |
| `environment` | String | Categorical | Tier (`production`, `staging`, `development`, `sandbox`) |
| `service_id` | String | Categorical | Unique service key (`compute-engine-vm`, `bigquery`, etc.) |
| `service_name` | String | Text | Service display name |
| `service_family` | String | Categorical | Family (`Compute`, `Containers`, `Storage`, `Serverless`, `Analytics`, `Database`, `Networking`) |
| `resource_id` | String | Unique ID | Persistent resource identifier |
| `resource_name` | String | Text | Descriptive resource name |
| `resource_type` | String | Categorical | Machine type / SKU (`c2-standard-16`, `n2-standard-4`, `db-custom-8-32`, etc.) |
| `region_id` | String | Categorical | GCP Region (`us-central1`, `europe-west6`, `asia-south1`, etc.) |
| `region_name` | String | Text | Geographic region name |
| `pricing_tier` | String | Categorical | Contract plan (`On-Demand`, `Commitment-1Yr`, `Commitment-3Yr`, `Spot`) |
| `pricing_unit` | String | Categorical | Rate unit (`hour`, `gib-month`, `request-million`, `tb-scanned`, `gib-transfer`) |
| `usage_quantity` | Float | Unit-specific | Metric volume consumed |
| `list_unit_price_usd` | Float | USD / unit | Standard catalog price per unit |
| `list_cost_usd` | Float | USD | Undiscounted gross spend |
| `discount_amount_usd`| Float | USD | Realized contract / commitment savings |
| `net_cost_usd` | Float | USD | Final invoice net spend ($List - Discount$) |
| `runtime_hours` | Float | Hours | Operational uptime in day (typically 24.0) |
| `provisioned_vcpu` | Float | Cores | Assigned CPU core count |
| `provisioned_memory_gb` | Float | GiB | Assigned memory capacity |
| `provisioned_storage_gb`| Float | GiB | Attached disk / dataset volume |
| `avg_cpu_utilization_pct` | Float | Percentage | 24-hour mean CPU load ($0.0 - 100.0$) |
| `max_cpu_utilization_pct` | Float | Percentage | Peak observed CPU load ($0.0 - 100.0$) |
| `avg_memory_utilization_pct` | Float | Percentage | 24-hour mean RAM load ($0.0 - 100.0$) |
| `max_memory_utilization_pct` | Float | Percentage | Peak observed RAM load ($0.0 - 100.0$) |
| `disk_read_iops` | Float | Ops/sec | Average disk read IOPS |
| `disk_write_iops` | Float | Ops/sec | Average disk write IOPS |
| `network_ingress_gb` | Float | GiB | Inbound network traffic |
| `network_egress_gb` | Float | GiB | Outbound network traffic |
| `total_requests` | Integer | Count | Total transactions / HTTP invocations |
| `is_idle` | Boolean | True/False | Deterministic idle flag (CPU < 3%, RAM < 8%, IOPS ~ 0) |
| `pue_factor` | Float | Ratio | Data center Power Usage Effectiveness ($1.08 - 1.15$) |
| `grid_carbon_intensity_gco2_per_kwh` | Float | gCO2e / kWh | Regional grid carbon factor ($15.3 - 712.0$) |
| `server_power_avg_watts` | Float | Watts | SPECpower computed server electrical draw |
| `energy_consumed_kwh` | Float | kWh | Total facility energy consumed including PUE |
| `scope2_location_based_gco2e` | Float | gCO2e | Scope 2 operational greenhouse gas emissions |
| `scope3_embodied_gco2e` | Float | gCO2e | Scope 3 amortized hardware manufacturing emissions |
| `total_carbon_gco2e` | Float | gCO2e | Total greenhouse gas footprint ($Scope 2 + Scope 3$) |
| `anomaly_flag` | Boolean | True/False | Flag for injected real-world incidents |
| `anomaly_type` | String | Categorical | Incident classification (`runaway_dev_cluster`, `unpartitioned_bigquery_scan`, etc.) |
| `optimization_category` | String | Categorical | Actionable category (`idle_zombie`, `compute_rightsizing`, `storage_lifecycle`, `green_migration`) |

---

## How to Regenerate
To reproduce the dataset with the exact same bitwise values:
```bash
python data/generate_dataset.py
```
