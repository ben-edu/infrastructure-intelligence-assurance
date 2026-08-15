from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from infra_assurance.prometheus_rule_context import build_prometheus_rule_context

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 15, 14, 0, tzinfo=timezone.utc)


def _candidate(candidate_id: str, state: str, scope_type: str, subject: str, *alert_names: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "state": state,
        "scope": {"type": scope_type, "subject": subject, "basis": ["TEST"]},
        "alerts": [
            {
                "attention_id": f"att-{candidate_id}-{index}",
                "handling_state": "ACTIVE" if state == "ACTIVE" else "INHIBITED",
                "alertname": name,
                "severity": "warning",
                "starts_at": "2026-08-15T13:00:00Z",
                "evidence_ids": [f"ev-{candidate_id}-{index}"],
            }
            for index, name in enumerate(alert_names)
        ],
    }


def _incident(*candidates: dict) -> dict:
    return {
        "incident_candidates_version": "0.3",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T13:50:00Z",
        "mutation_allowed": False,
        "source_status": {
            "alert_attention": "COMPLETE",
            "kubernetes_events": "COMPLETE",
            "routing_ownership": "COMPLETE",
        },
        "summary": {},
        "recommended_next_evidence_targets": [],
        "candidates": list(candidates),
        "drilldown_policy": {
            "version": "0.1",
            "mode": "SCOPE_AWARE",
            "requires_complete_alert_and_event_evidence": True,
            "default_log_scopes": ["WORKLOAD", "SERVICE_WITH_PREFERRED_ROUTING"],
        },
    }


def _rules_payload() -> dict:
    return {
        "status": "success",
        "data": {
            "groups": [
                {
                    "name": "kubernetes-resources",
                    "file": "/etc/prometheus/rules/secret-looking-path.yaml",
                    "rules": [
                        {
                            "type": "alerting",
                            "name": "KubeCPUOvercommit",
                            "query": "sum(namespace_cpu:kube_pod_container_resource_requests:sum) > scalar(kube_node_status_allocatable)",
                            "duration": 300,
                            "keepFiringFor": 0,
                            "labels": {"severity": "warning", "team": "platform"},
                            "annotations": {"runbook_url": "https://example.invalid/runbook", "summary": "do not persist"},
                            "alerts": [{"labels": {"namespace": "private"}}],
                            "health": "ok",
                            "lastError": "do not persist this error text",
                            "evaluationTime": 0.004,
                            "lastEvaluation": "2026-08-15T13:59:58Z",
                            "state": "firing",
                        },
                        {
                            "type": "alerting",
                            "name": "Watchdog",
                            "query": "vector(1)",
                            "duration": 0,
                            "keepFiringFor": 0,
                            "labels": {"severity": "none"},
                            "annotations": {"description": "do not persist"},
                            "alerts": [],
                            "health": "ok",
                            "evaluationTime": 0.001,
                            "lastEvaluation": "2026-08-15T13:59:57Z",
                            "state": "firing",
                        },
                        {
                            "type": "recording",
                            "name": "UnrelatedRecordingRule",
                            "query": "sum(rate(http_requests_total[5m]))",
                            "health": "ok",
                        },
                    ],
                },
                {
                    "name": "other-group",
                    "rules": [
                        {
                            "type": "alerting",
                            "name": "UnrequestedAlert",
                            "query": "up == 0",
                            "health": "ok",
                            "state": "firing",
                        }
                    ],
                },
            ]
        },
    }


def _runner_for(payload: dict, seen: list[list[str]]):
    def runner(command, **kwargs):
        seen.append(list(command))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(payload),
            stderr="",
        )

    return runner


def test_queries_only_exact_active_alert_names_and_excludes_embedded_alert_payloads():
    incident = _incident(
        _candidate("platform", "ACTIVE", "PLATFORM", "Platform/k3s-main", "KubeCPUOvercommit", "Watchdog"),
        _candidate("namespace", "SUPPRESSED", "NAMESPACE", "Namespace/moodle", "CPUThrottlingHigh"),
    )
    seen: list[list[str]] = []

    artifact = build_prometheus_rule_context(
        incident,
        runner=_runner_for(_rules_payload(), seen),
        now=NOW,
    )

    assert len(seen) == 1
    command = seen[0]
    assert command[:2] == ["kubectl", "get"]
    raw_path = command[command.index("--raw") + 1]
    assert "/services/kube-prom-stack-prometheus:9090/proxy/api/v1/rules?" in raw_path
    assert "type=alert" in raw_path
    assert "exclude_alerts=true" in raw_path
    assert "rule_name%5B%5D=KubeCPUOvercommit" in raw_path
    assert "rule_name%5B%5D=Watchdog" in raw_path
    assert "CPUThrottlingHigh" not in raw_path

    assert artifact["requested_alert_names"] == ["KubeCPUOvercommit", "Watchdog"]
    assert artifact["matched_alert_names"] == ["KubeCPUOvercommit", "Watchdog"]
    assert artifact["summary"]["rule_records"] == 2
    assert artifact["source"]["status"] == "COMPLETE"
    assert artifact["source"]["queried"] is True


