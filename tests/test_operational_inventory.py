from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from infra_assurance.operational_inventory import build_operational_inventory

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc)


def subject(kind: str, namespace: str, name: str, api_group: str = "apps") -> dict:
    return {
        "system": "kubernetes",
        "cluster": "k3s-main",
        "api_group": api_group,
        "kind": kind,
        "namespace": namespace,
        "name": name,
    }


def envelope(kind: str, namespace: str, name: str, data: dict, evidence_id: str, api_group: str = "apps") -> dict:
    return {
        "schema_version": "0.1",
        "evidence_id": evidence_id,
        "plane": "observed",
        "subject": subject(kind, namespace, name, api_group),
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": "2026-08-15T09:59:00Z",
        "observed_at": "2026-08-15T09:59:00Z",
        "expires_at": "2026-08-15T10:10:00Z",
        "data": data,
        "provenance": {
            "source_type": "kubernetes_api",
            "source_id": "k3s-main",
            "collector": "test",
            "collector_version": "0.1",
            "operation": "list",
        },
        "errors": [],
    }


def declared_workload() -> dict:
    return {
        "schema_version": "0.1",
        "evidence_id": "ev-declared-workload",
        "plane": "declared",
        "subject": subject("Deployment", "validation", "nginx-validation"),
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": "2026-08-15T09:59:00Z",
        "observed_at": "2026-08-15T09:59:00Z",
        "expires_at": "2026-08-15T10:15:00Z",
        "data": {"desired_replicas": 1, "images": ["nginx:stable"]},
        "provenance": {
            "source_type": "git",
            "source_id": "github.com/ben-edu/api-cluster-infra",
            "collector": "git-declared-observer",
            "collector_version": "0.1.0",
            "operation": "read kubernetes/validation/nginx/nginx-validation.yaml#document=2",
            "revision": "abc123",
        },
        "errors": [],
    }


def base_inputs():
    workload = envelope(
        "Deployment",
        "validation",
        "nginx-validation",
        {
            "desired_replicas": 1,
            "ready_replicas": 1,
            "images": ["nginx:stable"],
            "pod_labels": {"app": "nginx-validation"},
            "env": {"PASSWORD": "must-not-project"},
            "secret_payload": "must-not-project",
        },
        "ev-workload",
    )
    snapshot = {
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T09:59:00Z",
        "evidence": [workload],
    }
    topology = {
        "topology_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T09:59:00Z",
        "summary": {},
        "relations": [
            {
                "type": "SERVICE_SELECTOR_MATCHES_WORKLOAD",
                "source": "Service/validation/nginx-validation",
                "target": "Deployment/validation/nginx-validation",
                "basis": "SELECTOR_MATCH_INFERENCE",
                "evidence_ids": ["ev-service", "ev-workload"],
                "details": {"selector": {"app": "nginx-validation"}},
            },
            {
                "type": "INGRESS_REFERENCES_SERVICE",
                "source": "Ingress/validation/nginx-validation",
                "target": "Service/validation/nginx-validation",
                "basis": "OBSERVED_REFERENCE",
                "evidence_ids": ["ev-ingress", "ev-service"],
                "details": {
                    "host": "k3s-master.behnam.fr",
                    "path": "/",
                    "service_port": 80,
                },
            },
            {
                "type": "WORKLOAD_REFERENCES_PVC",
                "source": "Deployment/validation/nginx-validation",
                "target": "PersistentVolumeClaim/validation/nginx-data",
                "basis": "OBSERVED_REFERENCE",
                "evidence_ids": ["ev-workload", "ev-pvc"],
            },
        ],
        "issues": [],
    }
    diff = {
        "diff_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T10:00:00Z",
        "baseline": False,
        "changes": [],
        "unknowns": [],
    }
    drift = {
        "drift_version": "0.2",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T10:00:00Z",
        "status": "EVALUATED",
        "results": [
            {
                "classification": "IN_SYNC",
                "subject": "Deployment/validation/nginx-validation",
                "evidence_ids": ["ev-declared-workload", "ev-workload"],
                "field_mismatches": [],
                "unknown_fields": [],
                "declared_revision": "abc123",
                "declared_source": "github.com/ben-edu/api-cluster-infra",
            },
            {
                "classification": "DRIFT",
                "subject": "Ingress/validation/nginx-validation",
                "evidence_ids": ["ev-declared-ingress", "ev-ingress"],
                "field_mismatches": [
                    {
                        "field": "backends",
                        "declared": [{"host": "k3s-master.soria-academie.fr"}],
                        "observed": [{"host": "k3s-master.behnam.fr"}],
                    }
                ],
                "unknown_fields": [],
                "declared_revision": "abc123",
                "declared_source": "github.com/ben-edu/api-cluster-infra",
            },
        ],
        "unknowns": [],
    }
    declared_load = {
        "status": "AVAILABLE",
        "records": [declared_workload()],
        "errors": [],
    }
    return snapshot, topology, diff, drift, declared_load


