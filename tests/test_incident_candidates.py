from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from infra_assurance.incident_candidates import build_incident_candidates

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)


def _attention(*items):
    return {
        "alert_attention_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T12:00:00Z",
        "mutation_allowed": False,
        "source_status": {"prometheus": "COMPLETE", "alertmanager": "COMPLETE"},
        "summary": {},
        "attention": list(items),
        "unknowns": [],
        "caveats": [],
    }


def _alert(attention_id, scope_type, subject, handling, alertname="ExampleAlert", severity="warning"):
    return {
        "attention_id": attention_id,
        "alertmanager_alert_id": "am-" + attention_id,
        "prometheus_alert_id": "prom-" + attention_id,
        "correlation_status": "MATCHED",
        "state": "ACTIVE" if handling == "ACTIVE" else "SUPPRESSED",
        "handling_state": handling,
        "labels": {"alertname": alertname, "severity": severity},
        "scope": {
            "type": scope_type,
            "subject": subject,
            "basis": ["TEST_SCOPE_BASIS"],
        },
        "starts_at": "2026-08-15T11:00:00Z",
        "updated_at": "2026-08-15T11:30:00Z",
        "ends_at": None,
        "silence_refs": [],
        "evidence_ids": ["ev-alert-" + attention_id],
    }


def _event_correlation(*items, status="COMPLETE"):
    return {
        "event_correlation_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T12:00:00Z",
        "mutation_allowed": False,
        "source_status": {"kubernetes_events": status, "alert_attention": "COMPLETE"},
        "summary": {},
        "correlations": list(items),
        "caveats": [],
    }


def _correlation(attention_id, related=None, status="NO_DIRECT_EVENT_MATCH"):
    return {
        "attention_id": attention_id,
        "attention_scope": {
            "type": "NAMESPACE",
            "subject": "Namespace/moodle",
            "basis": ["TEST_SCOPE_BASIS"],
        },
        "handling_state": "INHIBITED",
        "correlation_status": status,
        "related_warning_events": related or [],
        "evidence_ids": ["ev-alert-" + attention_id],
    }


def _inventory():
    return {
        "inventory_version": "0.3",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T12:00:00Z",
        "mutation_allowed": False,
        "scope": {"entity_type": "KUBERNETES_WORKLOAD", "workload_kinds": ["Deployment"]},
        "summary": {"workloads_total": 2, "namespaces_total": 2},
        "namespace_counts": {"moodle": 1, "monitoring": 1},
        "entities": [
            {
                "entity_id": "w1",
                "entity_type": "KUBERNETES_WORKLOAD",
                "subject": {
                    "system": "kubernetes",
                    "cluster": "k3s-main",
                    "api_group": "apps",
                    "kind": "Deployment",
                    "namespace": "moodle",
                    "name": "moodle",
                },
                "observed": {"freshness": "CURRENT", "evidence_id": "ev-workload-moodle"},
                "declared": {"coverage": "OUTSIDE_DECLARED_SCOPE", "comparison": None},
                "runtime_observability": {"state": "NO_RUNTIME_SIGNAL_MATCH"},
                "relationships": {
                    "services": [
                        {
                            "subject": "Service/moodle/moodle",
                            "basis": "SELECTOR_MATCH_INFERENCE",
                            "evidence_ids": ["ev-service-moodle"],
                        }
                    ],
                    "ingress_route_candidates": [
                        {
                            "subject": "Ingress/moodle/moodle",
                            "basis": "COMPOSED_INFERENCE",
                            "evidence_ids": ["ev-ingress-moodle"],
                        }
                    ],
                    "persistent_volume_claims": [],
                },
                "recent_change": {"state": "UNCHANGED", "items": []},
                "attention": [],
                "evidence_ids": ["ev-workload-moodle"],
            },
            {
                "entity_id": "w2",
                "entity_type": "KUBERNETES_WORKLOAD",
                "subject": {
                    "system": "kubernetes",
                    "cluster": "k3s-main",
                    "api_group": "apps",
                    "kind": "Deployment",
                    "namespace": "monitoring",
                    "name": "grafana",
                },
                "observed": {"freshness": "CURRENT", "evidence_id": "ev-workload-grafana"},
                "declared": {"coverage": "OUTSIDE_DECLARED_SCOPE", "comparison": None},
                "runtime_observability": {"state": "PROMETHEUS_TARGETS_UP"},
                "relationships": {
                    "services": [],
                    "ingress_route_candidates": [],
                    "persistent_volume_claims": [],
                },
                "recent_change": {"state": "UNCHANGED", "items": []},
                "attention": [],
                "evidence_ids": ["ev-workload-grafana"],
            },
        ],
    }


def _change_context():
    return {
        "change_context_version": "0.1",
        "task": {
            "type": "infrastructure_change_awareness",
            "scope": {"cluster": "k3s-main"},
            "mutation_allowed": False,
        },
        "generated_at": "2026-08-15T12:00:00Z",
        "history": {},
        "drift": {
            "status": "EVALUATED",
            "summary": {"declared_records": 27, "in_sync": 26, "drift": 1, "unknown": 0, "loader_errors": 0},
        },
        "recent_changes": [],
        "drift_attention": [],
        "unknowns": [],
        "required_live_verification": [],
        "truncation": {
            "max_items_per_section": 50,
            "recent_changes_truncated": False,
            "drift_attention_truncated": False,
            "unknowns_truncated": False,
            "required_verification_truncated": False,
        },
    }


