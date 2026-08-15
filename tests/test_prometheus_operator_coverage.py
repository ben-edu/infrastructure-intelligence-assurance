from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from infra_assurance.prometheus_operator_coverage import (
    attach_observability_coverage,
    build_prometheus_operator_coverage,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc)


def _workload() -> dict:
    return {
        "schema_version": "0.1",
        "evidence_id": "ev-workload",
        "plane": "observed",
        "subject": {
            "system": "kubernetes",
            "cluster": "k3s-main",
            "api_group": "apps",
            "kind": "Deployment",
            "namespace": "validation",
            "name": "demo",
        },
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": "2026-08-15T09:00:00Z",
        "observed_at": "2026-08-15T09:00:00Z",
        "expires_at": "2026-08-15T09:05:00Z",
        "data": {
            "desired_replicas": 1,
            "ready_replicas": 1,
            "images": ["example.invalid/demo:1"],
            "pod_labels": {"app": "demo", "tier": "backend"},
        },
        "provenance": {},
        "errors": [],
    }


def _snapshot() -> dict:
    return {
        "snapshot_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T09:00:00Z",
        "evidence": [_workload()],
    }


def _topology() -> dict:
    return {
        "topology_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T09:00:00Z",
        "summary": {},
        "relations": [
            {
                "type": "SERVICE_SELECTOR_MATCHES_WORKLOAD",
                "source": "Service/validation/demo",
                "target": "Deployment/validation/demo",
                "basis": "SELECTOR_MATCH_INFERENCE",
                "evidence_ids": ["ev-service", "ev-workload"],
                "details": {"selector": {"app": "demo"}},
            }
        ],
        "issues": [],
    }


def _base_objects() -> dict[str, list[dict]]:
    return {
        "namespaces": [
            {"metadata": {"name": "monitoring", "labels": {"team": "platform"}}},
            {"metadata": {"name": "validation", "labels": {"team": "apps"}}},
        ],
        "services": [
            {
                "metadata": {
                    "namespace": "validation",
                    "name": "demo",
                    "labels": {"app": "demo", "metrics": "enabled"},
                }
            }
        ],
        "prometheuses.monitoring.coreos.com": [
            {
                "metadata": {
                    "namespace": "monitoring",
                    "name": "main",
                    "labels": {"app": "prometheus"},
                },
                "spec": {
                    "serviceMonitorSelector": {"matchLabels": {"release": "stack"}},
                    "serviceMonitorNamespaceSelector": {},
                    "podMonitorSelector": {"matchLabels": {"release": "stack"}},
                    "podMonitorNamespaceSelector": {},
                },
            }
        ],
        "servicemonitors.monitoring.coreos.com": [
            {
                "metadata": {
                    "namespace": "validation",
                    "name": "demo",
                    "labels": {"release": "stack"},
                },
                "spec": {
                    "selector": {"matchLabels": {"app": "demo"}},
                    "endpoints": [
                        {
                            "port": "metrics",
                            "path": "/metrics",
                            "interval": "30s",
                            "bearerTokenFile": "/var/run/secrets/token",
                            "basicAuth": {
                                "username": {"name": "secret", "key": "username"},
                                "password": {"name": "secret", "key": "password"},
                            },
                            "tlsConfig": {"insecureSkipVerify": True},
                        }
                    ],
                },
            }
        ],
        "podmonitors.monitoring.coreos.com": [],
    }


def _runner(objects: dict[str, list[dict]], failures: dict[str, str] | None = None):
    failures = failures or {}

    def run(command, **_kwargs):
        resource = command[2]
        if resource in failures:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr=failures[resource])
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"items": objects.get(resource, [])}),
            stderr="",
        )

    return run


def _minimal_inventory() -> dict:
    return {
        "inventory_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T09:00:00Z",
        "mutation_allowed": False,
        "scope": {
            "entity_type": "KUBERNETES_WORKLOAD",
            "workload_kinds": ["DaemonSet", "Deployment", "StatefulSet"],
        },
        "summary": {
            "workloads_total": 1,
            "namespaces_total": 1,
            "declared_workloads": 0,
            "workloads_in_sync": 0,
            "workloads_outside_declared_scope": 1,
            "workloads_with_attention": 0,
            "workloads_changed_in_latest_diff": 0,
            "service_links": 1,
            "ingress_route_candidates": 0,
            "pvc_links": 0,
            "related_drift_subjects": 0,
        },
        "namespace_counts": {"validation": 1},
        "entities": [
            {
                "entity_id": "kubernetes:k3s-main:apps:Deployment:validation:demo",
                "entity_type": "KUBERNETES_WORKLOAD",
                "subject": _workload()["subject"],
                "observed": {
                    "existence": "PRESENT",
                    "observation_status": "COMPLETE",
                    "freshness": "CURRENT",
                    "observed_at": "2026-08-15T09:00:00Z",
                    "expires_at": "2026-08-15T09:05:00Z",
                    "evidence_id": "ev-workload",
                    "attributes": {"desired_replicas": 1, "ready_replicas": 1, "images": ["example.invalid/demo:1"]},
                },
                "declared": {
                    "coverage": "OUTSIDE_DECLARED_SCOPE",
                    "comparison": None,
                    "evidence_id": None,
                    "source_id": None,
                    "revision": None,
                },
                "relationships": {
                    "services": [
                        {
                            "subject": "Service/validation/demo",
                            "basis": "SELECTOR_MATCH_INFERENCE",
                            "evidence_ids": ["ev-service", "ev-workload"],
                        }
                    ],
                    "ingress_route_candidates": [],
                    "persistent_volume_claims": [],
                },
                "recent_change": {"state": "UNCHANGED", "items": []},
                "attention": [],
                "evidence_ids": ["ev-workload"],
            }
        ],
    }


