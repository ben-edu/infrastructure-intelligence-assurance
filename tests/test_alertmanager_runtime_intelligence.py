from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from infra_assurance.alertmanager_runtime_intelligence import (
    build_alert_attention,
    build_alertmanager_runtime_intelligence,
)

NOW = datetime(2026, 8, 15, 10, 30, tzinfo=timezone.utc)


def prometheus_runtime(alerts=None, workload_alerts=None):
    return {
        "prometheus_runtime_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T10:30:00Z",
        "mutation_allowed": False,
        "source": {"status": "COMPLETE"},
        "active_alerts": alerts or [],
        "workload_runtime": workload_alerts or [],
    }


def success_runner(alerts, silences):
    def runner(command, **kwargs):
        path = command[-1]
        if "api/v2/alerts" in path:
            payload = alerts
        elif "api/v2/silences" in path:
            payload = silences
        else:
            raise AssertionError(path)
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    return runner


def test_alertmanager_projection_is_narrow_and_unique_prometheus_match_is_traceable():
    prom_alert = {
        "alert_id": "prom-alert-1",
        "evidence_id": "ev-prom-1",
        "state": "FIRING",
        "active_at": "2026-08-15T10:00:00Z",
        "labels": {
            "alertname": "KubeletDown",
            "severity": "warning",
            "namespace": "monitoring",
            "service": "kube-prom-stack-kubelet",
            "job": "kubelet",
        },
    }
    alerts = [
        {
            "fingerprint": "abc123",
            "startsAt": "2026-08-15T10:00:00Z",
            "updatedAt": "2026-08-15T10:29:00Z",
            "endsAt": "2026-08-15T11:00:00Z",
            "labels": {
                "alertname": "KubeletDown",
                "severity": "warning",
                "namespace": "monitoring",
                "service": "kube-prom-stack-kubelet",
                "job": "kubelet",
                "node": "worker-01",
                "instance": "10.42.1.22:10250",
                "password": "do-not-persist",
            },
            "annotations": {"summary": "free text must not persist"},
            "receivers": [{"name": "secret-receiver-name"}],
            "generatorURL": "http://sensitive.example/query",
            "status": {
                "state": "active",
                "silencedBy": [],
                "inhibitedBy": [],
                "mutedBy": [],
            },
        }
    ]
    result = build_alertmanager_runtime_intelligence(
        prometheus_runtime(alerts=[prom_alert]),
        runner=success_runner(alerts, []),
        now=NOW,
    )

    assert result["source"]["status"] == "COMPLETE"
    assert result["summary"]["alerts_total"] == 1
    assert result["summary"]["prometheus_correlations_matched"] == 1
    record = result["alerts"][0]
    assert record["prometheus_correlation"]["prometheus_alert_id"] == "prom-alert-1"
    assert record["labels"]["node"] == "worker-01"

    serialized = json.dumps(result)
    for forbidden in (
        "annotations",
        "receivers",
        "generatorURL",
        "secret-receiver-name",
        "10.42.1.22:10250",
        "password",
        "do-not-persist",
        "sensitive.example",
    ):
        assert forbidden not in serialized


def test_silenced_and_inhibited_alert_keeps_handling_state_without_free_form_silence_data():
    alerts = [
        {
            "fingerprint": "fp-1",
            "labels": {"alertname": "DiskFull", "severity": "critical", "namespace": "app"},
            "status": {
                "state": "suppressed",
                "silencedBy": ["silence-uuid"],
                "inhibitedBy": ["source-fingerprint"],
                "mutedBy": [],
            },
        }
    ]
    silences = [
        {
            "id": "silence-uuid",
            "status": {"state": "active"},
            "startsAt": "2026-08-15T10:00:00Z",
            "endsAt": "2026-08-15T12:00:00Z",
            "updatedAt": "2026-08-15T10:01:00Z",
            "createdBy": "do-not-persist",
            "comment": "do-not-persist",
            "matchers": [{"name": "password", "value": "do-not-persist"}],
        }
    ]
    result = build_alertmanager_runtime_intelligence(
        prometheus_runtime(), runner=success_runner(alerts, silences), now=NOW
    )
    record = result["alerts"][0]
    assert record["handling_state"] == "SILENCED_AND_INHIBITED"
    assert record["silenced_by_count"] == 1
    assert record["inhibited_by_count"] == 1
    assert result["silences"][0]["state"] == "ACTIVE"
    serialized = json.dumps(result)
    assert "createdBy" not in serialized
    assert "comment" not in serialized
    assert "matchers" not in serialized
    assert "do-not-persist" not in serialized


