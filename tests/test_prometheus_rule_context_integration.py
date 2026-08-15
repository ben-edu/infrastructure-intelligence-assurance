from __future__ import annotations

from copy import deepcopy

import pytest

from infra_assurance.prometheus_rule_context_integration import (
    integrate_prometheus_rule_context,
    render_rule_integration_markdown,
)


def _incident() -> dict:
    return {
        "incident_candidates_version": "0.3",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T14:06:50Z",
        "mutation_allowed": False,
        "source_status": {
            "alert_attention": "COMPLETE",
            "kubernetes_events": "COMPLETE",
            "routing_ownership": "COMPLETE",
        },
        "summary": {},
        "candidates": [
            {
                "candidate_id": "candidate-platform",
                "state": "ACTIVE",
                "scope": {
                    "type": "PLATFORM",
                    "subject": "Platform/k3s-main",
                },
                "alerts": [
                    {
                        "alertname": "KubeCPUOvercommit",
                        "evidence_ids": ["ev-alert-1"],
                    },
                    {
                        "alertname": "Watchdog",
                        "evidence_ids": ["ev-alert-2"],
                    },
                ],
                "alert_count": 2,
                "related_warning_events": [],
                "recent_changes": [],
                "drift_attention": [],
                "impact_context": {
                    "related_workloads_total": 0,
                    "related_workloads": [],
                },
                "recommended_checks": [
                    {
                        "code": "VERIFY_ALERT_CONDITION_CURRENT",
                        "target": "PROMETHEUS_ALERTMANAGER",
                        "check": "Verify current alert condition.",
                        "rationale": "Current alert handling does not prove cause.",
                        "live_verification_required": True,
                        "evidence_ids": ["ev-alert-1", "ev-alert-2"],
                    },
                    {
                        "code": "VERIFY_PLATFORM_SIGNAL_INPUTS",
                        "target": "PROMETHEUS_KUBERNETES",
                        "check": "Verify generic platform inputs.",
                        "rationale": "Platform scope requires current inputs.",
                        "live_verification_required": True,
                        "evidence_ids": ["ev-alert-1", "ev-alert-2"],
                    },
                ],
                "evidence_ids": ["ev-alert-1", "ev-alert-2"],
                "caveats": [],
            },
            {
                "candidate_id": "candidate-suppressed",
                "state": "SUPPRESSED",
                "scope": {
                    "type": "NAMESPACE",
                    "subject": "Namespace/monitoring",
                },
                "alerts": [
                    {
                        "alertname": "InfoInhibitor",
                        "evidence_ids": ["ev-alert-3"],
                    }
                ],
                "alert_count": 1,
                "related_warning_events": [],
                "recent_changes": [],
                "drift_attention": [],
                "impact_context": {
                    "related_workloads_total": 1,
                    "related_workloads": [],
                },
                "recommended_checks": [],
                "evidence_ids": ["ev-alert-3"],
                "caveats": [],
            },
        ],
        "recommended_next_evidence_targets": [
            {
                "target": "PROMETHEUS_ALERTMANAGER",
                "candidate_checks": 1,
            },
            {
                "target": "PROMETHEUS_KUBERNETES",
                "candidate_checks": 1,
            },
        ],
        "caveats": [],
    }


def _rule(
    rule_id: str,
    alertname: str,
    group: str,
    evidence_id: str,
) -> dict:
    return {
        "rule_id": rule_id,
        "evidence_id": evidence_id,
        "observed_at": "2026-08-15T14:06:52Z",
        "expires_at": "2026-08-15T14:11:52Z",
        "alertname": alertname,
        "group_name": group,
        "rule_type": "ALERTING",
        "state": "FIRING",
        "health": "OK",
        "duration_seconds": 600.0,
        "keep_firing_for_seconds": 0.0,
        "evaluation_time_seconds": 0.01,
        "last_evaluation": "2026-08-15T14:06:45Z",
        "expression_persisted": False,
        "query": "sensitive promql",
        "labels": {"cluster": "secret-ish"},
        "annotations": {"runbook_url": "https://example.invalid"},
    }


