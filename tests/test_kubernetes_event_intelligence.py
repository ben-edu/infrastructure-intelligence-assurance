from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from infra_assurance.kubernetes_event_intelligence import (
    build_event_correlation,
    build_kubernetes_event_runtime,
)

NOW = datetime(2026, 8, 15, 11, 0, tzinfo=timezone.utc)


def _event(*, name, namespace, kind, reason, event_type="Warning", last="2026-08-15T10:55:00Z", count=1):
    return {
        "metadata": {
            "name": f"event-{name}-{reason}",
            "uid": f"uid-{name}-{reason}",
            "creationTimestamp": last,
        },
        "type": event_type,
        "reason": reason,
        "message": "password=do-not-persist https://secret.example.invalid/token",
        "source": {"component": "kubelet", "host": "10.0.0.99"},
        "involvedObject": {
            "apiVersion": "v1",
            "kind": kind,
            "namespace": namespace,
            "name": name,
            "uid": "object-uid-do-not-persist",
        },
        "firstTimestamp": last,
        "lastTimestamp": last,
        "count": count,
    }


def _runner(items):
    def runner(command, **kwargs):
        assert command[-5:] == ["events", "--all-namespaces", "-o", "json"] or "events" in command
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps({"apiVersion": "v1", "kind": "EventList", "items": items}),
            "",
        )

    return runner


def _attention(*records):
    return {
        "alert_attention_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T11:00:00Z",
        "mutation_allowed": False,
        "source_status": {"prometheus": "COMPLETE", "alertmanager": "COMPLETE"},
        "summary": {},
        "attention": list(records),
        "unknowns": [],
        "caveats": [],
    }


def _attention_record(attention_id, scope_type, subject, handling="ACTIVE"):
    return {
        "attention_id": attention_id,
        "alertmanager_alert_id": f"am-{attention_id}",
        "prometheus_alert_id": f"prom-{attention_id}",
        "correlation_status": "MATCHED",
        "state": "ACTIVE",
        "handling_state": handling,
        "labels": {},
        "scope": {
            "type": scope_type,
            "subject": subject,
            "basis": ["TEST_SCOPE"],
        },
        "starts_at": None,
        "updated_at": None,
        "ends_at": None,
        "silence_refs": [],
        "evidence_ids": [f"ev-attention-{attention_id}"],
    }


def test_event_runtime_is_recent_bounded_and_excludes_message_and_source_host():
    result = build_kubernetes_event_runtime(
        cluster_id="k3s-main",
        runner=_runner(
            [
                _event(
                    name="kube-prom-stack-kubelet",
                    namespace="monitoring",
                    kind="Service",
                    reason="BackOff",
                    count=4,
                ),
                _event(
                    name="old-pod",
                    namespace="monitoring",
                    kind="Pod",
                    reason="Pulled",
                    event_type="Normal",
                    last="2026-08-15T08:00:00Z",
                ),
            ]
        ),
        now=NOW,
    )

    assert result["source"]["status"] == "COMPLETE"
    assert result["summary"]["events_seen_from_api"] == 2
    assert result["summary"]["events_recent"] == 1
    assert result["summary"]["events_warning"] == 1
    event = result["events"][0]
    assert event["subject"] == "Service/monitoring/kube-prom-stack-kubelet"
    assert event["reason"] == "BackOff"
    assert event["count"] == 4

    serialized = json.dumps(result)
    assert "message" not in serialized
    assert "source" not in event
    assert "10.0.0.99" not in serialized
    assert "object-uid-do-not-persist" not in serialized
    assert "do-not-persist" not in serialized
    assert "http://" not in serialized
    assert "https://" not in serialized


def test_service_attention_gets_direct_warning_event_without_root_cause_claim():
    runtime = build_kubernetes_event_runtime(
        cluster_id="k3s-main",
        runner=_runner(
            [
                _event(
                    name="kube-prom-stack-kubelet",
                    namespace="monitoring",
                    kind="Service",
                    reason="FailedDiscoveryCheck",
                )
            ]
        ),
        now=NOW,
    )
    attention = _attention(
        _attention_record(
            "a1",
            "SERVICE",
            "Service/monitoring/kube-prom-stack-kubelet",
            "INHIBITED",
        )
    )
    result = build_event_correlation(runtime, attention)
    record = result["correlations"][0]
    assert record["correlation_status"] == "MATCHED"
    assert record["related_warning_events"][0]["basis"] == [
        "DIRECT_OBJECT_IDENTITY",
        "RECENT_KUBERNETES_WARNING_EVENT",
    ]
    assert any("not a root-cause conclusion" in item for item in result["caveats"])