def test_ambiguous_prometheus_correlation_is_not_forced():
    labels = {"alertname": "SameAlert", "severity": "warning"}
    prom = prometheus_runtime(
        alerts=[
            {"alert_id": "p1", "evidence_id": "e1", "labels": labels},
            {"alert_id": "p2", "evidence_id": "e2", "labels": labels},
        ]
    )
    alerts = [
        {
            "fingerprint": "am1",
            "labels": labels,
            "status": {"state": "active", "silencedBy": [], "inhibitedBy": [], "mutedBy": []},
        }
    ]
    result = build_alertmanager_runtime_intelligence(
        prom, runner=success_runner(alerts, []), now=NOW
    )
    correlation = result["alerts"][0]["prometheus_correlation"]
    assert correlation["status"] == "AMBIGUOUS"
    assert correlation["prometheus_alert_id"] is None
    assert any(x["code"] == "ALERTMANAGER_PROMETHEUS_CORRELATION_AMBIGUOUS" for x in result["unknowns"])


def test_alert_attention_retains_node_scope_when_workload_ownership_is_unsupported():
    prom_alert = {
        "alert_id": "prom-alert-node",
        "evidence_id": "ev-prom-node",
        "labels": {"alertname": "KubeletDown", "severity": "warning", "job": "kubelet"},
    }
    alerts = [
        {
            "fingerprint": "am-node",
            "labels": {"alertname": "KubeletDown", "severity": "warning", "job": "kubelet", "node": "worker-02"},
            "status": {"state": "active", "silencedBy": [], "inhibitedBy": [], "mutedBy": []},
        }
    ]
    prom = prometheus_runtime(alerts=[prom_alert])
    runtime = build_alertmanager_runtime_intelligence(
        prom, runner=success_runner(alerts, []), now=NOW
    )
    attention = build_alert_attention(prom, runtime)
    item = attention["attention"][0]
    assert item["scope"]["type"] == "NODE"
    assert item["scope"]["subject"] == "Node/worker-02"
    assert attention["mutation_allowed"] is False


def test_both_proxy_failures_are_failed_to_observe_not_zero_fact():
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(
            command, 1, "", "Error from server (Forbidden): services/proxy is forbidden"
        )

    result = build_alertmanager_runtime_intelligence(
        prometheus_runtime(), runner=runner, now=NOW
    )
    assert result["source"]["status"] == "FAILED_TO_OBSERVE"
    assert {x["scope"] for x in result["errors"]} == {"alerts", "silences"}


def test_alertmanager_and_attention_artifacts_match_schemas():
    alerts = [
        {
            "fingerprint": "fp-schema",
            "labels": {"alertname": "TestAlert", "severity": "warning", "namespace": "test"},
            "status": {"state": "active", "silencedBy": [], "inhibitedBy": [], "mutedBy": []},
        }
    ]
    prom = prometheus_runtime()
    runtime = build_alertmanager_runtime_intelligence(
        prom, runner=success_runner(alerts, []), now=NOW
    )
    attention = build_alert_attention(prom, runtime)
    root = Path(__file__).resolve().parents[1]
    runtime_schema = json.loads((root / "schemas" / "alertmanager-runtime-intelligence.schema.json").read_text())
    attention_schema = json.loads((root / "schemas" / "alert-attention.schema.json").read_text())
    jsonschema.Draft202012Validator(runtime_schema).validate(runtime)
    jsonschema.Draft202012Validator(attention_schema).validate(attention)
