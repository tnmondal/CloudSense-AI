"""
CloudSense AI — Synthetic Dataset Generator Engine
Produces exactly 50,000 realistic, internally consistent, reproducible cloud usage records
coupling resource utilization, financial cost, and SPECpower/CCF carbon metrics.
"""

import math
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import numpy as np
import pandas as pd

from src.generator.config import (
    RANDOM_SEED,
    START_DATE,
    DAYS_COUNT,
    RESOURCES_COUNT,
    ORGANIZATION_STRUCTURE,
    REGIONS_CATALOG,
    PRICING_PLANS,
    MACHINE_SPECS,
    STORAGE_RATES,
    CONSUMPTION_RATES,
    POWER_CONSTANTS,
)
from src.generator.anomalies import INJECTED_INCIDENTS


def build_resource_inventory() -> List[Dict[str, Any]]:
    """
    Constructs a persistent inventory of exactly 200 enterprise cloud resources
    with designated archetypes: production steady, bursty, rightsizing candidates,
    idle zombies, storage tiers, serverless APIs, BigQuery pipelines, and network NATs.
    """
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    
    inventory: List[Dict[str, Any]] = []
    
    # 1. Compute Engine VMs (60 resources)
    vm_types = [
        ("e2-micro", 6),
        ("e2-medium", 14),
        ("n2-standard-4", 18),
        ("n2-standard-8", 10),
        ("c2-standard-16", 8),
        ("c2-standard-30", 2),
        ("a2-highgpu-1g", 2),
    ]
    vm_idx = 1
    for mtype, count in vm_types:
        for _ in range(count):
            spec = MACHINE_SPECS[mtype]
            # Distribute projects: dev/staging get micro/medium/c2, prod gets n2/c2/a2
            if "a2" in mtype:
                proj = next(p for p in ORGANIZATION_STRUCTURE if p["project_id"] == "proj-model-training")
                region_key = random.choice(["us-central1", "us-east4"])
                plan_key = "plan-on-demand"
                archetype = "ml_gpu_training"
            elif mtype in ["e2-micro", "e2-medium"]:
                proj = random.choice([
                    p for p in ORGANIZATION_STRUCTURE if p["environment"] in ["staging", "development", "sandbox"]
                ])
                region_key = random.choice(list(REGIONS_CATALOG.keys()))
                plan_key = random.choice(["plan-on-demand", "plan-spot"])
                archetype = "dev_general"
            elif vm_idx in [15, 16, 17, 18, 19]:  # Designated idle zombie VMs
                proj = random.choice([p for p in ORGANIZATION_STRUCTURE if p["environment"] in ["staging", "development"]])
                region_key = "us-east4"
                plan_key = "plan-on-demand"
                archetype = "idle_zombie"
            elif vm_idx in [25, 26, 27, 28, 29, 30]:  # Overprovisioned rightsizing candidates
                proj = next(p for p in ORGANIZATION_STRUCTURE if p["project_id"] == "proj-checkout-prod")
                region_key = "us-central1"
                plan_key = "plan-cud-1yr"
                archetype = "overprovisioned_compute"
            else:
                proj = random.choice([p for p in ORGANIZATION_STRUCTURE if p["environment"] == "production"])
                region_key = random.choice(["us-central1", "europe-west6", "europe-west1", "asia-south1"])
                plan_key = random.choice(["plan-on-demand", "plan-cud-1yr", "plan-cud-3yr"])
                archetype = "prod_steady"

            inventory.append({
                "resource_id": f"vm-{proj['project_id'].split('-')[1]}-{mtype.replace('.', '-')}-{vm_idx:03d}",
                "resource_name": f"{proj['project_name']} VM ({mtype}) #{vm_idx:02d}",
                "service_id": "compute-engine-vm",
                "service_name": "Compute Engine",
                "service_family": "Compute",
                "resource_type": mtype,
                "project": proj,
                "region_id": region_key,
                "pricing_plan_id": plan_key,
                "archetype": archetype,
                "provisioned_vcpu": spec["vcpu"],
                "provisioned_memory_gb": spec["memory_gb"],
                "provisioned_storage_gb": 100.0,
                "pricing_unit": "hour",
                "hourly_rate_usd": spec["hourly_rate_usd"],
            })
            vm_idx += 1

    # 2. GKE Node Pools (35 resources)
    for gke_idx in range(1, 36):
        proj = random.choice([p for p in ORGANIZATION_STRUCTURE if p["project_id"] in ["proj-core-infra", "proj-checkout-prod", "proj-qa-automation"]])
        if gke_idx == 10:
            # Target for runaway incident
            res_id = "gke-qa-loadtest-pool"
            archetype = "incident_target_gke"
            mtype = "c2-standard-16"
            proj = next(p for p in ORGANIZATION_STRUCTURE if p["project_id"] == "proj-qa-automation")
            region_key = "us-east4"
        elif gke_idx in [12, 13, 14]:
            archetype = "overprovisioned_compute"
            mtype = "n2-standard-8"
            region_key = "us-central1"
        else:
            archetype = "prod_steady"
            mtype = random.choice(["n2-standard-4", "n2-standard-8", "e2-medium"])
            region_key = random.choice(["us-central1", "europe-west6", "europe-west1"])

        spec = MACHINE_SPECS[mtype]
        inventory.append({
            "resource_id": res_id if gke_idx == 10 else f"gke-pool-{proj['project_id'].split('-')[1]}-{gke_idx:03d}",
            "resource_name": f"GKE Cluster Node Pool #{gke_idx:02d}",
            "service_id": "gke-node-pool",
            "service_name": "Google Kubernetes Engine",
            "service_family": "Containers",
            "resource_type": f"gke-{mtype}",
            "project": proj,
            "region_id": region_key,
            "pricing_plan_id": "plan-cud-1yr" if proj["environment"] == "production" else "plan-on-demand",
            "archetype": archetype,
            "provisioned_vcpu": spec["vcpu"] * 2,  # 2 nodes per standard pool
            "provisioned_memory_gb": spec["memory_gb"] * 2,
            "provisioned_storage_gb": 200.0,
            "pricing_unit": "hour",
            "hourly_rate_usd": spec["hourly_rate_usd"] * 2,
        })

    # 3. Cloud SQL Databases (25 resources)
    for db_idx in range(1, 26):
        proj = random.choice([p for p in ORGANIZATION_STRUCTURE if p["project_id"] in ["proj-checkout-prod", "proj-frontend-prod", "proj-checkout-staging", "proj-qa-automation"]])
        mtype = "db-custom-8-32" if proj["environment"] == "production" else "db-custom-4-16"
        spec = MACHINE_SPECS[mtype]
        region_key = "us-central1" if proj["environment"] == "production" else "us-east4"
        
        # 3 staging DBs are zombie idle
        archetype = "idle_zombie" if db_idx in [20, 21, 22] else "prod_steady"

        inventory.append({
            "resource_id": f"sql-{proj['project_id'].split('-')[1]}-db-{db_idx:03d}",
            "resource_name": f"{proj['project_name']} PostgreSQL #{db_idx:02d}",
            "service_id": "cloud-sql",
            "service_name": "Cloud SQL",
            "service_family": "Database",
            "resource_type": mtype,
            "project": proj,
            "region_id": region_key,
            "pricing_plan_id": "plan-cud-1yr" if proj["environment"] == "production" else "plan-on-demand",
            "archetype": archetype,
            "provisioned_vcpu": spec["vcpu"],
            "provisioned_memory_gb": spec["memory_gb"],
            "provisioned_storage_gb": 500.0 if proj["environment"] == "production" else 100.0,
            "pricing_unit": "hour",
            "hourly_rate_usd": spec["hourly_rate_usd"],
        })

    # 4. Cloud Storage Buckets (30 resources)
    storage_tiers = [
        ("standard-storage", 14),
        ("nearline-storage", 8),
        ("coldline-storage", 5),
        ("archive-storage", 3),
    ]
    st_idx = 1
    for st_type, count in storage_tiers:
        for _ in range(count):
            proj = random.choice(ORGANIZATION_STRUCTURE)
            region_key = random.choice(list(REGIONS_CATALOG.keys()))
            
            # 8 standard buckets are candidates for lifecycle transition (cold data in standard tier)
            if st_type == "standard-storage" and st_idx in [5, 6, 7, 8, 9, 10, 11, 12]:
                archetype = "stale_storage"
            elif st_idx == 1:  # Target for debug logging explosion
                archetype = "incident_target_storage"
                res_id = "gcs-app-logs-raw"
            else:
                archetype = "prod_steady"

            rate_info = STORAGE_RATES[st_type]
            inventory.append({
                "resource_id": res_id if (st_type == "standard-storage" and st_idx == 1) else f"gcs-{proj['project_id'].split('-')[1]}-{st_type.split('-')[0]}-{st_idx:03d}",
                "resource_name": f"Cloud Storage Bucket ({st_type}) #{st_idx:02d}",
                "service_id": "cloud-storage",
                "service_name": "Cloud Storage",
                "service_family": "Storage",
                "resource_type": st_type,
                "project": proj,
                "region_id": region_key,
                "pricing_plan_id": "plan-on-demand",
                "archetype": archetype,
                "provisioned_vcpu": 0.0,
                "provisioned_memory_gb": 0.0,
                "provisioned_storage_gb": float(random.randint(500, 15000)),
                "pricing_unit": "gib-month",
                "hourly_rate_usd": rate_info["rate_per_gb_day"] / 24.0,  # normalized hourly
            })
            st_idx += 1

    # 5. Cloud Run Serverless Services (20 resources)
    for cr_idx in range(1, 21):
        proj = random.choice([p for p in ORGANIZATION_STRUCTURE if p["project_id"] in ["proj-checkout-prod", "proj-frontend-prod", "proj-checkout-staging"]])
        region_key = random.choice(["us-central1", "europe-west1", "europe-west6"])
        if cr_idx == 1:
            res_id = "cr-checkout-api"
            archetype = "incident_target_serverless"
        else:
            archetype = "prod_steady"

        inventory.append({
            "resource_id": res_id if cr_idx == 1 else f"cr-{proj['project_id'].split('-')[1]}-svc-{cr_idx:03d}",
            "resource_name": f"Cloud Run Microservice #{cr_idx:02d}",
            "service_id": "cloud-run",
            "service_name": "Cloud Run",
            "service_family": "Serverless",
            "resource_type": "serverless-service",
            "project": proj,
            "region_id": region_key,
            "pricing_plan_id": "plan-on-demand",
            "archetype": archetype,
            "provisioned_vcpu": 2.0,
            "provisioned_memory_gb": 4.0,
            "provisioned_storage_gb": 0.0,
            "pricing_unit": "request-million",
            "hourly_rate_usd": 0.0, # Derived from requests + CPU
        })

    # 6. BigQuery Datasets & Query Pipelines (15 resources)
    for bq_idx in range(1, 16):
        proj = next(p for p in ORGANIZATION_STRUCTURE if p["project_id"] in ["proj-data-lakehouse", "proj-analytics-bi"])
        region_key = "us-central1"
        if bq_idx == 1:
            res_id = "bq-analytics-pipeline"
            archetype = "incident_target_bigquery"
        else:
            archetype = "prod_steady"

        inventory.append({
            "resource_id": res_id if bq_idx == 1 else f"bq-{proj['project_id'].split('-')[1]}-dataset-{bq_idx:03d}",
            "resource_name": f"BigQuery Analytics Pipeline #{bq_idx:02d}",
            "service_id": "bigquery",
            "service_name": "BigQuery",
            "service_family": "Analytics",
            "resource_type": "analytics-slots",
            "project": proj,
            "region_id": region_key,
            "pricing_plan_id": "plan-on-demand",
            "archetype": archetype,
            "provisioned_vcpu": 4.0,
            "provisioned_memory_gb": 16.0,
            "provisioned_storage_gb": float(random.randint(2000, 25000)),
            "pricing_unit": "tb-scanned",
            "hourly_rate_usd": 0.0, # Derived from TB scanned
        })

    # 7. Cloud NAT & Networking Gateways (15 resources)
    for net_idx in range(1, 16):
        proj = random.choice([p for p in ORGANIZATION_STRUCTURE if p["project_id"] in ["proj-core-infra", "proj-checkout-prod"]])
        region_key = random.choice(list(REGIONS_CATALOG.keys()))
        if net_idx == 1:
            res_id = "net-nat-gateway-us"
            archetype = "incident_target_network"
        else:
            archetype = "prod_steady"

        inventory.append({
            "resource_id": res_id if net_idx == 1 else f"net-{proj['project_id'].split('-')[1]}-gw-{net_idx:03d}",
            "resource_name": f"Cloud NAT & VPC Interconnect #{net_idx:02d}",
            "service_id": "cloud-nat-egress",
            "service_name": "Cloud NAT & Networking",
            "service_family": "Networking",
            "resource_type": "nat-gateway",
            "project": proj,
            "region_id": region_key,
            "pricing_plan_id": "plan-on-demand",
            "archetype": archetype,
            "provisioned_vcpu": 1.0,
            "provisioned_memory_gb": 2.0,
            "provisioned_storage_gb": 0.0,
            "pricing_unit": "gib-transfer",
            "hourly_rate_usd": 0.045, # Gateway base rate
        })

    assert len(inventory) == RESOURCES_COUNT, f"Expected {RESOURCES_COUNT} resources, got {len(inventory)}"
    return inventory


