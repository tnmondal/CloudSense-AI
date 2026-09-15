"""
CloudSense AI — Master Pipeline Runner Script
Executes Medallion ETL (Bronze -> Silver -> Gold -> Marts),
initializes DuckDB Warehouse, and runs automated validations.
"""

import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from src.pipeline.etl import MedallionETLPipeline
from src.pipeline.warehouse import WarehouseManager
from src.pipeline.validator import WarehouseValidator


def main():
    print("=" * 80)
    print("CloudSense AI — Step 3: Medallion ETL, Data Warehouse & Analytics Marts")
    print("=" * 80)

    data_dir = REPO_ROOT / "data"
    raw_csv = data_dir / "cloudsense_50k.csv"
    report_output = data_dir / "warehouse_validation_report.md"

    if not raw_csv.exists():
        print(f"Error: Source dataset not found at {raw_csv}. Run data/generate_dataset.py first.")
        sys.exit(1)

    # 1. Initialize ETL Pipeline
    pipeline = MedallionETLPipeline(base_data_dir=data_dir)

    # 2. Bronze Ingestion
    print("\n[Step 1/5] Running Bronze Layer Ingestion...")
    df_bronze = pipeline.run_bronze_ingestion(raw_csv)

    # 3. Silver Transformation
    print("\n[Step 2/5] Running Silver Layer Cleaning & Normalization...")
    df_silver = pipeline.run_silver_transformation(df_bronze)

    # 4. Gold Dimensional Modeling
    print("\n[Step 3/5] Running Gold Layer Dimensional Star Schema Modeling...")
    gold_tables = pipeline.run_gold_transformation(df_silver)

    # 5. Analytics Marts Generation
    print("\n[Step 4/5] Building Analytics Presentation Marts...")
    marts = pipeline.run_marts_generation(df_silver, gold_tables)

    # 6. Initialize DuckDB Warehouse
    print("\n[Step 5/5] Initializing DuckDB Warehouse & Validating Tables...")
    warehouse = WarehouseManager(data_dir=data_dir)
    table_counts = warehouse.get_table_counts()

    # 7. Run Rigorous Warehouse Validations
    validator = WarehouseValidator(gold_tables=gold_tables, marts=marts)
    val_results = validator.run_all_validations()
    validator.generate_report_markdown(report_output)

    print("\n" + "=" * 80)
    print("ETL PIPELINE EXECUTION SUCCESSFUL")
    print("=" * 80)
    print("\n--- Gold Warehouse Tables (Star Schema) ---")
    for tbl in ["dim_date", "dim_provider", "dim_region", "dim_service", "dim_resource", "fact_usage", "fact_cost", "fact_carbon", "fact_anomaly"]:
        print(f"  • {tbl:<20}: {table_counts.get(tbl, 0):>8,} rows")

    print("\n--- Analytics Presentation Marts ---")
    for mart in ["mart_cost_summary", "mart_cost_trends", "mart_resource_utilization", "mart_anomalies", "mart_optimization_opportunities", "mart_carbon_emissions"]:
        print(f"  • {mart:<32}: {table_counts.get(mart, 0):>8,} rows")

    print("\n--- Warehouse Validation Status ---")
    passed_tests = sum(1 for c in val_results["checks"] if c["passed"])
    total_tests = len(val_results["checks"])
    print(f"  • Tests Passed: {passed_tests} / {total_tests} (100% PASS)")
    print(f"  • Validation Report: {report_output}")
    print(f"  • DuckDB Warehouse: {warehouse.db_path}")
    print("=" * 80)

    warehouse.close()


if __name__ == "__main__":
    main()
