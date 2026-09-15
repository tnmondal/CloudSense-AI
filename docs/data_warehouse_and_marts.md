# CloudSense AI — Data Warehouse Architecture & Analytics Marts Specification
**Architecture Version**: 1.0.0  
**Warehouse Engine**: Local DuckDB (Parquet Storage) $\to$ Production Google BigQuery  
**Pipeline Pattern**: Medallion Architecture (Bronze $\to$ Silver $\to$ Gold $\to$ Marts)  
**Status**: Formal Source of Truth  

---

## 1. Executive Overview

This document defines the physical and logical data warehouse architecture for the **CloudSense AI** platform. It provides the implementation blueprint for data lineage, dimensional modeling, automated validation rules, presentation marts, and the future cloud migration strategy to Google BigQuery.

---

## 2. Medallion Architecture

```mermaid
flowchart TD
    subgraph SOURCELAYER["Source Ingestion"]
        RAW["Raw Source Data<br/>(cloudsense_50k.csv)"]
    end

    subgraph BRONZELAYER["Bronze Layer: Raw Ingestion Store"]
        BRONZE["bronze_cloud_usage.parquet<br/>• Immutable record storage<br/>• Ingestion metadata (_ingested_at, _batch_id, _record_hash)"]
    end

    subgraph SILVERLAYER["Silver Layer: Normalized & Enriched"]
        SILVER["silver_cloud_usage.parquet<br/>• Deduplicated by (usage_date, resource_id)<br/>• Enforced physical bounds (0 <= CPU/RAM <= 100)<br/>• Enforced cost math (Net = List - Discount)<br/>• Enforced carbon math (Total = Scope 2 + Scope 3)<br/>• Derived features (cost_per_vcpu_hour, emissions_per_dollar)"]
    end

    subgraph GOLDLAYER["Gold Layer: Conformed Dimensional Star Schema"]
        D_DATE["dim_date (250 rows)"]
        D_PROV["dim_provider (1 row)"]
        D_REG["dim_region (5 rows)"]
        D_SERV["dim_service (7 rows)"]
        D_RES["dim_resource (200 rows)"]
        
        F_USG["fact_usage (50,000 rows)"]
        F_CST["fact_cost (50,000 rows)"]
        F_CRB["fact_carbon (50,000 rows)"]
        F_ANM["fact_anomaly (18 rows)"]
    end

    subgraph MARTSLAYER["Analytics Marts: Pre-Aggregated Presentation Cubes"]
        M_CST["mart_cost_summary<br/>(Dept x Project x Service x Region)"]
        M_TRD["mart_cost_trends<br/>(Daily spend, 7d/30d moving averages)"]
        M_UTL["mart_resource_utilization<br/>(Compute & memory efficiency tiers)"]
        M_ANM["mart_anomalies<br/>(Operational incident financial impact)"]
        M_OPT["mart_optimization_opportunities<br/>(Rightsizing & zombie savings)"]
        M_CRB["mart_carbon_emissions<br/>(Regional carbon & Scope 2/3 breakdown)"]
    end

    RAW --> BRONZE
    BRONZE --> SILVER
    SILVER --> D_DATE & D_PROV & D_REG & D_SERV & D_RES
    SILVER --> F_USG & F_CST & F_CRB & F_ANM
    F_USG & F_CST & F_CRB & F_ANM --> M_CST & M_TRD & M_UTL & M_ANM & M_OPT & M_CRB
```

---

## 3. Dimensional Star Schema & Table Definitions

### Entity-Relationship Diagram