def test_service_monitor_chain_is_configuration_match_not_health_claim():
    coverage = build_prometheus_operator_coverage(
        _snapshot(),
        _topology(),
        runner=_runner(_base_objects()),
        now=NOW,
    )

    assert coverage["source_status"] == "COMPLETE"
    assert coverage["summary"]["prometheus_instances"] == 1
    assert coverage["summary"]["selected_service_monitors"] == 1
    item = coverage["workload_coverage"][0]
    assert item["status"] == "OPERATOR_MONITOR_MATCH"
    assert item["scope_completeness"] == "COMPLETE"
    assert len(item["service_monitor_paths"]) == 1
    assert item["service_monitor_paths"][0]["basis"] == [
        "PROMETHEUS_MONITOR_SELECTION_INFERENCE",
        "SERVICEMONITOR_SERVICE_SELECTOR_INFERENCE",
        "SERVICE_SELECTOR_MATCH_INFERENCE",
    ]
    assert "scrape target health" in item["caveats"][0].lower()


def test_pod_monitor_matches_workload_template_labels_as_inference():
    objects = _base_objects()
    objects["servicemonitors.monitoring.coreos.com"] = []
    objects["podmonitors.monitoring.coreos.com"] = [
        {
            "metadata": {
                "namespace": "validation",
                "name": "demo-pods",
                "labels": {"release": "stack"},
            },
            "spec": {
                "selector": {
                    "matchLabels": {"app": "demo"},
                    "matchExpressions": [
                        {"key": "tier", "operator": "In", "values": ["backend"]}
                    ],
                },
                "podMetricsEndpoints": [{"port": "metrics", "path": "/metrics"}],
            },
        }
    ]

    coverage = build_prometheus_operator_coverage(
        _snapshot(),
        _topology(),
        runner=_runner(objects),
        now=NOW,
    )
    item = coverage["workload_coverage"][0]
    assert item["status"] == "OPERATOR_MONITOR_MATCH"
    assert item["service_monitor_paths"] == []
    assert item["pod_monitor_paths"][0]["basis"] == [
        "PROMETHEUS_MONITOR_SELECTION_INFERENCE",
        "PODMONITOR_TEMPLATE_LABEL_INFERENCE",
    ]


def test_null_prometheus_resource_selector_selects_no_monitors():
    objects = _base_objects()
    objects["prometheuses.monitoring.coreos.com"][0]["spec"].pop("serviceMonitorSelector")

    coverage = build_prometheus_operator_coverage(
        _snapshot(),
        _topology(),
        runner=_runner(objects),
        now=NOW,
    )
    assert coverage["summary"]["selected_service_monitors"] == 0
    assert coverage["workload_coverage"][0]["status"] == "NO_OPERATOR_MONITOR_MATCH"


def test_prometheus_namespace_selector_uses_namespace_labels():
    objects = _base_objects()
    objects["prometheuses.monitoring.coreos.com"][0]["spec"]["serviceMonitorNamespaceSelector"] = {
        "matchLabels": {"team": "apps"}
    }

    coverage = build_prometheus_operator_coverage(
        _snapshot(),
        _topology(),
        runner=_runner(objects),
        now=NOW,
    )
    assert coverage["summary"]["selected_service_monitors"] == 1
    assert coverage["workload_coverage"][0]["status"] == "OPERATOR_MONITOR_MATCH"


def test_failed_monitor_collection_does_not_become_no_monitor_claim():
    objects = _base_objects()
    objects["podmonitors.monitoring.coreos.com"] = []
    coverage = build_prometheus_operator_coverage(
        _snapshot(),
        _topology(),
        runner=_runner(
            objects,
            failures={"servicemonitors.monitoring.coreos.com": "Error from server (Forbidden): forbidden"},
        ),
        now=NOW,
    )
    item = coverage["workload_coverage"][0]
    assert coverage["source_status"] == "PARTIAL"
    assert item["status"] == "UNKNOWN"
    assert item["scope_completeness"] == "PARTIAL"
    assert any(error["code"] == "KUBERNETES_FORBIDDEN" for error in coverage["errors"])


def test_sensitive_endpoint_auth_fields_are_not_projected():
    coverage = build_prometheus_operator_coverage(
        _snapshot(),
        _topology(),
        runner=_runner(_base_objects()),
        now=NOW,
    )
    serialized = json.dumps(coverage)
    for forbidden in (
        "bearerTokenFile",
        "basicAuth",
        "password",
        "tlsConfig",
        "authorization",
        "oauth2",
    ):
        assert forbidden not in serialized


def test_coverage_and_enriched_inventory_validate_against_schemas():
    coverage = build_prometheus_operator_coverage(
        _snapshot(),
        _topology(),
        runner=_runner(_base_objects()),
        now=NOW,
    )
    enriched = attach_observability_coverage(_minimal_inventory(), coverage)

    coverage_schema = json.loads(
        (ROOT / "schemas" / "prometheus-operator-coverage.schema.json").read_text(encoding="utf-8")
    )
    inventory_schema = json.loads(
        (ROOT / "schemas" / "workload-operational-inventory.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(coverage_schema).validate(coverage)
    Draft202012Validator(inventory_schema).validate(enriched)

    assert enriched["inventory_version"] == "0.2"
    assert enriched["observability_source_status"] == "COMPLETE"
    assert enriched["entities"][0]["observability"]["status"] == "OPERATOR_MONITOR_MATCH"
    assert enriched["summary"]["workloads_with_operator_monitor_match"] == 1