def test_namespace_attention_can_use_namespace_membership_but_platform_is_not_broadly_matched():
    runtime = build_kubernetes_event_runtime(
        cluster_id="k3s-main",
        runner=_runner(
            [
                _event(
                    name="some-pod",
                    namespace="moodle",
                    kind="Pod",
                    reason="FailedMount",
                )
            ]
        ),
        now=NOW,
    )
    attention = _attention(
        _attention_record("namespace", "NAMESPACE", "Namespace/moodle", "INHIBITED"),
        _attention_record("platform", "PLATFORM", "Platform/k3s-main", "ACTIVE"),
    )
    result = build_event_correlation(runtime, attention)
    ns, platform = result["correlations"]
    assert ns["correlation_status"] == "MATCHED"
    assert ns["related_warning_events"][0]["basis"] == [
        "NAMESPACE_SCOPE_MEMBERSHIP",
        "RECENT_KUBERNETES_WARNING_EVENT",
    ]
    assert platform["correlation_status"] == "NO_DIRECT_EVENT_MATCH"
    assert platform["related_warning_events"] == []


def test_pod_name_is_not_promoted_to_workload_ownership():
    runtime = build_kubernetes_event_runtime(
        cluster_id="k3s-main",
        runner=_runner(
            [
                _event(
                    name="web-abc123",
                    namespace="app",
                    kind="Pod",
                    reason="CrashLoopBackOff",
                )
            ]
        ),
        now=NOW,
    )
    attention = _attention(
        _attention_record("workload", "WORKLOAD", "Deployment/app/web", "ACTIVE")
    )
    result = build_event_correlation(runtime, attention)
    assert result["correlations"][0]["correlation_status"] == "NO_DIRECT_EVENT_MATCH"


def test_event_read_failure_produces_unknown_correlation_not_false_no_match():
    def runner(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            1,
            "",
            "Error from server (Forbidden): events is forbidden",
        )

    runtime = build_kubernetes_event_runtime(
        cluster_id="k3s-main",
        runner=runner,
        now=NOW,
    )
    assert runtime["source"]["status"] == "FAILED_TO_OBSERVE"
    assert runtime["errors"][0]["code"] == "KUBERNETES_EVENTS_FORBIDDEN"

    correlation = build_event_correlation(
        runtime,
        _attention(_attention_record("a1", "SERVICE", "Service/app/web")),
    )
    assert correlation["correlations"][0]["correlation_status"] == "UNKNOWN"


def test_truncation_marks_source_partial_and_no_match_unknown():
    runtime = build_kubernetes_event_runtime(
        cluster_id="k3s-main",
        runner=_runner(
            [
                _event(name="a", namespace="a", kind="Pod", reason="FailedA"),
                _event(name="b", namespace="b", kind="Pod", reason="FailedB"),
            ]
        ),
        now=NOW,
        max_events=1,
    )
    assert runtime["source"]["status"] == "PARTIAL"
    assert runtime["summary"]["window_truncated"] is True

    correlation = build_event_correlation(
        runtime,
        _attention(_attention_record("service", "SERVICE", "Service/missing/x")),
    )
    assert correlation["correlations"][0]["correlation_status"] == "UNKNOWN"


def test_reason_with_free_form_content_is_redacted():
    runtime = build_kubernetes_event_runtime(
        cluster_id="k3s-main",
        runner=_runner(
            [
                _event(
                    name="web",
                    namespace="app",
                    kind="Service",
                    reason="bad reason with spaces password=secret",
                )
            ]
        ),
        now=NOW,
    )
    assert runtime["events"][0]["reason"] == "REDACTED_REASON"


def test_runtime_and_correlation_match_schemas():
    runtime = build_kubernetes_event_runtime(
        cluster_id="k3s-main",
        runner=_runner(
            [
                _event(
                    name="web",
                    namespace="app",
                    kind="Service",
                    reason="BackOff",
                )
            ]
        ),
        now=NOW,
    )
    correlation = build_event_correlation(
        runtime,
        _attention(_attention_record("service", "SERVICE", "Service/app/web")),
    )

    root = Path(__file__).resolve().parents[1]
    runtime_schema = json.loads(
        (root / "schemas" / "kubernetes-event-runtime.schema.json").read_text(encoding="utf-8")
    )
    correlation_schema = json.loads(
        (root / "schemas" / "kubernetes-event-correlation.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(runtime_schema).validate(runtime)
    jsonschema.Draft202012Validator(correlation_schema).validate(correlation)
