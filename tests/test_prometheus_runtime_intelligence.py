from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from infra_assurance.prometheus_runtime_intelligence import (
    attach_prometheus_runtime,
    build_prometheus_runtime_intelligence,
)

NOW = datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc)


def workload_evidence():
    return {
        "schema_version": "0.1",
        "evidence_id": "ev-workload",
        "plane": "observed",
        "subject": {
            "system": "kubernetes",
            "cluster": "k3s-main",
            "api_group": "apps",
            "kind": "Deployment",
            "namespace": "app",
            "name": "web",
        },
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": "2026-08-15T10:00:00Z",
        "observed_at": "2026-08-15T10:00:00Z",
        "expires_at": "2026-08-15T10:05:00Z",
        "data": {
            "desired_replicas": 1,
            "ready_replicas": 1,
            "images": ["example/web:1"],
        },
        "provenance": {},
        "errors": [],
    }


def snapshot():
    return {
        "snapshot_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T10:00:00Z",
        "evidence": [workload_evidence()],
    }


def topology():
    return {
        "topology_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T10:00:00Z",
        "relations": [
            {
                "type": "SERVICE_SELECTOR_MATCHES_WORKLOAD",
                "source": "Service/app/web",
                "target": "Deployment/app/web",
                "basis": "SELECTOR_MATCH_INFERENCE",
                "evidence_ids": ["ev-service", "ev-workload"],
                "details": {"selector": {"app": "web"}},
            }
        ],
        "issues": [],
        "summary": {},
    }


def prometheus_success_runner(*, target_health="up", target_error="", alerts=None):
    alerts = alerts or []

    def runner(command, **kwargs):
        path = command[-1]
        if "api/v1/targets" in path:
            payload = {
                "status": "success",
                "data": {
                    "activeTargets": [
                        {
                            "scrapeUrl": "http://10.0.0.5:8080/metrics?token=do-not-persist",
                            "scrapePool": "serviceMonitor/app/web/0",
                            "health": target_health,
                            "lastError": target_error,
                            "lastScrape": "2026-08-15T09:59:50Z",
                            "lastScrapeDuration": 0.12,
                            "labels": {
                                "namespace": "app",
                                "service": "web",
                                "job": "web",
                                "endpoint": "metrics",
                                "pod": "web-abc",
                                "instance": "10.0.0.5:8080",
                                "password": "do-not-persist",
                            },
                            "discoveredLabels": {
                                "__meta_kubernetes_secret_name": "do-not-persist"
                            },
                        }
                    ],
                    "droppedTargets": [],
                },
            }
        elif "api/v1/alerts" in path:
            payload = {"status": "success", "data": {"alerts": alerts}}
        else:
            raise AssertionError(path)
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    return runner


def test_successful_runtime_target_and_alert_attribution_is_narrow_and_traceable():
    alerts = [
        {
            "state": "firing",
            "activeAt": "2026-08-15T09:58:00Z",
            "labels": {
                "alertname": "WebHighErrorRate",
                "severity": "warning",
                "namespace": "app",
                "service": "web",
                "instance": "10.0.0.5:8080",
                "password": "do-not-persist",
            },
            "annotations": {
                "summary": "secret-bearing free text must not be persisted"
            },
        }
    ]
    result = build_prometheus_runtime_intelligence(
        snapshot(),
        topology(),
        runner=prometheus_success_runner(alerts=alerts),
        now=NOW,
    )

    assert result["source"]["status"] == "COMPLETE"
    assert result["summary"]["targets_total"] == 1
    assert result["summary"]["targets_up"] == 1
    assert result["summary"]["active_alerts_firing"] == 1
    runtime = result["workload_runtime"][0]
    assert runtime["state"] == "ACTIVE_ALERT"
    assert runtime["targets"][0]["basis"] == [
        "PROMETHEUS_RUNTIME_TARGET_SERVICE_LABEL",
        "SERVICE_SELECTOR_MATCH_INFERENCE",
    ]
    assert runtime["active_alerts"][0]["basis"] == [
        "PROMETHEUS_ACTIVE_ALERT_SERVICE_LABEL",
        "SERVICE_SELECTOR_MATCH_INFERENCE",
    ]
    assert len(runtime["targets"][0]["evidence_ids"]) >= 2

    serialized = json.dumps(result)
    assert "scrapeUrl" not in serialized
    assert "discoveredLabels" not in serialized
    assert "annotations" not in serialized
    assert "10.0.0.5:8080" not in serialized
    assert "password" not in serialized
    assert "do-not-persist" not in serialized


