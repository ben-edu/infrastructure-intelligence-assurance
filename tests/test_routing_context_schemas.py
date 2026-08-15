from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def test_workload_routing_extension_schema_accepts_sanitized_projection():
    artifact = {
        "inventory_version": "0.4",
        "cluster_id": "k3s-main",
        "mutation_allowed": False,
        "routing_ownership_source_status": "COMPLETE",
        "routing_ownership_generated_at": "2026-08-15T12:00:00Z",
        "routing_service_states": [
            {
                "service": "Service/monitoring/loki-headless",
                "state": "RESOLVED_WORKLOAD_ROUTING",
                "scope_completeness": "COMPLETE",
                "resolved_workloads": [
                    {
                        "subject": "StatefulSet/monitoring/loki",
                        "pod_targets": 1,
                        "basis": ["ENDPOINT_TARGET_REF", "POD_CONTROLLER_OWNER_REFERENCE"],
                        "evidence_ids": ["route-1"],
                    },
                    {
                        "subject": "DaemonSet/monitoring/loki-canary",
                        "pod_targets": 3,
                        "basis": ["ENDPOINT_TARGET_REF", "POD_CONTROLLER_OWNER_REFERENCE"],
                        "evidence_ids": ["route-2"],
                    },
                ],
                "evidence_ids": ["route-1", "route-2"],
            }
        ],
        "routing_ownership_unknowns": [],
        "summary": {
            "routing_service_links": 2,
            "workloads_with_routing_service": 2,
            "routing_services_resolved": 1,
            "routing_services_non_pod": 0,
            "routing_services_unknown_or_partial": 0,
            "routing_workloads_not_in_inventory": 0,
        },
        "entities": [
            {
                "subject": {"kind": "StatefulSet"},
                "relationships": {
                    "services": [],
                    "routing_services": [
                        {
                            "subject": "Service/monitoring/loki-headless",
                            "state": "RESOLVED_WORKLOAD_ROUTING",
                            "scope_completeness": "COMPLETE",
                            "pod_targets": 1,
                            "basis": ["ENDPOINT_TARGET_REF"],
                            "evidence_ids": ["route-1"],
                        }
                    ],
                },
                "evidence_ids": ["route-1"],
            }
        ],
    }
    schema = json.loads(
        (ROOT / "schemas" / "workload-routing-integration.schema.json").read_text()
    )
    jsonschema.Draft202012Validator(schema).validate(artifact)


def test_incident_routing_extension_schema_accepts_non_pod_no_claim():
    artifact = {
        "incident_candidates_version": "0.2",
        "cluster_id": "k3s-main",
        "mutation_allowed": False,
        "source_status": {"routing_ownership": "COMPLETE"},
        "summary": {
            "service_candidates_with_preferred_routing": 0,
            "service_candidates_without_workload_routing_claim": 1,
        },
        "candidates": [
            {
                "scope": {
                    "type": "SERVICE",
                    "subject": "Service/kube-system/kube-prom-stack-kubelet",
                },
                "impact_context": {
                    "service_routing": {
                        "source_status": "COMPLETE",
                        "service": "Service/kube-system/kube-prom-stack-kubelet",
                        "state": "NON_POD_ROUTING",
                        "scope_completeness": "COMPLETE",
                        "selection": "NO_WORKLOAD_ROUTING_CLAIM",
                        "resolved_workloads": [],
                        "evidence_ids": ["route-node"],
                    }
                },
            }
        ],
    }
    schema = json.loads(
        (ROOT / "schemas" / "incident-routing-integration.schema.json").read_text()
    )
    jsonschema.Draft202012Validator(schema).validate(artifact)
