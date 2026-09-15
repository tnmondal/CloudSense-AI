# CloudSense AI — Warehouse Integrity & Validation Audit
**Generated At**: 2026-09-03 11:09:17  
**Overall Status**: PASSED (100%)  
**Tests Passed**: 25 / 25  

---

## Validation Test Matrix

| Category | Test Name | Status | Details |
|---|---|---|---|
| Primary Key Integrity | `dim_date.date_key Uniqueness & Non-Null` | **PASS** | Total rows: 250, Unique PKs: 250, Nulls: 0 |
| Primary Key Integrity | `dim_provider.provider_id Uniqueness & Non-Null` | **PASS** | Total rows: 1, Unique PKs: 1, Nulls: 0 |
| Primary Key Integrity | `dim_region.region_id Uniqueness & Non-Null` | **PASS** | Total rows: 5, Unique PKs: 5, Nulls: 0 |
| Primary Key Integrity | `dim_service.service_id Uniqueness & Non-Null` | **PASS** | Total rows: 7, Unique PKs: 7, Nulls: 0 |
| Primary Key Integrity | `dim_resource.resource_id Uniqueness & Non-Null` | **PASS** | Total rows: 200, Unique PKs: 200, Nulls: 0 |
| Primary Key Integrity | `fact_usage.usage_fact_id Uniqueness & Non-Null` | **PASS** | Total rows: 50,000, Unique PKs: 50,000, Nulls: 0 |
| Primary Key Integrity | `fact_cost.cost_fact_id Uniqueness & Non-Null` | **PASS** | Total rows: 50,000, Unique PKs: 50,000, Nulls: 0 |
| Primary Key Integrity | `fact_carbon.carbon_fact_id Uniqueness & Non-Null` | **PASS** | Total rows: 50,000, Unique PKs: 50,000, Nulls: 0 |
| Primary Key Integrity | `fact_anomaly.anomaly_fact_id Uniqueness & Non-Null` | **PASS** | Total rows: 18, Unique PKs: 18, Nulls: 0 |
| Referential Integrity | `fact_usage Foreign Key Constraints` | **PASS** | Orphan FKs -> Resource: 0, Service: 0, Region: 0, Date: 0, Provider: 0 |
| Referential Integrity | `fact_cost Foreign Key Constraints` | **PASS** | Orphan FKs -> Resource: 0, Service: 0, Region: 0, Date: 0, Provider: 0 |
| Referential Integrity | `fact_carbon Foreign Key Constraints` | **PASS** | Orphan FKs -> Resource: 0, Service: 0, Region: 0, Date: 0, Provider: 0 |
| Missing Values | `dim_date Zero Null Constraints` | **PASS** | Total null cells: 0 |
| Missing Values | `dim_provider Zero Null Constraints` | **PASS** | Total null cells: 0 |
| Missing Values | `dim_region Zero Null Constraints` | **PASS** | Total null cells: 0 |
| Missing Values | `dim_service Zero Null Constraints` | **PASS** | Total null cells: 0 |
| Missing Values | `dim_resource Zero Null Constraints` | **PASS** | Total null cells: 0 |
| Missing Values | `fact_usage Zero Null Constraints` | **PASS** | Total null cells: 0 |
| Missing Values | `fact_cost Zero Null Constraints` | **PASS** | Total null cells: 0 |
| Missing Values | `fact_carbon Zero Null Constraints` | **PASS** | Total null cells: 0 |
| Missing Values | `fact_anomaly Zero Null Constraints` | **PASS** | Total null cells: 0 |
| Business Invariant | `fact_cost: Net = List - Discount` | **PASS** | Max deviation: 0.000000 |
| Physical Invariant | `fact_carbon: Total = Scope2 + Scope3` | **PASS** | Max deviation: 0.000000 |
| Physical Invariant | `fact_usage: 0 <= Avg_CPU <= Max_CPU <= 100` | **PASS** | Min Avg CPU: 0.0, Max Peak CPU: 100.0 |
| Reconciliation | `mart_cost_trends Net Cost == fact_cost Net Cost` | **PASS** | fact_cost Total: $726,397.32, mart_cost_trends Total: $726,397.32 |

---

## Warehouse Table Summary
| Table Name | Table Type | Record Count | Primary Key | Description |
|---|---|---|---|---|
| `dim_date` | **Dimension** | 250 | `date_key` | Conformed Date Dimension (250 days) |
| `dim_provider` | **Dimension** | 1 | `provider_id` | Cloud Service Provider (GCP) |
| `dim_region` | **Dimension** | 5 | `region_id` | 5 Global Data Center Regions & Grid Emissions |
| `dim_service` | **Dimension** | 7 | `service_id` | 7 Cloud Service Taxonomies & Pricing Models |
| `dim_resource` | **Dimension** | 200 | `resource_id` | 200 Persistent Cloud Assets across 8 Projects |
| `fact_usage` | **Fact** | 50,000 | `usage_fact_id` | Daily Usage & Monitoring Telemetry (Grain: Resource-Day) |
| `fact_cost` | **Fact** | 50,000 | `cost_fact_id` | Daily Financial Cost Line Items (Grain: Resource-Day) |
| `fact_carbon` | **Fact** | 50,000 | `carbon_fact_id` | Daily Energy & Scope 2/3 Emissions (Grain: Resource-Day) |
| `fact_anomaly` | **Fact** | 18 | `anomaly_fact_id` | Flagged Operational FinOps Incidents (18 Events) |

---

## Analytics Marts Summary
| Mart Name | Record Count | Aggregation Grain | Business Purpose |
|---|---|---|---|
| `mart_cost_summary` | 79 | Dept x Project x Service x Region | Executive spend breakdown & unit economics |
| `mart_cost_trends` | 250 | Daily Date (250 Days) | Time-series forecasting, 7d/30d moving averages |
| `mart_resource_utilization` | 170 | Resource (200 Assets) | Compute/RAM efficiency tiers & rightsizing targets |
| `mart_anomalies` | 5 | Incident Type x Severity | Operational incident triage & financial surge analysis |
| `mart_optimization_opportunities` | 49 | Resource x Optimization Category | Prioritized annual savings recommendations |
| `mart_carbon_emissions` | 5 | Region | Regional carbon intensity & Scope 2/3 breakdown |

---

## Audit Sign-Off
All dimensional foreign key relationships, physical utilization bounds, and financial cost equations reconcile with 100% precision. The warehouse layer is verified and ready for analytical query execution.
