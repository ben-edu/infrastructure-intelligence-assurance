from __future__ import annotations

from datetime import datetime, timezone

import pytest

from infra_assurance.operator_attention_incident import (
    build_operator_attention_with_incidents,
    render_operator_attention_with_incidents_markdown,
)


def _operator() -> dict:
    return {
        "operator_attention_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-30T10:00:00Z",
        "mutation_allowed": False,
        "scope": "KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY",
        "source_artifacts": [
            "inventory.json",
            "context.json",
            "change-context.json",
            "backup-assurance.json",
        ],
        "summary": {
            "workloads_total": 68,
            "workloads_with_attention": 3,
            "attention_now_total": 5,
            "recent_changes_total": 0,
            "unknowns_total": 0,
            "required_live_verification_total": 8,
            "backup_assets_total": 37,
            "backup_protection_unknown": 37,
            "backup_restore_verification_unknown": 37,
            "backup_unprotected_claims": 0,
        },
        "attention_now": [
            {
                "source": "topology",
                "code": "SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES",
                "severity": "AMBIGUOUS",
                "subject": "Service/monitoring/loki-headless",
                "statement": "bounded topology ambiguity",
                "evidence_ids": ["ev-topology"],
                "count": None,
            },
            {
                "source": "backup_assurance",
                "code": "BACKUP_PROTECTION_UNKNOWN",
                "severity": "UNKNOWN",
                "subject": None,
                "statement": "UNKNOWN is not UNPROTECTED.",
                "evidence_ids": [],
                "count": 37,
            },
        ],
        "recent_changes": [],
        "unknowns": [],
        "required_live_verification": [
            {
                "source": "backup_assurance",
                "code": "OBSERVE_RESTORE_TEST",
                "check": "Observe restore testing from an authoritative source.",
                "reason": "Authoritative backup evidence required.",
                "target": "RESTORE_TEST",
                "authoritative_source_required": True,
            }
        ],
        "truncation": {
            "attention_now_truncated": False,
            "recent_changes_truncated": False,
            "unknowns_truncated": False,
            "required_live_verification_truncated": False,
        },
        "backup_assurance": {
            "source_status": "COMPLETE",
            "summary": {
                "assets_total": 37,
                "protection_unknown": 37,
                "restore_verification_unknown": 37,
                "unprotected_claims": 0,
            },
            "trust": {
                "unknown_is_not_unprotected": True,
                "recovery_test_overdue_claimed": False,
                "authoritative_backup_evidence_required_for_unprotected": True,
            },
        },
    }


def _incidents(*, partial: bool = False) -> dict:
    source_status = {
        "alert_attention": "COMPLETE",
        "kubernetes_events": "PARTIAL" if partial else "COMPLETE",
        "change_context": "COMPLETE",
        "drift": "COMPLETE",
        "inventory": "COMPLETE",
    }
    return {
        "incident_candidates_version": "0.1",
        "cluster_id": "k3s-main",
        "mutation_allowed": False,
        "source_status": source_status,
        "summary": {
            "alert_attention_records": 4,
            "incident_candidates": 2,
            "active_candidates": 2,
            "suppressed_candidates": 0,
            "unknown_candidates": 0,
            "candidates_with_related_warning_events": 1,
            "candidates_with_exact_recent_change": 0,
            "candidates_with_exact_drift": 0,
            "candidates_with_related_workloads": 2,
            "candidates_requiring_live_verification": 2,
        },
        "candidates": [
            {
                "candidate_id": "incident-candidate-a",
                "scope": {"type": "NAMESPACE", "subject": "Namespace/moodle", "basis": ["ALERT_SCOPE"]},
                "state": "ACTIVE",
                "alert_count": 2,
                "alerts": [{"alertname": "secret-alert-detail"}],
                "related_warning_events": [{"event_id": "secret-event-detail"}],
                "recent_changes": [],
                "drift_attention": [],
                "impact_context": {"related_workloads": [{"subject": "Deployment/moodle/secret"}]},
                "recommended_checks": [
                    {
                        "code": "VERIFY_ALERT_CONDITION_CURRENT",
                        "target": "PROMETHEUS_ALERTMANAGER",
                        "check": "Verify the current alert condition for Namespace/moodle.",
                        "live_verification_required": True,
                    },
                    {
                        "code": "VERIFY_RELATED_EVENT_OBJECT_STATE",
                        "target": "KUBERNETES_OBJECT",
                        "check": "Verify the current state of the involved object.",
                        "live_verification_required": True,
                    },
                ],
            },
            {
                "candidate_id": "incident-candidate-b",
                "scope": {"type": "PLATFORM", "subject": "Platform/k3s-main", "basis": ["ALERT_SCOPE"]},
                "state": "ACTIVE",
                "alert_count": 2,
                "alerts": [],
                "related_warning_events": [],
                "recent_changes": [],
                "drift_attention": [],
                "impact_context": {},
                "recommended_checks": [
                    {
                        "code": "VERIFY_PROMETHEUS_RULE_INPUTS",
                        "target": "PROMETHEUS_RULE_INPUTS",
                        "check": "Verify current rule inputs.",
                        "live_verification_required": True,
                    }
                ],
            },
        ],
    }


