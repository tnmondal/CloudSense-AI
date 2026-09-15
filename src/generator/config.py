"""
CloudSense AI — Data Generator Configuration & Catalogs
Defines the enterprise organization, cloud catalog, hardware benchmarks,
regional emissions, and pricing rate cards used for realistic synthesis.
"""

from typing import Dict, List, Any

# Fixed random seed for complete reproducibility
RANDOM_SEED = 42

# Time span configuration: 250 contiguous days x 200 distinct cloud resources = exactly 50,000 records
START_DATE = "2025-09-01"
DAYS_COUNT = 250
RESOURCES_COUNT = 200

# Enterprise Organizational Hierarchy (Apex Enterprises Inc.)
ORGANIZATION_STRUCTURE = [
    {
        "project_id": "proj-checkout-prod",
        "project_name": "Checkout & Payments Production",
        "department": "Engineering",
        "cost_center": "CC-1001",
        "environment": "production",
        "owner_email": "checkout-lead@apex.corp",
        "business_criticality": "Tier-1",
    },
    {
        "project_id": "proj-checkout-staging",
        "project_name": "Checkout & Payments Staging",
        "department": "Engineering",
        "cost_center": "CC-1001",
        "environment": "staging",
        "owner_email": "checkout-qa@apex.corp",
        "business_criticality": "Tier-3",
    },
    {
        "project_id": "proj-data-lakehouse",
        "project_name": "Enterprise Data Lakehouse",
        "department": "Data & AI",
        "cost_center": "CC-2002",
        "environment": "production",
        "owner_email": "data-infra@apex.corp",
        "business_criticality": "Tier-1",
    },
    {
        "project_id": "proj-model-training",
        "project_name": "GenAI & ML Model Training",
        "department": "Data & AI",
        "cost_center": "CC-2002",
        "environment": "development",
        "owner_email": "ml-research@apex.corp",
        "business_criticality": "Tier-2",
    },
    {
        "project_id": "proj-frontend-prod",
        "project_name": "Customer Experience Web Apps",
        "department": "Customer Experience",
        "cost_center": "CC-3003",
        "environment": "production",
        "owner_email": "frontend-lead@apex.corp",
        "business_criticality": "Tier-1",
    },
    {
        "project_id": "proj-core-infra",
        "project_name": "Shared Kubernetes & VPC Backbone",
        "department": "Operations",
        "cost_center": "CC-4004",
        "environment": "production",
        "owner_email": "sre-core@apex.corp",
        "business_criticality": "Tier-1",
    },
    {
        "project_id": "proj-qa-automation",
        "project_name": "End-to-End QA & Load Testing",
        "department": "Internal Tools",
        "cost_center": "CC-5005",
        "environment": "development",
        "owner_email": "qa-tools@apex.corp",
        "business_criticality": "Tier-3",
    },
    {
        "project_id": "proj-analytics-bi",
        "project_name": "Corporate BI & Reporting",
        "department": "Data & AI",
        "cost_center": "CC-2002",
        "environment": "production",
        "owner_email": "bi-reports@apex.corp",
        "business_criticality": "Tier-2",
    }
]

# Cloud Regions: PUE, Grid Carbon Intensity (gCO2e/kWh), and Renewable Energy Profile
REGIONS_CATALOG: Dict[str, Dict[str, Any]] = {
    "us-central1": {
        "region_name": "Iowa, USA",
        "country": "US",
        "continent": "North America",
        "pue_factor": 1.10,
        "grid_carbon_intensity_gco2_per_kwh": 132.0,
        "renewable_tier": "High (>80%)",
    },
    "us-east4": {
        "region_name": "Northern Virginia, USA",
        "country": "US",
        "continent": "North America",
        "pue_factor": 1.12,
        "grid_carbon_intensity_gco2_per_kwh": 339.0,
        "renewable_tier": "Moderate (40-80%)",
    },
    "europe-west6": {
        "region_name": "Zurich, Switzerland",
        "country": "CH",
        "continent": "Europe",
        "pue_factor": 1.08,
        "grid_carbon_intensity_gco2_per_kwh": 15.3,
        "renewable_tier": "High (>80%)",
    },
    "europe-west1": {
        "region_name": "St. Ghislain, Belgium",
        "country": "BE",
        "continent": "Europe",
        "pue_factor": 1.10,
        "grid_carbon_intensity_gco2_per_kwh": 167.0,
        "renewable_tier": "Moderate (40-80%)",
    },
    "asia-south1": {
        "region_name": "Mumbai, India",
        "country": "IN",
        "continent": "Asia",
        "pue_factor": 1.15,
        "grid_carbon_intensity_gco2_per_kwh": 712.0,
        "renewable_tier": "Low (<40%)",
    },
}

# Pricing Plans and Commitment Discounts
PRICING_PLANS: Dict[str, Dict[str, Any]] = {
    "plan-on-demand": {
        "pricing_plan_id": "plan-on-demand",
        "commitment_type": "On-Demand",
        "discount_percentage": 0.00,
        "commitment_duration_months": 0,
    },
    "plan-cud-1yr": {
        "pricing_plan_id": "plan-cud-1yr",
        "commitment_type": "Commitment-1Yr",
        "discount_percentage": 0.25,
        "commitment_duration_months": 12,
    },
    "plan-cud-3yr": {
        "pricing_plan_id": "plan-cud-3yr",
        "commitment_type": "Commitment-3Yr",
        "discount_percentage": 0.45,
        "commitment_duration_months": 36,
    },
    "plan-spot": {
        "pricing_plan_id": "plan-spot",
        "commitment_type": "Spot",
        "discount_percentage": 0.65,
        "commitment_duration_months": 0,
    }
}

