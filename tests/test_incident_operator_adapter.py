from datetime import datetime, timezone

import pytest

from infra_assurance.incident_operator_adapter import build_incident_operator_adapter


def _artifact():
    return {
        "incident_candidates_version": "0.1",
        "cluster_id": "k3s-main",
        "mutation_allowed": False,
        "source_status": {
            "alert_attention": "COMPLETE",
            "kubernetes_events": "COMPLETE",
            "change_context": "COMPLETE",
            "drift": "COMPLETE",
            "inventory": "COMPLETE",
        },
        "summary": {
            "alert_attention_records": 3,
            "incident_candidates": 2,
            "active_candidates": 1,
            "suppressed_candidates": 1,
            "unknown_candidates": 0,
            "candidates_with_related_warning_events": 1,
            "candidates_with_exact_recent_change": 1,
            "candidates_with_exact_drift": 1,
            "candidates_with_related_workloads": 1,
            "candidates_requiring_live_verification": 1,
        },
        "candidates": [
            {
                "candidate_id": "incident-candidate-a",
                "scope": {"type": "SERVICE", "subject": "Service/monitoring/api", "basis": ["ALERT_LABELS"]},
                "state": "ACTIVE",
                "alert_count": 2,
                "alerts": [{"alertname": "RawAlertDetailMustNotLeak", "labels": {"private": "value"}}],
                "related_warning_events": [{"event_id": "event-1", "reason": "RawEventReasonMustNotLeak"}],
                "recent_changes": [{"classification": "MODIFIED", "field_changes": ["private-field"]}],
                "drift_attention": [{"field_mismatches": ["private-drift-field"]}],
                "impact_context": {"related_workloads_total": 1, "related_workloads": [{"subject": "Deployment/monitoring/api"}]},
                "recommended_checks": [
                    {
                        "code": "VERIFY_ALERT_CONDITION_CURRENT",
                        "target": "PROMETHEUS_ALERTMANAGER",
                        "check": "Verify the current alert condition before action.",
                        "rationale": "raw rationale not projected",
                        "live_verification_required": True,
                    }
                ],
            },
            {
                "candidate_id": "incident-candidate-b",
                "scope": {"type": "PLATFORM", "subject": "Cluster/k3s-main", "basis": ["PLATFORM"]},
                "state": "SUPPRESSED",
                "alert_count": 1,
                "related_warning_events": [],
                "recent_changes": [],
                "drift_attention": [],
                "recommended_checks": [],
            },
        ],
    }


def test_projects_compact_incident_operator_contract():
    result = build_incident_operator_adapter(
        _artifact(),
        now=datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc),
    )

    assert result["cluster_id"] == "k3s-main"
    assert result["mutation_allowed"] is False
    assert result["scope"] == "INCIDENT_CANDIDATES_EXISTING_EVIDENCE_ONLY"
    assert result["source_status"] == "COMPLETE"
    assert result["summary"]["incident_candidates"] == 2
    assert result["summary"]["active_candidates"] == 1
    assert result["summary"]["suppressed_candidates"] == 1
    assert result["summary"]["attention_total"] == 1
    assert result["summary"]["required_verification_categories_total"] == 1
    assert result["candidates"][0] == {
        "candidate_id": "incident-candidate-a",
        "state": "ACTIVE",
        "scope": {"type": "SERVICE", "subject": "Service/monitoring/api"},
        "alert_count": 2,
        "related_warning_events_count": 1,
        "recent_changes_count": 1,
        "drift_attention_count": 1,
        "recommended_checks_count": 1,
    }


def test_projection_discards_raw_incident_details():
    result = build_incident_operator_adapter(_artifact())
    rendered = repr(result)

    for forbidden in (
        "RawAlertDetailMustNotLeak",
        "RawEventReasonMustNotLeak",
        "private-field",
        "private-drift-field",
        "raw rationale not projected",
        "Deployment/monitoring/api",
    ):
        assert forbidden not in rendered


def test_incomplete_sources_are_explicit_attention_not_negative_evidence():
    artifact = _artifact()
    artifact["source_status"]["kubernetes_events"] = "FAILED_TO_OBSERVE"

    result = build_incident_operator_adapter(artifact)

    assert result["source_status"] == "PARTIAL"
    assert result["attention"][0]["code"] == "INCIDENT_SOURCE_INCOMPLETE"
    assert result["attention"][0]["severity"] == "UNKNOWN"
    assert "absence" in result["attention"][0]["statement"].lower()


def test_required_verification_is_deduplicated_and_truncated_explicitly():
    artifact = _artifact()
    artifact["candidates"][0]["recommended_checks"] = [
        {
            "code": "VERIFY_A",
            "target": "TARGET_A",
            "check": "Check A",
            "live_verification_required": True,
        },
        {
            "code": "VERIFY_A",
            "target": "TARGET_A",
            "check": "Check A",
            "live_verification_required": True,
        },
        {
            "code": "VERIFY_B",
            "target": "TARGET_B",
            "check": "Check B",
            "live_verification_required": True,
        },
    ]

    result = build_incident_operator_adapter(artifact, max_verifications=1)

    assert result["summary"]["required_verification_categories_total"] == 2
    assert len(result["required_live_verification"]) == 1
    assert result["truncation"]["required_live_verification_truncated"] is True


def test_candidate_projection_truncation_is_explicit():
    result = build_incident_operator_adapter(_artifact(), max_candidates=1)

    assert result["summary"]["incident_candidates"] == 2
    assert result["summary"]["projected_candidates"] == 1
    assert result["truncation"]["candidates_truncated"] is True


def test_trust_semantics_and_invalid_inputs_fail_closed():
    result = build_incident_operator_adapter(_artifact())

    assert result["trust"] == {
        "candidate_is_confirmed_incident": False,
        "candidate_is_root_cause": False,
        "suppressed_means_resolved": False,
        "live_verification_required_before_action": True,
    }

    with pytest.raises(ValueError, match="identify a cluster"):
        build_incident_operator_adapter({"summary": {}, "source_status": {"x": "COMPLETE"}})
    with pytest.raises(ValueError, match="max_candidates"):
        build_incident_operator_adapter(_artifact(), max_candidates=0)
    with pytest.raises(ValueError, match="max_verifications"):
        build_incident_operator_adapter(_artifact(), max_verifications=0)
