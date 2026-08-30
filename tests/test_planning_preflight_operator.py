import pytest

from infra_assurance.planning_preflight_operator import (
    INTEGRATION_SCOPE,
    enrich_deployment_preflight_with_operator_context,
    render_operator_aware_preflight_markdown,
)


def _preflight(*, namespace="validation", pvc=True, unknowns=None, conflicts=None, required=None):
    request = {
        "request_version": "0.1",
        "type": "hypothetical_kubernetes_application_deployment",
        "cluster_id": "k3s-main",
        "namespace": namespace,
        "application": "assurance-demo",
        "deployment": {"name": "assurance-demo", "replicas": 2, "image": "example.invalid/demo:1"},
    }
    if pvc:
        request["pvc"] = {"name": "data", "size": "1Gi", "storage_class": None}
    return {
        "preflight_version": "0.1",
        "generated_at": "2026-08-30T10:00:00Z",
        "cluster_id": "k3s-main",
        "request": request,
        "mutation_allowed": False,
        "readiness": "PLAN_WITH_LIVE_VERIFICATION",
        "facts": [{"code": "BASE_FACT", "statement": "base", "evidence_ids": []}],
        "conflicts": list(conflicts or []),
        "inferences": [],
        "unknowns": list(unknowns or []),
        "required_live_verification": list(
            required
            or [
                {
                    "code": "VERIFY_IMAGE_PULLABILITY",
                    "check": "Verify image pullability.",
                    "reason": "Registry evidence is outside the base slice.",
                    "evidence_ids": [],
                }
            ]
        ),
        "candidate_plan": [{"order": 1, "action": "Prepare Deployment.", "state": "PLAN_ONLY", "evidence_ids": []}],
        "post_change_verification": [
            {"code": "VERIFY_DEPLOYMENT_READINESS", "statement": "Verify readiness.", "evidence_ids": []}
        ],
    }


def _operator(*, candidates=None, attention=None, changes=None, unknowns=None):
    candidates = candidates if candidates is not None else [
        {
            "candidate_id": "inc-platform",
            "state": "ACTIVE",
            "scope": {"type": "PLATFORM", "subject": "Platform/k3s-main"},
            "alert_count": 2,
            "related_warning_events_count": 0,
            "recent_changes_count": 0,
            "drift_attention_count": 0,
            "recommended_checks_count": 2,
        },
        {
            "candidate_id": "inc-other",
            "state": "ACTIVE",
            "scope": {"type": "NAMESPACE", "subject": "Namespace/monitoring"},
            "alert_count": 5,
            "related_warning_events_count": 0,
            "recent_changes_count": 0,
            "drift_attention_count": 0,
            "recommended_checks_count": 1,
        },
    ]
    return {
        "operator_attention_version": "0.1",
        "generated_at": "2026-08-30T10:05:00Z",
        "cluster_id": "k3s-main",
        "mutation_allowed": False,
        "scope": "KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY",
        "summary": {
            "attention_now_total": 7,
            "recent_changes_total": 1,
            "unknowns_total": 1,
            "required_live_verification_total": 11,
            "backup_assets_total": 37,
            "backup_protection_unknown": 37,
            "backup_restore_verification_unknown": 37,
            "backup_unprotected_claims": 0,
            "incident_candidates_total": len(candidates),
            "incident_active_candidates": sum(1 for item in candidates if item["state"] == "ACTIVE"),
            "incident_suppressed_candidates": sum(1 for item in candidates if item["state"] == "SUPPRESSED"),
        },
        "attention_now": list(
            attention
            or [
                {
                    "source": "inventory",
                    "code": "DECLARED_OBSERVED_DRIFT",
                    "severity": "DRIFT",
                    "subject": "Ingress/validation/nginx-validation",
                    "statement": "Observed drift intersects validation.",
                },
                {
                    "source": "inventory",
                    "code": "OTHER",
                    "severity": "ATTENTION",
                    "subject": "Service/monitoring/loki-headless",
                    "statement": "Other namespace.",
                },
            ]
        ),
        "recent_changes": list(changes or [{"classification": "MODIFIED", "subject": "Deployment/validation/api"}]),
        "unknowns": list(
            unknowns
            or [
                {
                    "source": "change_context",
                    "code": "UNKNOWN_TARGET_STATE",
                    "subject": "Service/validation/api",
                    "statement": "Target state needs fresh verification.",
                }
            ]
        ),
        "required_live_verification": [],
        "source_artifacts": [
            "inventory.json",
            "context.json",
            "change-context.json",
            "backup-assurance.json",
            "incident-candidates.json",
        ],
        "truncation": {
            "attention_now_truncated": False,
            "recent_changes_truncated": False,
            "unknowns_truncated": False,
            "required_live_verification_truncated": False,
            "incident_candidates_truncated": False,
        },
        "backup_assurance": {
            "source_status": "COMPLETE",
            "trust": {
                "unknown_is_not_unprotected": True,
                "recovery_test_overdue_claimed": False,
                "authoritative_backup_evidence_required_for_unprotected": True,
            },
        },
        "incident_candidates": {
            "source_status": "PARTIAL",
            "source_statuses": {"alerts": "COMPLETE", "events": "PARTIAL"},
            "summary": {},
            "candidates": candidates,
            "trust": {
                "candidate_is_confirmed_incident": False,
                "candidate_is_root_cause": False,
                "suppressed_means_resolved": False,
                "live_verification_required_before_action": True,
            },
            "truncation": {"candidates_truncated": False, "required_live_verification_truncated": False},
        },
    }