def test_down_target_is_not_called_application_unhealthy_but_surfaces_target_down():
    result = build_prometheus_runtime_intelligence(
        snapshot(),
        topology(),
        runner=prometheus_success_runner(
            target_health="down",
            target_error="context deadline exceeded",
        ),
        now=NOW,
    )
    runtime = result["workload_runtime"][0]
    assert runtime["state"] == "PROMETHEUS_TARGET_DOWN"
    assert runtime["targets"][0]["error_code"] == "TARGET_TIMEOUT"


def test_no_target_match_is_scoped_not_unmonitored_claim():
    def runner(command, **kwargs):
        path = command[-1]
        data = {"activeTargets": [], "droppedTargets": []} if "targets" in path else {"alerts": []}
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps({"status": "success", "data": data}),
            "",
        )

    result = build_prometheus_runtime_intelligence(
        snapshot(), topology(), runner=runner, now=NOW
    )
    runtime = result["workload_runtime"][0]
    assert runtime["state"] == "NO_RUNTIME_SIGNAL_MATCH"
    assert any("does not prove absence" in caveat for caveat in runtime["caveats"])


def test_proxy_failure_produces_unknown_not_false_runtime_absence():
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            "",
            "Error from server (Forbidden): services/proxy is forbidden",
        )

    result = build_prometheus_runtime_intelligence(
        snapshot(), topology(), runner=runner, now=NOW
    )
    assert result["source"]["status"] == "FAILED_TO_OBSERVE"
    assert result["workload_runtime"][0]["state"] == "UNKNOWN"
    assert {item["scope"] for item in result["errors"]} == {"targets", "alerts"}


def test_partial_source_makes_workload_runtime_unknown():
    calls = 0

    def runner(command, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return subprocess.CompletedProcess(
                command,
                1,
                "",
                "Error from server (Forbidden): services/proxy is forbidden",
            )
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps({"status": "success", "data": {"alerts": []}}),
            "",
        )

    result = build_prometheus_runtime_intelligence(
        snapshot(), topology(), runner=runner, now=NOW
    )
    assert result["source"]["status"] == "PARTIAL"
    assert result["workload_runtime"][0]["state"] == "UNKNOWN"


def test_attach_prometheus_runtime_upgrades_inventory_without_mutation():
    runtime = build_prometheus_runtime_intelligence(
        snapshot(),
        topology(),
        runner=prometheus_success_runner(),
        now=NOW,
    )
    inventory = {
        "inventory_version": "0.2",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T10:00:00Z",
        "mutation_allowed": False,
        "scope": {},
        "summary": {},
        "namespace_counts": {"app": 1},
        "observability_source_status": "COMPLETE",
        "entities": [
            {
                "entity_id": "workload",
                "entity_type": "KUBERNETES_WORKLOAD",
                "subject": workload_evidence()["subject"],
                "observed": {},
                "declared": {},
                "relationships": {},
                "recent_change": {},
                "attention": [],
                "observability": {},
                "evidence_ids": ["ev-workload"],
            }
        ],
    }
    result = attach_prometheus_runtime(inventory, runtime)
    assert result["inventory_version"] == "0.3"
    assert result["mutation_allowed"] is False
    assert result["prometheus_runtime_source_status"] == "COMPLETE"
    assert result["entities"][0]["runtime_observability"]["state"] == "PROMETHEUS_TARGETS_UP"
    assert runtime["targets"][0]["evidence_id"] in result["entities"][0]["evidence_ids"]


def test_runtime_artifact_matches_schema():
    result = build_prometheus_runtime_intelligence(
        snapshot(),
        topology(),
        runner=prometheus_success_runner(),
        now=NOW,
    )
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "prometheus-runtime-intelligence.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(result)
