"""
CloudSense AI — Anomaly Incident Specifications
Defines specific, realistic enterprise incidents injected into the dataset
with clear root causes, targeted resources, and physical/financial indicators.
"""

from typing import Dict, List, Any

# Incident catalog for controlled anomaly injection
INJECTED_INCIDENTS = [
    {
        "incident_id": "INC-001",
        "name": "Runaway Dev GKE Load-Test Cluster",
        "target_resource_id": "gke-qa-loadtest-pool",
        "start_day_offset": 45,   # Mid-October
        "duration_days": 4,       # Friday through Monday
        "anomaly_type": "runaway_dev_cluster",
        "root_cause": "QA team provisioned 20 c2-standard-16 nodes for weekend stress testing and omitted auto-shutdown.",
        "effects": {
            "provisioned_vcpu": 320,        # 20 nodes * 16 vCPU
            "provisioned_memory_gb": 1280,  # 20 nodes * 64 GB
            "avg_cpu_utilization_pct": 2.1, # Sat idle after 2-hour test
            "max_cpu_utilization_pct": 5.4,
            "cost_multiplier": 8.5,
            "runtime_hours": 24.0,
        }
    },
    {
        "incident_id": "INC-002",
        "name": "Unpartitioned BigQuery Full-Scan Spree",
        "target_resource_id": "bq-analytics-pipeline",
        "start_day_offset": 110,  # Mid-December
        "duration_days": 3,
        "anomaly_type": "unpartitioned_bigquery_scan",
        "root_cause": "Ad-hoc analytic query ran without WHERE partition_date filter against raw unpartitioned event logs.",
        "effects": {
            "usage_quantity_multiplier": 14.0, # Normal 15 TB -> 210 TB scanned/day
            "avg_cpu_utilization_pct": 85.0,
            "cost_multiplier": 14.0,
        }
    },
    {
        "incident_id": "INC-003",
        "name": "Cross-Continental Database Replication Egress Leak",
        "target_resource_id": "net-nat-gateway-us",
        "start_day_offset": 165,  # Mid-February
        "duration_days": 4,
        "anomaly_type": "egress_leak",
        "root_cause": "Misconfigured database dump replication sent full uncompressed database snapshots to asia-south1 instead of us-central1.",
        "effects": {
            "network_egress_gb_override": 4250.0, # Normal 35 GB -> 4,250 GB/day
            "cost_multiplier": 18.0,
        }
    },
    {
        "incident_id": "INC-004",
        "name": "Debug Logging Explosion in Standard Storage",
        "target_resource_id": "gcs-app-logs-raw",
        "start_day_offset": 82,   # Late November
        "duration_days": 5,
        "anomaly_type": "storage_log_explosion",
        "root_cause": "Production deployment set LOG_LEVEL=DEBUG with trace payloads, dumping 85 TB of verbose telemetry.",
        "effects": {
            "provisioned_storage_gb_multiplier": 6.5,
            "disk_write_iops_multiplier": 9.0,
            "cost_multiplier": 6.5,
        }
    },
    {
        "incident_id": "INC-005",
        "name": "DDoS Traffic Surge on Checkout API",
        "target_resource_id": "cr-checkout-api",
        "start_day_offset": 195,  # Mid-March
        "duration_days": 2,
        "anomaly_type": "cpu_spike_dos",
        "root_cause": "Volumetric layer-7 bot attack saturated serverless instances triggering maximum autoscaling concurrency.",
        "effects": {
            "total_requests_multiplier": 12.0,
            "avg_cpu_utilization_pct": 98.2,
            "max_cpu_utilization_pct": 100.0,
            "cost_multiplier": 7.8,
        }
    }
]