def test_groups_only_identical_scope_and_preserves_active_vs_suppressed():
    attention = _attention(
        _alert("a1", "SERVICE", "Service/monitoring/kubelet", "INHIBITED", "CPUThrottlingHigh", "info"),
        _alert("a2", "SERVICE", "Service/monitoring/kubelet", "ACTIVE", "ExampleActive"),
        _alert("a3", "NAMESPACE", "Namespace/monitoring", "INHIBITED", "InfoInhibitor", "none"),
    )
    events = _event_correlation(
        _correlation("a1"), _correlation("a2"), _correlation("a3")
    )

    artifact = build_incident_candidates(attention, events, _inventory(), _change_context(), now=NOW)

    assert artifact["summary"]["incident_candidates"] == 2
    by_subject = {item["scope"]["subject"]: item for item in artifact["candidates"]}
    assert by_subject["Service/monitoring/kubelet"]["alert_count"] == 2
    assert by_subject["Service/monitoring/kubelet"]["state"] == "ACTIVE"
    assert by_subject["Namespace/monitoring"]["state"] == "SUPPRESSED"


def test_namespace_impact_is_breadth_context_not_business_impact():
    attention = _attention(_alert("a1", "NAMESPACE", "Namespace/moodle", "INHIBITED"))
    event = {
        "event_id": "event-1",
        "subject": "Pod/moodle/moodle-abc",
        "reason": "ProbeWarning",
        "last_seen": "2026-08-15T11:59:00Z",
        "count": 4,
        "basis": ["NAMESPACE_SCOPE_MEMBERSHIP", "RECENT_KUBERNETES_WARNING_EVENT"],
        "evidence_ids": ["ev-event-1"],
    }
    events = _event_correlation(_correlation("a1", [event], "MATCHED"))

    artifact = build_incident_candidates(attention, events, _inventory(), _change_context(), now=NOW)
    candidate = artifact["candidates"][0]

    assert candidate["impact_context"]["related_workloads_total"] == 1
    assert candidate["impact_context"]["related_workloads"][0]["basis"] == ["NAMESPACE_MEMBERSHIP"]
    assert "does not mean every workload" in candidate["impact_context"]["caveat"]
    assert candidate["related_warning_events"][0]["reason"] == "ProbeWarning"
    assert any(check["code"] == "VERIFY_RELATED_EVENT_OBJECT_STATE" for check in candidate["recommended_checks"])


def test_platform_scope_does_not_expand_to_all_workloads_and_active_recommends_verification():
    attention = _attention(_alert("a1", "PLATFORM", "Platform/k3s-main", "ACTIVE", "KubeCPUOvercommit"))
    events = _event_correlation(_correlation("a1"))

    artifact = build_incident_candidates(attention, events, _inventory(), _change_context(), now=NOW)
    candidate = artifact["candidates"][0]

    assert candidate["impact_context"]["related_workloads_total"] == 0
    assert candidate["impact_context"]["platform_context"] == {"workloads_total": 2, "namespaces_total": 2}
    codes = {item["code"] for item in candidate["recommended_checks"]}
    assert "VERIFY_ALERT_CONDITION_CURRENT" in codes
    assert "VERIFY_PLATFORM_SIGNAL_INPUTS" in codes
    assert "CHECK_SCOPE_LOGS_IF_NEEDED" in codes
    assert any(item["target"] == "LOKI_CANDIDATE" for item in artifact["recommended_next_evidence_targets"])


def test_service_impact_uses_existing_selector_inference_only():
    attention = _attention(_alert("a1", "SERVICE", "Service/moodle/moodle", "INHIBITED"))
    events = _event_correlation(_correlation("a1"))

    artifact = build_incident_candidates(attention, events, _inventory(), _change_context(), now=NOW)
    impact = artifact["candidates"][0]["impact_context"]

    assert impact["related_workloads_total"] == 1
    assert impact["related_workloads"][0]["subject"] == "Deployment/moodle/moodle"
    assert impact["related_workloads"][0]["basis"] == ["SELECTOR_MATCH_INFERENCE"]
    assert "EndpointSlice or Pod routing is not proven" in impact["caveat"]


def test_partial_event_source_never_turns_missing_event_into_false_certainty():
    attention = _attention(_alert("a1", "PLATFORM", "Platform/k3s-main", "ACTIVE"))
    events = _event_correlation(_correlation("a1", status="UNKNOWN"), status="PARTIAL")

    artifact = build_incident_candidates(attention, events, _inventory(), _change_context(), now=NOW)
    candidate = artifact["candidates"][0]

    assert artifact["source_status"]["kubernetes_events"] == "PARTIAL"
    assert candidate["event_correlation_statuses"] == ["UNKNOWN"]
    assert any(check["code"] == "REFRESH_KUBERNETES_EVENT_EVIDENCE" for check in candidate["recommended_checks"])


def test_incident_candidate_output_validates_schema():
    attention = _attention(_alert("a1", "NAMESPACE", "Namespace/moodle", "INHIBITED"))
    events = _event_correlation(_correlation("a1"))
    artifact = build_incident_candidates(attention, events, _inventory(), _change_context(), now=NOW)

    schema = json.loads((ROOT / "schemas" / "incident-candidates.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(artifact)