def generate_time_series_dataset() -> pd.DataFrame:
    """
    Generates exactly 50,000 records (250 days x 200 persistent resources)
    modeling realistic temporal dynamics, physics, carbon emissions, and non-random anomalies.
    """
    # Deterministic seeding
    np.random.seed(RANDOM_SEED)
    random.seed(RANDOM_SEED)

    inventory = build_resource_inventory()
    start_dt = datetime.strptime(START_DATE, "%Y-%m-%d")
    
    rows: List[Dict[str, Any]] = []

    # Map incidents by day offset and resource_id
    incident_map: Dict[Tuple[int, str], Dict[str, Any]] = {}
    for inc in INJECTED_INCIDENTS:
        for offset in range(inc["start_day_offset"], inc["start_day_offset"] + inc["duration_days"]):
            incident_map[(offset, inc["target_resource_id"])] = inc

    # Generate day-by-day for each resource
    for day_idx in range(DAYS_COUNT):
        curr_dt = start_dt + timedelta(days=day_idx)
        date_str = curr_dt.strftime("%Y-%m-%d")
        dow = curr_dt.weekday()
        is_weekend = dow >= 5
        dom = curr_dt.day

        # Global organic growth trend (+0.04% per day ~ 10% over 250 days)
        organic_growth = 1.0 + (0.0004 * day_idx)

        # Black Friday / Cyber Monday surge (around day 84 to 88, late November)
        is_black_friday = (84 <= day_idx <= 88)
        bf_multiplier = 1.75 if is_black_friday else 1.0

        for res in inventory:
            proj = res["project"]
            reg = REGIONS_CATALOG[res["region_id"]]
            plan = PRICING_PLANS[res["pricing_plan_id"]]
            archetype = res["archetype"]
            service_id = res["service_id"]

            # Check if active incident
            active_inc = incident_map.get((day_idx, res["resource_id"]))

            # --- Base Utilization and Metrics ---
            runtime_hours = 24.0
            total_requests = 0
            disk_read_iops = 0.0
            disk_write_iops = 0.0
            network_ingress_gb = 0.0
            network_egress_gb = 0.0
            is_idle = False
            anomaly_flag = False
            anomaly_type = "None"
            optimization_category = "None"

            # 1. Physical Utilization modeling per archetype
            if archetype == "idle_zombie":
                # Idle resource with near-zero utilization
                avg_cpu = round(random.uniform(0.5, 2.5), 2)
                max_cpu = round(avg_cpu + random.uniform(0.5, 2.0), 2)
                avg_ram = round(random.uniform(3.0, 7.5), 2)
                max_ram = round(avg_ram + random.uniform(1.0, 3.0), 2)
                disk_read_iops = round(random.uniform(0.0, 1.5), 2)
                disk_write_iops = round(random.uniform(0.1, 2.0), 2)
                network_ingress_gb = round(random.uniform(0.01, 0.15), 3)
                network_egress_gb = round(random.uniform(0.01, 0.10), 3)
                total_requests = random.randint(0, 50)
                is_idle = True
                optimization_category = "idle_zombie"

            elif archetype == "overprovisioned_compute":
                # Consistently low utilization despite high allocation
                avg_cpu = round(random.uniform(4.0, 11.5), 2)
                max_cpu = round(avg_cpu + random.uniform(3.0, 8.0), 2)
                avg_ram = round(random.uniform(15.0, 24.0), 2)
                max_ram = round(avg_ram + random.uniform(4.0, 9.0), 2)
                disk_read_iops = round(random.uniform(10.0, 45.0), 2)
                disk_write_iops = round(random.uniform(15.0, 50.0), 2)
                network_ingress_gb = round(random.uniform(1.5, 8.0), 2)
                network_egress_gb = round(random.uniform(1.0, 6.5), 2)
                total_requests = random.randint(2000, 12000)
                optimization_category = "compute_rightsizing"

            elif archetype == "stale_storage":
                # Cold data sitting in standard storage tier
                avg_cpu = 0.0
                max_cpu = 0.0
                avg_ram = 0.0
                max_ram = 0.0
                disk_read_iops = 0.0
                disk_write_iops = round(random.uniform(0.0, 0.5), 2)
                network_ingress_gb = 0.0
                network_egress_gb = round(random.uniform(0.0, 0.05), 3)
                optimization_category = "storage_lifecycle"

            elif archetype == "ml_gpu_training":
                # High GPU compute during training sprints, quiet on weekends
                if is_weekend:
                    avg_cpu = round(random.uniform(5.0, 15.0), 2)
                    max_cpu = round(avg_cpu + random.uniform(5.0, 12.0), 2)
                    avg_ram = round(random.uniform(20.0, 35.0), 2)
                else:
                    avg_cpu = round(random.uniform(70.0, 92.0), 2)
                    max_cpu = round(random.uniform(92.0, 99.5), 2)
                    avg_ram = round(random.uniform(65.0, 88.0), 2)
                max_ram = round(min(100.0, avg_ram + random.uniform(5.0, 10.0)), 2)
                disk_read_iops = round(random.uniform(150.0, 600.0), 2)
                disk_write_iops = round(random.uniform(100.0, 400.0), 2)
                network_ingress_gb = round(random.uniform(15.0, 80.0), 2)
                network_egress_gb = round(random.uniform(10.0, 50.0), 2)

            else:
                # Standard production or dev workload
                if proj["environment"] in ["development", "staging"]:
                    # Dev workloads drop drastically on weekends
                    factor = 0.35 if is_weekend else 1.0
                else:
                    # Prod workloads rise on weekends (e-commerce) and paydays
                    factor = 1.15 if is_weekend else 1.0
                    if dom in [1, 15]:
                        factor *= 1.25
                
                factor *= organic_growth * bf_multiplier

                base_cpu = random.uniform(38.0, 62.0) * factor
                avg_cpu = round(min(88.0, max(2.0, base_cpu)), 2)
                max_cpu = round(min(98.0, avg_cpu + random.uniform(8.0, 22.0)), 2)
                
                base_ram = random.uniform(45.0, 70.0) * (0.85 if is_weekend and proj["environment"] != "production" else 1.0)
                avg_ram = round(min(89.0, max(5.0, base_ram)), 2)
                max_ram = round(min(98.0, avg_ram + random.uniform(5.0, 15.0)), 2)

                disk_read_iops = round(random.uniform(40.0, 180.0) * factor, 2)
                disk_write_iops = round(random.uniform(30.0, 150.0) * factor, 2)
                network_ingress_gb = round(random.uniform(5.0, 35.0) * factor, 2)
                network_egress_gb = round(random.uniform(10.0, 60.0) * factor, 2)
                total_requests = int(random.randint(15000, 75000) * factor)

            # High carbon intensity region optimization flag (e.g. Mumbai batch or Virginia dev)
            if reg["grid_carbon_intensity_gco2_per_kwh"] > 300.0 and proj["environment"] in ["development", "staging"]:
                if optimization_category == "None":
                    optimization_category = "green_migration"

            # 2. Injected Incident Overrides (Controlled, Physical, Explainable)
            vcpu = res["provisioned_vcpu"]
            ram_gb = res["provisioned_memory_gb"]
            storage_gb = res["provisioned_storage_gb"]

            if active_inc:
                anomaly_flag = True
                anomaly_type = active_inc["anomaly_type"]
                effects = active_inc["effects"]

                if "provisioned_vcpu" in effects:
                    vcpu = effects["provisioned_vcpu"]
                if "provisioned_memory_gb" in effects:
                    ram_gb = effects["provisioned_memory_gb"]
                if "avg_cpu_utilization_pct" in effects:
                    avg_cpu = effects["avg_cpu_utilization_pct"]
                    max_cpu = effects.get("max_cpu_utilization_pct", avg_cpu + 3.0)
                if "network_egress_gb_override" in effects:
                    network_egress_gb = effects["network_egress_gb_override"]
                if "provisioned_storage_gb_multiplier" in effects:
                    storage_gb *= effects["provisioned_storage_gb_multiplier"]
                if "total_requests_multiplier" in effects:
                    total_requests = int(total_requests * effects["total_requests_multiplier"])

            # 3. Usage Quantity and Financial Cost Calculations
            if service_id == "compute-engine-vm" or service_id == "gke-node-pool":
                usage_quantity = runtime_hours
                list_unit_price = res["hourly_rate_usd"]
                if active_inc and "cost_multiplier" in active_inc["effects"]:
                    list_unit_price *= active_inc["effects"]["cost_multiplier"]
                list_cost = round(usage_quantity * list_unit_price, 4)

            elif service_id == "cloud-sql":
                usage_quantity = runtime_hours
                # Compute hourly + persistent database storage allocation
                storage_daily_rate = (storage_gb * (STORAGE_RATES["persistent-ssd"]["rate_per_gb_day"]))
                hourly_rate = res["hourly_rate_usd"] + (storage_daily_rate / 24.0)
                list_unit_price = round(hourly_rate, 4)
                list_cost = round(usage_quantity * list_unit_price, 4)

            elif service_id == "cloud-storage":
                st_rate_info = STORAGE_RATES[res["resource_type"]]
                usage_quantity = round(storage_gb, 2)
                list_unit_price = round(st_rate_info["rate_per_gb_day"], 6)
                if active_inc and "cost_multiplier" in active_inc["effects"]:
                    usage_quantity *= active_inc["effects"]["cost_multiplier"]
                list_cost = round(usage_quantity * list_unit_price, 4)

            elif service_id == "cloud-run":
                # Derived from requests and execution
                if total_requests == 0:
                    total_requests = random.randint(5000, 35000)
                req_millions = total_requests / 1_000_000.0
                usage_quantity = round(req_millions, 4)
                list_unit_price = CONSUMPTION_RATES["cloud_run_req_million"]
                
                # Serverless vCPU-hours
                exec_vcpu_hours = (total_requests * 0.15) / 3600.0 * vcpu
                compute_fee = exec_vcpu_hours * CONSUMPTION_RATES["cloud_run_vcpu_hour"]
                req_fee = req_millions * list_unit_price
                
                if active_inc and "cost_multiplier" in active_inc["effects"]:
                    req_fee *= active_inc["effects"]["cost_multiplier"]
                    compute_fee *= active_inc["effects"]["cost_multiplier"]

                list_cost = round(req_fee + compute_fee, 4)
                list_unit_price = round(list_cost / max(usage_quantity, 0.0001), 4)

            elif service_id == "bigquery":
                # Usage is TB scanned
                base_tb = random.uniform(5.0, 25.0) * organic_growth
                if dow in [0, 4]: # Mon/Fri heavy ETL
                    base_tb *= 1.4
                if active_inc and "usage_quantity_multiplier" in active_inc["effects"]:
                    base_tb *= active_inc["effects"]["usage_quantity_multiplier"]
                
                usage_quantity = round(base_tb, 3)
                list_unit_price = CONSUMPTION_RATES["bigquery_tb_scanned"]
                list_cost = round(usage_quantity * list_unit_price, 4)

            elif service_id == "cloud-nat-egress":
                usage_quantity = round(network_egress_gb, 3)
                list_unit_price = CONSUMPTION_RATES["egress_internet_per_gb"]
                gateway_base = res["hourly_rate_usd"] * runtime_hours
                transfer_fee = usage_quantity * list_unit_price
                if active_inc and "cost_multiplier" in active_inc["effects"]:
                    transfer_fee *= active_inc["effects"]["cost_multiplier"]
                list_cost = round(gateway_base + transfer_fee, 4)
                list_unit_price = round(list_cost / max(usage_quantity, 0.01), 4)

            else:
                usage_quantity = runtime_hours
                list_unit_price = 0.10
                list_cost = round(usage_quantity * list_unit_price, 4)

            # Apply commitment / contract discounts
            discount_pct = plan["discount_percentage"]
            discount_amount = round(list_cost * discount_pct, 4)
            net_cost = round(list_cost - discount_amount, 4)

            # 4. Energy Consumption & Carbon Emissions (SPECpower & CCF Model)
            # Power (Watts) = P_idle*vCPU + (P_max - P_idle)*vCPU*U + P_ram*RAM + P_disk*Disk
            p_idle = POWER_CONSTANTS["p_idle_per_vcpu_watts"]
            p_max = POWER_CONSTANTS["p_max_per_vcpu_watts"]
            p_ram = POWER_CONSTANTS["p_ram_per_gb_watts"]
            p_disk = POWER_CONSTANTS["p_disk_ssd_per_tb_watts"]

            if vcpu > 0:
                cpu_power = (p_idle * vcpu) + ((p_max - p_idle) * vcpu * (avg_cpu / 100.0))
            else:
                cpu_power = 0.0

            ram_power = p_ram * ram_gb
            disk_power = p_disk * (storage_gb / 1000.0)
            server_power_avg_watts = round(cpu_power + ram_power + disk_power, 3)

            pue = reg["pue_factor"]
            energy_kwh = round((server_power_avg_watts * pue / 1000.0) * runtime_hours, 4)

            # Scope 2 (Operational) = Energy (kWh) * Grid Carbon Intensity (gCO2e/kWh)
            grid_intensity = reg["grid_carbon_intensity_gco2_per_kwh"]
            scope2_co2 = round(energy_kwh * grid_intensity, 3)

            # Scope 3 (Embodied) = (Server Embodied / Lifespan) * (vCPU / Total Server vCPUs) * Runtime Hours
            if vcpu > 0:
                scope3_co2 = round((POWER_CONSTANTS["server_embodied_co2_kg"] * 1000.0 / POWER_CONSTANTS["server_lifespan_hours"]) * (vcpu / POWER_CONSTANTS["chassis_total_vcpus"]) * runtime_hours, 3)
            else:
                # For standalone storage without direct vCPU allocation, model ~0.005 gCO2e / GB-day
                scope3_co2 = round(0.005 * storage_gb, 3)

            total_co2 = round(scope2_co2 + scope3_co2, 3)

            # Construct final schema row
            rec_id = f"rec_{date_str.replace('-', '')}_{len(rows) + 1:05d}"
            rows.append({
                "record_id": rec_id,
                "usage_date": date_str,
                "cloud_provider": "GCP",
                "project_id": proj["project_id"],
                "project_name": proj["project_name"],
                "department": proj["department"],
                "cost_center": proj["cost_center"],
                "environment": proj["environment"],
                "service_id": service_id,
                "service_name": res["service_name"],
                "service_family": res["service_family"],
                "resource_id": res["resource_id"],
                "resource_name": res["resource_name"],
                "resource_type": res["resource_type"],
                "region_id": res["region_id"],
                "region_name": reg["region_name"],
                "pricing_tier": plan["commitment_type"],
                "pricing_unit": res["pricing_unit"],
                "usage_quantity": usage_quantity,
                "list_unit_price_usd": list_unit_price,
                "list_cost_usd": list_cost,
                "discount_amount_usd": discount_amount,
                "net_cost_usd": net_cost,
                "runtime_hours": runtime_hours,
                "provisioned_vcpu": float(vcpu),
                "provisioned_memory_gb": float(ram_gb),
                "provisioned_storage_gb": float(storage_gb),
                "avg_cpu_utilization_pct": float(avg_cpu),
                "max_cpu_utilization_pct": float(max_cpu),
                "avg_memory_utilization_pct": float(avg_ram),
                "max_memory_utilization_pct": float(max_ram),
                "disk_read_iops": float(disk_read_iops),
                "disk_write_iops": float(disk_write_iops),
                "network_ingress_gb": float(network_ingress_gb),
                "network_egress_gb": float(network_egress_gb),
                "total_requests": int(total_requests),
                "is_idle": bool(is_idle),
                "pue_factor": float(pue),
                "grid_carbon_intensity_gco2_per_kwh": float(grid_intensity),
                "server_power_avg_watts": float(server_power_avg_watts),
                "energy_consumed_kwh": float(energy_kwh),
                "scope2_location_based_gco2e": float(scope2_co2),
                "scope3_embodied_gco2e": float(scope3_co2),
                "total_carbon_gco2e": float(total_co2),
                "anomaly_flag": bool(anomaly_flag),
                "anomaly_type": str(anomaly_type),
                "optimization_category": str(optimization_category),
            })

    df = pd.DataFrame(rows)
    assert len(df) == 50000, f"Expected exactly 50,000 rows, generated {len(df)}"
    return df