def test_enrichment_preserves_base_contract_and_projects_only_relevant_operator_context():
    result = enrich_deployment_preflight_with_operator_context(_preflight(), _operator())

    assert result["scope"] == INTEGRATION_SCOPE
    assert result["mutation_allowed"] is False
    assert result["facts"][0]["code"] == "BASE_FACT"
    assert len(result["operator_context"]["relevant_attention"]) == 1
    assert len(result["operator_context"]["relevant_recent_changes"]) == 1
    assert len(result["operator_context"]["relevant_unknowns"]) == 1
    assert [item["candidate_id"] for item in result["operator_context"]["relevant_incident_candidates"]] == ["inc-platform"]
    assert result["operator_context"]["incident_source_status"] == "PARTIAL"
    assert result["operator_context"]["trust"]["candidate_is_confirmed_incident"] is False
    assert result["operator_context"]["trust"]["backup_unknown_is_not_unprotected"] is True
    assert result["operator_context"]["trust"]["recovery_test_overdue_claimed"] is False


def test_active_platform_or_target_namespace_candidate_becomes_prechange_verification_not_incident_claim():
    target = {
        "candidate_id": "inc-target",
        "state": "ACTIVE",
        "scope": {"type": "NAMESPACE", "subject": "Namespace/validation"},
        "alert_count": 1,
        "recommended_checks_count": 1,
    }
    result = enrich_deployment_preflight_with_operator_context(_preflight(), _operator(candidates=[target]))

    codes = [item["code"] for item in result["required_live_verification"]]
    assert "VERIFY_ACTIVE_INCIDENT_CONTEXT_BEFORE_CHANGE" in codes
    assert result["safest_next_action"]["code"] == "VERIFY_ACTIVE_INCIDENT_CONTEXT"
    assert result["safest_next_action"]["mutation_allowed"] is False
    assert result["operator_context"]["trust"]["candidate_is_root_cause"] is False


def test_suppressed_candidate_is_visible_but_does_not_trigger_active_incident_gate():
    suppressed = {
        "candidate_id": "inc-suppressed",
        "state": "SUPPRESSED",
        "scope": {"type": "NAMESPACE", "subject": "Namespace/validation"},
        "alert_count": 1,
        "recommended_checks_count": 0,
    }
    result = enrich_deployment_preflight_with_operator_context(
        _preflight(),
        _operator(candidates=[suppressed], attention=[], changes=[], unknowns=[]),
    )

    assert result["operator_context"]["relevant_incident_candidates"][0]["state"] == "SUPPRESSED"
    assert result["operator_context"]["trust"]["suppressed_means_resolved"] is False
    assert "VERIFY_ACTIVE_INCIDENT_CONTEXT_BEFORE_CHANGE" not in [
        item["code"] for item in result["required_live_verification"]
    ]
    assert result["safest_next_action"]["code"] == "COMPLETE_PRE_CHANGE_LIVE_VERIFICATION"


def test_unknown_or_conflict_precedes_operator_attention_in_safest_next_action():
    unknown_result = enrich_deployment_preflight_with_operator_context(
        _preflight(unknowns=[{"code": "COLLECTION_STALE", "statement": "Deployment collection is stale."}]),
        _operator(),
    )
    assert unknown_result["safest_next_action"]["code"] == "REFRESH_OR_REPAIR_REQUIRED_EVIDENCE"

    conflict_result = enrich_deployment_preflight_with_operator_context(
        _preflight(conflicts=[{"code": "RESOURCE_NAME_CONFLICT", "statement": "Deployment exists."}]),
        _operator(candidates=[], attention=[], changes=[], unknowns=[]),
    )
    assert conflict_result["safest_next_action"]["code"] == "RESOLVE_OBSERVED_CHANGE_CONFLICT"


def test_pvc_post_change_requires_authoritative_backup_evidence_without_unprotected_claim():
    result = enrich_deployment_preflight_with_operator_context(
        _preflight(pvc=True),
        _operator(candidates=[], attention=[], changes=[], unknowns=[]),
    )
    codes = [item["code"] for item in result["post_change_verification"]]
    assert "VERIFY_BACKUP_PROTECTION_EVIDENCE_AFTER_CHANGE" in codes
    assert result["operator_context"]["summary"]["backup_unprotected_claims"] == 0
    assert result["operator_context"]["trust"]["backup_unknown_is_not_unprotected"] is True
    assert result["operator_context"]["trust"]["recovery_test_overdue_claimed"] is False


def test_invalid_cluster_scope_or_trust_semantics_fail_closed():
    operator = _operator()
    operator["cluster_id"] = "other"
    with pytest.raises(ValueError, match="same cluster"):
        enrich_deployment_preflight_with_operator_context(_preflight(), operator)

    operator = _operator()
    operator["scope"] = "KUBERNETES_EXISTING_EVIDENCE_ONLY"
    with pytest.raises(ValueError, match="accepted Kubernetes\+backup\+incident scope"):
        enrich_deployment_preflight_with_operator_context(_preflight(), operator)

    operator = _operator()
    operator["incident_candidates"]["trust"]["suppressed_means_resolved"] = True
    with pytest.raises(ValueError, match="must not be treated as resolved"):
        enrich_deployment_preflight_with_operator_context(_preflight(), operator)


def test_markdown_exposes_operator_context_safest_action_and_read_only_trust_boundary():
    result = enrich_deployment_preflight_with_operator_context(_preflight(), _operator())
    rendered = render_operator_aware_preflight_markdown(result)

    assert "## Operator context" in rendered
    assert "## Safest next action" in rendered
    assert "Incident candidates are not confirmed incidents" in rendered
    assert "Suppressed incident candidates are not treated as resolved" in rendered
    assert "Backup UNKNOWN is not treated as UNPROTECTED" in rendered
    assert "Mutation allowed: `false`" in rendered