def _rule_artifact(status: str = "COMPLETE") -> dict:
    return {
        "prometheus_rule_context_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T14:06:52Z",
        "mutation_allowed": False,
        "source": {
            "status": status,
        },
        "rules": [
            _rule(
                "rule-cpu",
                "KubeCPUOvercommit",
                "kubernetes-resources",
                "ev-rule-cpu",
            ),
            _rule(
                "rule-watchdog",
                "Watchdog",
                "general.rules",
                "ev-rule-watchdog",
            ),
        ],
        "candidate_context": [
            {
                "candidate_id": "candidate-platform",
                "scope": {
                    "type": "PLATFORM",
                    "subject": "Platform/k3s-main",
                },
                "alert_names": [
                    "KubeCPUOvercommit",
                    "Watchdog",
                ],
                "matched_rule_ids": [
                    "rule-cpu",
                    "rule-watchdog",
                ],
                "unmatched_alert_names": [],
                "basis": [
                    "EXACT_ALERTNAME_PROMETHEUS_RULE_MATCH"
                ],
                "evidence_ids": [
                    "ev-rule-cpu",
                    "ev-rule-watchdog",
                ],
                "required_live_verification": [
                    {
                        "target": "PROMETHEUS_RULE_INPUTS",
                        "statement": "Verify current metric inputs.",
                    }
                ],
            }
        ],
    }


def _active(result: dict) -> dict:
    return next(
        item
        for item in result["candidates"]
        if item["candidate_id"] == "candidate-platform"
    )


def _codes(candidate: dict) -> set[str]:
    return {
        item["code"]
        for item in candidate["recommended_checks"]
    }


def _targets(candidate: dict) -> set[str]:
    return {
        item["target"]
        for item in candidate["recommended_checks"]
    }


def test_complete_exact_context_refines_platform_target_and_projects_safe_rules():
    result = integrate_prometheus_rule_context(
        _incident(),
        _rule_artifact(),
    )
    candidate = _active(result)
    context = candidate["prometheus_rule_context"]

    assert result["incident_candidates_version"] == "0.4"
    assert result["mutation_allowed"] is False
    assert result["source_status"]["prometheus_rule_context"] == "COMPLETE"
    assert result["prometheus_rule_context_integration"] == {
        "version": "0.1",
        "mode": "EXACT_COMPLETE_ONLY",
        "source_status": "COMPLETE",
        "source_generated_at": "2026-08-15T14:06:52Z",
    }

    assert context["selection"] == "COMPLETE_EXACT_RULE_MATCH"
    assert context["alert_names"] == [
        "KubeCPUOvercommit",
        "Watchdog",
    ]
    assert context["unmatched_alert_names"] == []
    assert context["missing_rule_ids"] == []
    assert context["basis"] == [
        "CANDIDATE_ID",
        "EXACT_ALERTNAME_PROMETHEUS_RULE_MATCH",
    ]
    assert {
        rule["alertname"]
        for rule in context["matched_rules"]
    } == {"KubeCPUOvercommit", "Watchdog"}
    assert all(
        rule["expression_persisted"] is False
        for rule in context["matched_rules"]
    )

    raw_rule_projection = str(context["matched_rules"])
    assert "sensitive promql" not in raw_rule_projection
    assert "runbook_url" not in raw_rule_projection
    assert "annotations" not in raw_rule_projection
    assert "labels" not in raw_rule_projection
    assert "query" not in raw_rule_projection

    assert "VERIFY_ALERT_CONDITION_CURRENT" in _codes(candidate)
    assert "VERIFY_PROMETHEUS_RULE_INPUTS" in _codes(candidate)
    assert "VERIFY_PLATFORM_SIGNAL_INPUTS" not in _codes(candidate)
    assert "PROMETHEUS_RULE_INPUTS" in _targets(candidate)
    assert "PROMETHEUS_KUBERNETES" not in _targets(candidate)

    assert result["summary"][
        "active_candidates_considered_for_prometheus_rule_context"
    ] == 1
    assert result["summary"][
        "active_candidates_with_complete_prometheus_rule_context"
    ] == 1
    assert result["summary"][
        "platform_checks_refined_to_prometheus_rule_inputs"
    ] == 1
    assert result["summary"]["prometheus_rule_integration_unknowns"] == 0
    assert result["prometheus_rule_context_integration_unknowns"] == []

    declared_targets = {
        item["target"]: item["candidate_checks"]
        for item in result["recommended_next_evidence_targets"]
    }
    assert declared_targets == {
        "PROMETHEUS_ALERTMANAGER": 1,
        "PROMETHEUS_RULE_INPUTS": 1,
    }

    suppressed = next(
        item
        for item in result["candidates"]
        if item["candidate_id"] == "candidate-suppressed"
    )
    assert "prometheus_rule_context" not in suppressed