def test_combines_existing_operator_attention_with_compact_incident_evidence():
    result = build_operator_attention_with_incidents(
        _operator(),
        _incidents(),
        now=datetime(2026, 8, 30, 10, 30, tzinfo=timezone.utc),
    )

    assert result["scope"] == "KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY"
    assert result["mutation_allowed"] is False
    assert result["source_artifacts"][-1] == "incident-candidates.json"
    assert result["summary"]["attention_now_total"] == 6
    assert result["summary"]["required_live_verification_total"] == 11
    assert result["summary"]["incident_candidates_total"] == 2
    assert result["summary"]["incident_active_candidates"] == 2
    assert result["summary"]["incident_candidates_with_related_warning_events"] == 1
    assert result["incident_candidates"]["trust"]["candidate_is_confirmed_incident"] is False
    assert "secret-alert-detail" not in repr(result)
    assert "secret-event-detail" not in repr(result)
    assert "Deployment/moodle/secret" not in repr(result)


def test_partial_incident_sources_are_explicit_and_not_negative_evidence():
    result = build_operator_attention_with_incidents(_operator(), _incidents(partial=True))

    assert result["incident_candidates"]["source_status"] == "PARTIAL"
    codes = {
        item["code"]
        for item in result["attention_now"]
        if item.get("source") == "incident_candidates"
    }
    assert "INCIDENT_SOURCE_INCOMPLETE" in codes
    assert "ACTIVE_INCIDENT_CANDIDATES" in codes
    trust = result["incident_candidates"]["trust"]
    assert trust["candidate_is_confirmed_incident"] is False
    assert trust["candidate_is_root_cause"] is False
    assert trust["suppressed_means_resolved"] is False
    assert trust["live_verification_required_before_action"] is True


def test_cluster_mismatch_fails_closed():
    incidents = _incidents()
    incidents["cluster_id"] = "other-cluster"

    with pytest.raises(ValueError, match="same cluster"):
        build_operator_attention_with_incidents(_operator(), incidents)


def test_rejects_unaccepted_operator_contract():
    operator = _operator()
    operator["scope"] = "KUBERNETES_EXISTING_EVIDENCE_ONLY"
    with pytest.raises(ValueError, match="accepted Kubernetes\+backup scope"):
        build_operator_attention_with_incidents(operator, _incidents())

    operator = _operator()
    operator["mutation_allowed"] = True
    with pytest.raises(ValueError, match="mutation_allowed=false"):
        build_operator_attention_with_incidents(operator, _incidents())


def test_combined_totals_survive_projection_truncation():
    result = build_operator_attention_with_incidents(
        _operator(),
        _incidents(partial=True),
        max_items=2,
        max_incident_candidates=1,
    )

    assert result["summary"]["attention_now_total"] == 7
    assert result["summary"]["required_live_verification_total"] == 11
    assert len(result["attention_now"]) == 2
    assert len(result["required_live_verification"]) == 2
    assert result["truncation"]["attention_now_truncated"] is True
    assert result["truncation"]["required_live_verification_truncated"] is True
    assert result["truncation"]["incident_candidates_truncated"] is True


def test_markdown_keeps_incident_trust_language():
    result = build_operator_attention_with_incidents(_operator(), _incidents(partial=True))
    rendered = render_operator_attention_with_incidents_markdown(result)

    assert "## Incident candidates" in rendered
    assert "Source status: PARTIAL" in rendered
    assert "Candidate grouping is not incident confirmation or root-cause proof." in rendered
    assert "## Backup assurance" in rendered