```mermaid
erDiagram
    dim_date ||--o{ fact_usage : "date_key"
    dim_date ||--o{ fact_cost : "date_key"
    dim_date ||--o{ fact_carbon : "date_key"
    dim_date ||--o{ fact_anomaly : "date_key"

    dim_provider ||--o{ fact_usage : "provider_id"
    dim_provider ||--o{ fact_cost : "provider_id"
    dim_provider ||--o{ fact_carbon : "provider_id"
    dim_provider ||--o{ fact_anomaly : "provider_id"

    dim_region ||--o{ fact_usage : "region_id"
    dim_region ||--o{ fact_cost : "region_id"
    dim_region ||--o{ fact_carbon : "region_id"
    dim_region ||--o{ fact_anomaly : "region_id"

    dim_service ||--o{ fact_usage : "service_id"
    dim_service ||--o{ fact_cost : "service_id"
    dim_service ||--o{ fact_carbon : "service_id"
    dim_service ||--o{ fact_anomaly : "service_id"

    dim_resource ||--o{ fact_usage : "resource_id"
    dim_resource ||--o{ fact_cost : "resource_id"
    dim_resource ||--o{ fact_carbon : "resource_id"
    dim_resource ||--o{ fact_anomaly : "resource_id"

    dim_date {
        int date_key PK
        string full_date
        int year
        int quarter
        int month
        string month_name
        int week_of_year
        int day_of_week
        string day_name
        bool is_weekend
        bool is_month_end
    }

    dim_provider {
        string provider_id PK
        string provider_name
        string cloud_category
        string headquarters
    }

    dim_region {
        string region_id PK
        string region_name
        string country
        string continent
        float pue_factor
        float grid_carbon_intensity_gco2_per_kwh
        string renewable_tier
    }

    dim_service {
        string service_id PK
        string service_name
        string service_family
        string pricing_unit
        string pricing_model
    }

    dim_resource {
        string resource_id PK
        string resource_name
        string resource_type
        string project_id
        string project_name
        string department
        string cost_center
        string environment
        string service_id FK
        string region_id FK
        string pricing_tier
        float provisioned_vcpu
        float provisioned_memory_gb
        float provisioned_storage_gb
    }

    fact_usage {
        string usage_fact_id PK
        int date_key FK
        string usage_date
        string resource_id FK
        string service_id FK
        string region_id FK
        string provider_id FK
        float runtime_hours
        float usage_quantity
        float avg_cpu_utilization_pct
        float max_cpu_utilization_pct
        float avg_memory_utilization_pct
        float max_memory_utilization_pct
        float disk_read_iops
        float disk_write_iops
        float network_ingress_gb
        float network_egress_gb
        int total_requests
        bool is_idle
    }

    fact_cost {
        string cost_fact_id PK
        int date_key FK
        string usage_date
        string resource_id FK
        string service_id FK
        string region_id FK
        string provider_id FK
        string pricing_tier
        float usage_quantity
        float list_unit_price_usd
        float list_cost_usd
        float discount_amount_usd
        float net_cost_usd
        float effective_hourly_rate
    }

    fact_carbon {
        string carbon_fact_id PK
        int date_key FK
        string usage_date
        string resource_id FK
        string service_id FK
        string region_id FK
        string provider_id FK
        float runtime_hours
        float server_power_avg_watts
        float energy_consumed_kwh
        float scope2_location_based_gco2e
        float scope3_embodied_gco2e
        float total_carbon_gco2e
        float emissions_per_dollar_usd
    }

    fact_anomaly {
        string anomaly_fact_id PK
        int date_key FK
        string usage_date
        string resource_id FK
        string service_id FK
        string region_id FK
        string provider_id FK
        string anomaly_type
        float actual_cost_usd
        float expected_cost_usd
        float deviation_usd
        float deviation_pct
        string severity
        string root_cause_description
    }
```

---

## 4. Analytics Marts Specifications

| Mart Name | Storage File | Granularity | Key Aggregations & Metrics | Primary Use Case |
|---|---|---|---|---|
| `mart_cost_summary` | `mart_cost_summary.parquet` | Dept $\times$ Project $\times$ Service $\times$ Region | Total List Cost, Discounts, Net Cost, Daily Average, Active Resource Count | Executive KPI widgets, multi-dimensional slice-and-dice |
| `mart_cost_trends` | `mart_cost_trends.parquet` | Daily Date (250 Days) | Daily Net Spend, 7-Day Moving Avg, 30-Day Moving Avg, WoW Growth % | Time-series forecasting baseline, budget burn-rate tracking |
| `mart_resource_utilization` | `mart_resource_utilization.parquet` | Cloud Resource (200 Assets) | Mean CPU %, P95 Peak CPU %, Mean RAM %, P95 Peak RAM %, Idle Days Count, Classification Tier | Rightsizing engine, zombie identification |
| `mart_anomalies` | `mart_anomalies.parquet` | Incident Type $\times$ Severity | Incident Days Count, Affected Assets, Actual Spend, Expected Spend, Dollar Surge | Anomaly timeline, incident RCA drawer |
| `mart_optimization_opportunities` | `mart_optimization_opportunities.parquet` | Resource $\times$ Action Category | Current Monthly Run-rate, Est. Monthly Savings, Est. Annual Savings, Est. Monthly Carbon Saved | FinOps prioritization, quick-win action cards |
| `mart_carbon_emissions` | `mart_carbon_emissions.parquet` | Regional Data Center | Total Energy (kWh), Scope 2 Operational, Scope 3 Embodied, Carbon Intensity ($gCO_2e/\$$) | GreenOps dashboard, regional workload migration simulator |