# Machine Specifications and Rate Cards
MACHINE_SPECS: Dict[str, Dict[str, Any]] = {
    "e2-micro": {
        "vcpu": 2,
        "memory_gb": 1.0,
        "hourly_rate_usd": 0.0084,
        "category": "General Purpose (Burstable)",
    },
    "e2-medium": {
        "vcpu": 2,
        "memory_gb": 4.0,
        "hourly_rate_usd": 0.0336,
        "category": "General Purpose",
    },
    "n2-standard-4": {
        "vcpu": 4,
        "memory_gb": 16.0,
        "hourly_rate_usd": 0.1942,
        "category": "Standard Balanced",
    },
    "n2-standard-8": {
        "vcpu": 8,
        "memory_gb": 32.0,
        "hourly_rate_usd": 0.3884,
        "category": "Standard Balanced",
    },
    "c2-standard-16": {
        "vcpu": 16,
        "memory_gb": 64.0,
        "hourly_rate_usd": 0.7768,
        "category": "Compute-Optimized",
    },
    "c2-standard-30": {
        "vcpu": 30,
        "memory_gb": 120.0,
        "hourly_rate_usd": 1.4565,
        "category": "Compute-Optimized",
    },
    "a2-highgpu-1g": {
        "vcpu": 12,
        "memory_gb": 85.0,
        "hourly_rate_usd": 3.6738,
        "category": "GPU Accelerated (NVIDIA A100)",
    },
    "db-custom-4-16": {
        "vcpu": 4,
        "memory_gb": 16.0,
        "hourly_rate_usd": 0.2450,
        "category": "Managed Database (Cloud SQL)",
    },
    "db-custom-8-32": {
        "vcpu": 8,
        "memory_gb": 32.0,
        "hourly_rate_usd": 0.4900,
        "category": "Managed Database (Cloud SQL)",
    },
}

# Storage Rates ($/GB-Month, $/GB-Day = $/GB-Month / 30.0)
STORAGE_RATES: Dict[str, Dict[str, Any]] = {
    "standard-storage": {
        "rate_per_gb_month": 0.020,
        "rate_per_gb_day": 0.020 / 30.0,
        "retrieval_fee_per_gb": 0.0,
        "unit": "gib-month",
    },
    "nearline-storage": {
        "rate_per_gb_month": 0.010,
        "rate_per_gb_day": 0.010 / 30.0,
        "retrieval_fee_per_gb": 0.01,
        "unit": "gib-month",
    },
    "coldline-storage": {
        "rate_per_gb_month": 0.004,
        "rate_per_gb_day": 0.004 / 30.0,
        "retrieval_fee_per_gb": 0.02,
        "unit": "gib-month",
    },
    "archive-storage": {
        "rate_per_gb_month": 0.0012,
        "rate_per_gb_day": 0.0012 / 30.0,
        "retrieval_fee_per_gb": 0.05,
        "unit": "gib-month",
    },
    "persistent-ssd": {
        "rate_per_gb_month": 0.170,
        "rate_per_gb_day": 0.170 / 30.0,
        "retrieval_fee_per_gb": 0.0,
        "unit": "gib-month",
    },
    "persistent-standard": {
        "rate_per_gb_month": 0.040,
        "rate_per_gb_day": 0.040 / 30.0,
        "retrieval_fee_per_gb": 0.0,
        "unit": "gib-month",
    }
}

# BigQuery, Serverless, and Networking Pricing
CONSUMPTION_RATES = {
    "bigquery_tb_scanned": 6.25,          # $6.25 per TB scanned
    "cloud_run_vcpu_hour": 0.0864,        # $0.00002400 / vCPU-sec * 3600
    "cloud_run_gib_hour": 0.0090,         # $0.00000250 / GiB-sec * 3600
    "cloud_run_req_million": 0.40,        # $0.40 per million requests
    "egress_internet_per_gb": 0.12,       # $0.12 / GB internet egress
    "egress_inter_region_per_gb": 0.02,   # $0.02 / GB inter-region egress
}

# Hardware Power Constants (SPECpower benchmarks)
POWER_CONSTANTS = {
    "p_idle_per_vcpu_watts": 12.50,       # Base server power per vCPU at 0% load
    "p_max_per_vcpu_watts": 35.00,        # Maximum power per vCPU at 100% saturation
    "p_ram_per_gb_watts": 0.38,           # Memory wattage
    "p_disk_ssd_per_tb_watts": 1.20,      # SSD storage wattage
    "p_disk_hdd_per_tb_watts": 0.65,      # HDD storage wattage
    "server_embodied_co2_kg": 1200.0,     # 1,200 kg CO2e per 128-vCPU server chassis
    "server_lifespan_hours": 35064.0,     # 4 years lifespan (4 * 365.25 * 24)
    "chassis_total_vcpus": 128.0,
}