def test_incomplete_source_retains_generic_platform_verification():
    result = integrate_prometheus_rule_context(
        _incident(),
        _rule_artifact(status="PARTIAL"),
    )
    candidate = _active(result)
    context = candidate["prometheus_rule_context"]

    assert context["selection"] == "SOURCE_INCOMPLETE"
    assert context["matched_rules"] == []
    assert "VERIFY_PLATFORM_SIGNAL_INPUTS" in _codes(candidate)
    assert "PROMETHEUS_KUBERNETES" in _targets(candidate)
    assert "VERIFY_PROMETHEUS_RULE_INPUTS" not in _codes(candidate)
    assert result["summary"][
        "platform_checks_refined_to_prometheus_rule_inputs"
    ] == 0
    assert result["summary"]["prometheus_rule_integration_unknowns"] == 1


def test_unmatched_alert_retains_generic_verification_and_is_explicit():
    rules = _rule_artifact()
    rules["rules"] = [rules["rules"][0]]
    context = rules["candidate_context"][0]
    context["matched_rule_ids"] = ["rule-cpu"]
    context["unmatched_alert_names"] = ["Watchdog"]

    result = integrate_prometheus_rule_context(
        _incident(),
        rules,
    )
    candidate = _active(result)
    integrated = candidate["prometheus_rule_context"]

    assert integrated["selection"] == "PARTIAL_EXACT_RULE_MATCH"
    assert integrated["unmatched_alert_names"] == ["Watchdog"]
    assert [
        item["alertname"]
        for item in integrated["matched_rules"]
    ] == ["KubeCPUOvercommit"]
    assert "PROMETHEUS_KUBERNETES" in _targets(candidate)
    assert "PROMETHEUS_RULE_INPUTS" not in _targets(candidate)
    assert result["prometheus_rule_context_integration_unknowns"][0][
        "code"
    ] == "PROMETHEUS_RULE_INTEGRATION_PARTIAL_EXACT_RULE_MATCH"


def test_candidate_alert_set_mismatch_is_not_promoted():
    rules = _rule_artifact()
    rules["candidate_context"][0]["alert_names"] = [
        "KubeCPUOvercommit"
    ]

    result = integrate_prometheus_rule_context(
        _incident(),
        rules,
    )
    candidate = _active(result)

    assert candidate["prometheus_rule_context"]["selection"] == (
        "CANDIDATE_ALERT_SET_MISMATCH"
    )
    assert candidate["prometheus_rule_context"]["matched_rules"] == []
    assert "PROMETHEUS_KUBERNETES" in _targets(candidate)


def test_missing_rule_record_is_not_promoted():
    rules = _rule_artifact()
    rules["rules"] = [rules["rules"][0]]

    result = integrate_prometheus_rule_context(
        _incident(),
        rules,
    )
    candidate = _active(result)
    context = candidate["prometheus_rule_context"]

    assert context["selection"] == "MATCHED_RULE_RECORD_MISSING"
    assert context["missing_rule_ids"] == ["rule-watchdog"]
    assert context["matched_rules"] == []
    assert "PROMETHEUS_KUBERNETES" in _targets(candidate)


def test_cluster_mismatch_is_rejected():
    rules = _rule_artifact()
    rules["cluster_id"] = "other"

    with pytest.raises(ValueError, match="same cluster"):
        integrate_prometheus_rule_context(
            _incident(),
            rules,
        )


def test_wrong_input_versions_are_rejected():
    incident = _incident()
    incident["incident_candidates_version"] = "0.2"

    with pytest.raises(ValueError, match="incident candidates v0.3"):
        integrate_prometheus_rule_context(
            incident,
            _rule_artifact(),
        )

    rules = _rule_artifact()
    rules["prometheus_rule_context_version"] = "0.2"

    with pytest.raises(ValueError, match="rule context v0.1"):
        integrate_prometheus_rule_context(
            _incident(),
            rules,
        )


def test_mutation_flags_are_required_false():
    incident = _incident()
    incident["mutation_allowed"] = True

    with pytest.raises(ValueError, match="mutation_allowed=false"):
        integrate_prometheus_rule_context(
            incident,
            _rule_artifact(),
        )

    rules = _rule_artifact()
    rules["mutation_allowed"] = True

    with pytest.raises(ValueError, match="mutation_allowed=false"):
        integrate_prometheus_rule_context(
            _incident(),
            rules,
        )


def test_markdown_surfaces_rule_context_without_promql():
    result = integrate_prometheus_rule_context(
        _incident(),
        _rule_artifact(),
    )
    text = render_rule_integration_markdown(result)

    assert "Prometheus rule context integration" in text
    assert "COMPLETE_EXACT_RULE_MATCH" in text
    assert "KubeCPUOvercommit" in text
    assert "Watchdog" in text
    assert "kubernetes-resources" in text
    assert "general.rules" in text
    assert "PROMETHEUS_RULE_INPUTS" in text
    assert "sensitive promql" not in text
    assert "https://" not in text