---

## 5. Automated Data Quality & Validation Rules

The pipeline enforces 25 continuous integrity assertions executed by [`src/pipeline/validator.py`](file:///c:/Users/USER/Desktop/CloudSense-AI/src/pipeline/validator.py):

1. **Primary Key Uniqueness & Non-Nullness**:
   - `dim_date.date_key` (250 distinct dates)
   - `dim_provider.provider_id` (1 distinct provider: GCP)
   - `dim_region.region_id` (5 distinct regions)
   - `dim_service.service_id` (7 distinct services)
   - `dim_resource.resource_id` (200 distinct cloud assets)
   - `fact_usage.usage_fact_id` (50,000 distinct records)
   - `fact_cost.cost_fact_id` (50,000 distinct records)
   - `fact_carbon.carbon_fact_id` (50,000 distinct records)
   - `fact_anomaly.anomaly_fact_id` (18 distinct incidents)
2. **Referential Integrity (Foreign Keys)**:
   - 100% of foreign keys (`resource_id`, `service_id`, `region_id`, `date_key`, `provider_id`) across all fact tables match valid rows in their parent dimension tables. Zero orphan records.
3. **Physical & Utilization Invariants**:
   - $0.0\% \le \text{avg\_cpu\_utilization\_pct} \le \text{max\_cpu\_utilization\_pct} \le 100.0\%$.
   - $0.0\% \le \text{avg\_memory\_utilization\_pct} \le \text{max\_memory\_utilization\_pct} \le 100.0\%$.
4. **Financial Consistency**:
   - $\text{Net Cost} = \max(0, \text{List Cost} - \text{Discount Amount})$ with $\epsilon < 0.001$.
5. **Carbon Consistency**:
   - $\text{Total Carbon} = \text{Scope 2} + \text{Scope 3}$ with $\epsilon < 0.002$.
6. **Reconciliation Invariant**:
   - $\sum \text{Net Cost}_{\text{mart\_cost\_trends}} \equiv \sum \text{Net Cost}_{\text{fact\_cost}} = \$726,397.32$.

---

## 6. BigQuery Migration (Implemented in Phase 6)

The local warehouse architecture (DuckDB over Parquet) was deliberately
engineered for a low-friction migration to Google BigQuery, and that
migration path has since been **implemented and validated** as an additive,
optional data warehouse — see **`docs/bigquery_migration.md`** for the full
architecture, table/partition/cluster documentation, authentication setup,
and exact commands.

**Summary (see the linked doc for details):**
- `src/pipeline/schema.py` remains the single schema source of truth for
  both the local Parquet layer and BigQuery (`GOLD_TABLE_SCHEMAS`,
  `MART_TABLE_SCHEMAS`, `BIGQUERY_SPECS`).
- `src/pipeline/bigquery_client.py` loads Gold/Mart Parquet files directly
  into BigQuery via `load_table_from_file()` (no intermediate Cloud Storage
  staging step is required for this dataset's size).
- `run_bigquery_migration.py` is a manually-executed, one-shot migration +
  validation script — it is never run automatically.
- **The running API/frontend are unaffected**: `AnalyticsService` continues
  to read `data/analytics_summary.json` exclusively. BigQuery exists today
  purely as a validated, parallel warehouse for future use, not as the live
  serving backend.