def test_inventory_composes_workload_context_without_promoting_inferences_to_facts():
    snapshot, topology, diff, drift, declared_load = base_inputs()
    inventory = build_operational_inventory(
        snapshot, topology, diff, drift, declared_load, now=NOW
    )

    entity = inventory["entities"][0]
    assert entity["declared"]["comparison"] == "IN_SYNC"
    assert entity["observed"]["freshness"] == "CURRENT"
    assert entity["observed"]["attributes"] == {
        "desired_replicas": 1,
        "ready_replicas": 1,
        "images": ["nginx:stable"],
    }
    assert entity["relationships"]["services"][0]["basis"] == "SELECTOR_MATCH_INFERENCE"
    route = entity["relationships"]["ingress_route_candidates"][0]
    assert route["basis"] == "COMPOSED_INFERENCE"
    assert route["subject"] == "Ingress/validation/nginx-validation"
    assert entity["relationships"]["persistent_volume_claims"][0]["basis"] == "OBSERVED_REFERENCE"
    assert any(
        item["source"] == "drift"
        and item["subject"] == "Ingress/validation/nginx-validation"
        for item in entity["attention"]
    )
    assert inventory["summary"]["related_drift_subjects"] == 1


def test_observed_projection_excludes_unmodeled_sensitive_values():
    snapshot, topology, diff, drift, declared_load = base_inputs()
    inventory = build_operational_inventory(
        snapshot, topology, diff, drift, declared_load, now=NOW
    )
    serialized = json.dumps(inventory)
    assert "must-not-project" not in serialized
    assert "secret_payload" not in serialized
    assert '"env"' not in serialized


def test_topology_ambiguity_is_related_attention_not_observed_fact():
    snapshot, topology, diff, drift, declared_load = base_inputs()
    topology["issues"].append(
        {
            "code": "SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES",
            "severity": "AMBIGUOUS",
            "subject": "Service/validation/nginx-validation",
            "statement": "Service selector matched two controllers.",
            "evidence_ids": ["ev-service", "ev-workload", "ev-other"],
            "required_live_verification": "Inspect EndpointSlices and Pod ownership.",
        }
    )
    inventory = build_operational_inventory(
        snapshot, topology, diff, drift, declared_load, now=NOW
    )
    entity = inventory["entities"][0]
    issue = next(item for item in entity["attention"] if item["source"] == "topology")
    assert issue["severity"] == "AMBIGUOUS"
    assert entity["observed"]["attributes"]["ready_replicas"] == 1


def test_absence_from_complete_declared_scope_is_not_drift():
    snapshot, topology, diff, drift, declared_load = base_inputs()
    declared_load["records"] = []
    drift["results"] = []
    inventory = build_operational_inventory(
        snapshot, topology, diff, drift, declared_load, now=NOW
    )
    entity = inventory["entities"][0]
    assert entity["declared"]["coverage"] == "OUTSIDE_DECLARED_SCOPE"
    assert entity["declared"]["comparison"] is None
    assert not any(item["source"] == "drift" for item in entity["attention"])


def test_partial_declared_source_does_not_claim_outside_scope():
    snapshot, topology, diff, drift, declared_load = base_inputs()
    declared_load["status"] = "AVAILABLE_PARTIAL"
    declared_load["records"] = []
    drift["results"] = []
    inventory = build_operational_inventory(
        snapshot, topology, diff, drift, declared_load, now=NOW
    )
    assert inventory["entities"][0]["declared"]["coverage"] == "DECLARED_COVERAGE_INCOMPLETE"


def test_unsafe_latest_collection_makes_workload_change_unknown():
    snapshot, topology, diff, drift, declared_load = base_inputs()
    diff["unknowns"] = [
        {
            "code": "CURRENT_COLLECTION_FAILED",
            "api_group": "apps",
            "resource_kind": "Deployment",
            "statement": "Deployment membership cannot be compared safely.",
            "evidence_ids": ["ev-deployment-collection"],
        }
    ]
    inventory = build_operational_inventory(
        snapshot, topology, diff, drift, declared_load, now=NOW
    )
    entity = inventory["entities"][0]
    assert entity["recent_change"]["state"] == "UNKNOWN"
    assert any(item["code"] == "LATEST_CHANGE_UNKNOWN" for item in entity["attention"])


def test_inventory_validates_against_schema():
    snapshot, topology, diff, drift, declared_load = base_inputs()
    inventory = build_operational_inventory(
        snapshot, topology, diff, drift, declared_load, now=NOW
    )
    schema = json.loads(
        (ROOT / "schemas" / "workload-operational-inventory.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(inventory)