def test_safe_projection_omits_promql_labels_annotations_files_embedded_alerts_and_error_text():
    artifact = build_prometheus_rule_context(
        _incident(_candidate("platform", "ACTIVE", "PLATFORM", "Platform/k3s-main", "KubeCPUOvercommit", "Watchdog")),
        runner=_runner_for(_rules_payload(), []),
        now=NOW,
    )

    raw = json.dumps(artifact)
    for forbidden in (
        '"query"',
        '"labels"',
        '"annotations"',
        '"file"',
        '"alerts"',
        '"lastError"',
        "runbook_url",
        "http_requests_total",
        "namespace_cpu:kube_pod_container_resource_requests:sum",
        "example.invalid",
        "do not persist",
    ):
        assert forbidden not in raw

    assert all(rule["expression_persisted"] is False for rule in artifact["rules"])
    assert {rule["alertname"] for rule in artifact["rules"]} == {"KubeCPUOvercommit", "Watchdog"}
    assert {rule["group_name"] for rule in artifact["rules"]} == {"kubernetes-resources"}


def test_exact_rule_matches_are_attached_only_to_active_candidate_and_require_input_verification():
    artifact = build_prometheus_rule_context(
        _incident(
            _candidate("platform", "ACTIVE", "PLATFORM", "Platform/k3s-main", "KubeCPUOvercommit", "Watchdog"),
            _candidate("moodle", "SUPPRESSED", "NAMESPACE", "Namespace/moodle", "CPUThrottlingHigh"),
        ),
        runner=_runner_for(_rules_payload(), []),
        now=NOW,
    )

    assert len(artifact["candidate_context"]) == 1
    context = artifact["candidate_context"][0]
    assert context["candidate_id"] == "platform"
    assert context["scope"] == {"type": "PLATFORM", "subject": "Platform/k3s-main"}
    assert context["alert_names"] == ["KubeCPUOvercommit", "Watchdog"]
    assert len(context["matched_rule_ids"]) == 2
    assert context["unmatched_alert_names"] == []
    assert context["basis"] == ["EXACT_ALERTNAME_PROMETHEUS_RULE_MATCH"]
    assert context["required_live_verification"] == [
        {
            "target": "PROMETHEUS_RULE_INPUTS",
            "statement": "Prometheus rule metadata is observed, but current PromQL input values are not collected by this slice and require separate live verification before causal interpretation.",
        }
    ]


def test_no_active_candidate_performs_no_prometheus_query():
    calls: list[list[str]] = []
    artifact = build_prometheus_rule_context(
        _incident(_candidate("moodle", "SUPPRESSED", "NAMESPACE", "Namespace/moodle", "CPUThrottlingHigh")),
        runner=_runner_for(_rules_payload(), calls),
        now=NOW,
    )
    assert calls == []
    assert artifact["source"]["queried"] is False
    assert artifact["source"]["status"] == "COMPLETE"
    assert artifact["requested_alert_names"] == []
    assert artifact["rules"] == []
    assert artifact["candidate_context"] == []


def test_alert_name_bound_is_explicit_and_makes_source_partial():
    names = tuple(f"Alert{i:02d}" for i in range(5))
    seen: list[list[str]] = []
    artifact = build_prometheus_rule_context(
        _incident(_candidate("platform", "ACTIVE", "PLATFORM", "Platform/k3s-main", *names)),
        runner=_runner_for({"status": "success", "data": {"groups": []}}, seen),
        now=NOW,
        max_alert_names=2,
    )
    assert artifact["source"]["status"] == "PARTIAL"
    assert artifact["bounds"] == {
        "max_active_alert_names": 2,
        "active_alert_names_total": 5,
        "active_alert_names_requested": 2,
        "active_alert_names_truncated": True,
    }
    assert artifact["requested_alert_names"] == ["Alert00", "Alert01"]
    assert any(item["code"] == "PROMETHEUS_RULE_ALERT_SCOPE_TRUNCATED" for item in artifact["unknowns"])


def test_proxy_failure_is_failed_to_observe_not_absence():
    def denied(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="Error from server (Forbidden): denied")

    artifact = build_prometheus_rule_context(
        _incident(_candidate("platform", "ACTIVE", "PLATFORM", "Platform/k3s-main", "Watchdog")),
        runner=denied,
        now=NOW,
    )
    assert artifact["source"]["status"] == "FAILED_TO_OBSERVE"
    assert artifact["rules"] == []
    assert artifact["errors"][0]["code"] == "PROMETHEUS_PROXY_FORBIDDEN"
    assert artifact["unmatched_alert_names"] == ["Watchdog"]
    assert any(item["code"] == "PROMETHEUS_ALERT_RULE_NOT_MATCHED" for item in artifact["unknowns"])


def test_unsafe_alertname_is_not_sent_to_prometheus():
    seen: list[list[str]] = []
    artifact = build_prometheus_rule_context(
        _incident(_candidate("platform", "ACTIVE", "PLATFORM", "Platform/k3s-main", "SafeAlert", 'bad{name="secret"}')),
        runner=_runner_for({"status": "success", "data": {"groups": []}}, seen),
        now=NOW,
    )
    assert artifact["requested_alert_names"] == ["SafeAlert"]
    raw_path = seen[0][seen[0].index("--raw") + 1]
    assert "SafeAlert" in raw_path
    assert "secret" not in raw_path


def test_output_validates_schema():
    artifact = build_prometheus_rule_context(
        _incident(_candidate("platform", "ACTIVE", "PLATFORM", "Platform/k3s-main", "KubeCPUOvercommit", "Watchdog")),
        runner=_runner_for(_rules_payload(), []),
        now=NOW,
    )
    schema = json.loads((ROOT / "schemas" / "prometheus-rule-context.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(artifact)
