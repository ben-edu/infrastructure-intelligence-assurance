from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from infra_assurance.scope_aware_drilldown import apply_scope_aware_drilldown

ROOT = Path(__file__).resolve().parents[1]


def _check(code: str, target: str) -> dict:
    return {
        "code": code,
        "target": target,
        "check": f"check {code}",
        "rationale": f"rationale {code}",
        "live_verification_required": True,
        "evidence_ids": [f"ev-{code}"],
    }


def _candidate(
    scope_type: str,
    subject: str,
    *,
    state: str = "ACTIVE",
    with_log: bool = True,
    related_workloads: list[str] | None = None,
    service_selection: str | None = None,
    service_state: str = "RESOLVED_WORKLOAD_ROUTING",
) -> dict:
    workloads = [
        {
            "subject": value,
            "basis": ["ENDPOINTSLICE_POD_CONTROLLER_OWNER_ROUTING"],
            "observed_freshness": "CURRENT",
            "declared_coverage": "OUTSIDE_DECLARED_SCOPE",
            "declared_comparison": None,
            "prometheus_runtime_state": "NO_RUNTIME_SIGNAL_MATCH",
            "evidence_ids": [f"ev-{value}"],
        }
        for value in (related_workloads or [])
    ]
    impact = {
        "related_workloads_total": len(workloads),
        "related_workloads": workloads,
        "related_workloads_truncated": False,
        "ingress_route_candidates": [],
        "ingress_route_candidates_truncated": False,
        "persistent_volume_claims": [],
        "persistent_volume_claims_truncated": False,
        "platform_context": (
            {"workloads_total": 68, "namespaces_total": 19}
            if scope_type == "PLATFORM"
            else None
        ),
        "basis": [],
        "caveat": "test context",
    }
    if scope_type == "SERVICE":
        impact["service_routing"] = {
            "source_status": "COMPLETE",
            "service": subject,
            "state": service_state,
            "scope_completeness": "COMPLETE",
            "selection": service_selection or "NO_WORKLOAD_ROUTING_CLAIM",
            "resolved_workloads": list(related_workloads or []),
            "evidence_ids": ["ev-routing"],
        }

    checks = [_check("VERIFY_ALERT_CONDITION_CURRENT", "PROMETHEUS_ALERTMANAGER")]
    if with_log:
        checks.append(_check("CHECK_SCOPE_LOGS_IF_NEEDED", "LOKI_CANDIDATE"))
    if scope_type == "PLATFORM":
        checks.append(_check("VERIFY_PLATFORM_SIGNAL_INPUTS", "PROMETHEUS_KUBERNETES"))

    return {
        "candidate_id": f"candidate-{scope_type.lower()}",
        "scope": {"type": scope_type, "subject": subject, "basis": ["TEST"]},
        "state": state,
        "alert_count": 1,
        "alerts": [],
        "event_correlation_statuses": ["NO_DIRECT_EVENT_MATCH"],
        "related_warning_events": [],
        "recent_changes": [],
        "drift_attention": [],
        "impact_context": impact,
        "recommended_checks": checks,
        "evidence_ids": ["ev-candidate"],
        "caveats": [],
    }


def _artifact(*candidates: dict, alert_status: str = "COMPLETE", event_status: str = "COMPLETE") -> dict:
    return {
        "incident_candidates_version": "0.2",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T13:13:29Z",
        "mutation_allowed": False,
        "source_status": {
            "alert_attention": alert_status,
            "kubernetes_events": event_status,
            "change_context": "COMPLETE",
            "drift": "EVALUATED",
            "inventory": "COMPLETE",
            "routing_ownership": "COMPLETE",
        },
        "summary": {
            "alert_attention_records": len(candidates),
            "incident_candidates": len(candidates),
            "active_candidates": sum(x["state"] == "ACTIVE" for x in candidates),
            "suppressed_candidates": sum(x["state"] == "SUPPRESSED" for x in candidates),
            "unknown_candidates": sum(x["state"] == "UNKNOWN" for x in candidates),
            "candidates_with_related_warning_events": 0,
            "candidates_with_exact_recent_change": 0,
            "candidates_with_exact_drift": 0,
            "candidates_with_related_workloads": sum(
                x["impact_context"]["related_workloads_total"] > 0 for x in candidates
            ),
            "candidates_requiring_live_verification": len(candidates),
            "service_candidates_with_preferred_routing": 0,
            "service_candidates_without_workload_routing_claim": 0,
        },
        "recommended_next_evidence_targets": [],
        "candidates": list(candidates),
        "unassociated_change_unknowns": [],
        "unassociated_required_live_verification": [],
        "caveats": [],
    }


def _codes(candidate: dict) -> set[str]:
    return {x["code"] for x in candidate["recommended_checks"]}


def _targets(artifact: dict) -> set[str]:
    return {x["target"] for x in artifact["recommended_next_evidence_targets"]}


def test_platform_active_candidate_drops_generic_log_recommendation():
    artifact = _artifact(
        _candidate("PLATFORM", "Platform/k3s-main")
    )
    result = apply_scope_aware_drilldown(artifact)
    candidate = result["candidates"][0]

    assert result["incident_candidates_version"] == "0.3"
    assert "VERIFY_ALERT_CONDITION_CURRENT" in _codes(candidate)
    assert "VERIFY_PLATFORM_SIGNAL_INPUTS" in _codes(candidate)
    assert "CHECK_SCOPE_LOGS_IF_NEEDED" not in _codes(candidate)
    assert "LOKI_CANDIDATE" not in _targets(result)
    assert "PROMETHEUS_ALERTMANAGER" in _targets(result)
    assert "PROMETHEUS_KUBERNETES" in _targets(result)
    assert result["summary"]["platform_active_candidates_without_default_log_recommendation"] == 1


def test_workload_scope_retains_and_refines_log_recommendation():
    result = apply_scope_aware_drilldown(
        _artifact(_candidate("WORKLOAD", "Deployment/apps/api"))
    )
    candidate = result["candidates"][0]
    log_check = next(x for x in candidate["recommended_checks"] if x["target"] == "LOKI_CANDIDATE")

    assert "Deployment/apps/api" in log_check["check"]
    assert result["summary"]["scope_aware_log_recommendations_retained"] == 1
    assert "LOKI_CANDIDATE" in _targets(result)


def test_service_scope_retains_logs_only_with_preferred_complete_workload_routing():
    preferred = _candidate(
        "SERVICE",
        "Service/apps/api",
        related_workloads=["Deployment/apps/api"],
        service_selection="PREFERRED_ROUTING_EVIDENCE",
    )
    result = apply_scope_aware_drilldown(_artifact(preferred))
    log_check = next(x for x in result["candidates"][0]["recommended_checks"] if x["target"] == "LOKI_CANDIDATE")
    assert "Deployment/apps/api" in log_check["check"]

    fallback = _candidate(
        "SERVICE",
        "Service/apps/api",
        related_workloads=["Deployment/apps/api"],
        service_selection="SELECTOR_INFERENCE_FALLBACK",
    )
    fallback_result = apply_scope_aware_drilldown(_artifact(fallback))
    assert "CHECK_SCOPE_LOGS_IF_NEEDED" not in _codes(fallback_result["candidates"][0])


def test_non_pod_service_never_gets_default_log_recommendation():
    candidate = _candidate(
        "SERVICE",
        "Service/kube-system/kube-prom-stack-kubelet",
        service_selection="NO_WORKLOAD_ROUTING_CLAIM",
        service_state="NON_POD_ROUTING",
    )
    result = apply_scope_aware_drilldown(_artifact(candidate))
    assert "LOKI_CANDIDATE" not in _targets(result)
    assert "CHECK_SCOPE_LOGS_IF_NEEDED" not in _codes(result["candidates"][0])


def test_namespace_and_node_scopes_do_not_get_default_log_recommendations():
    result = apply_scope_aware_drilldown(
        _artifact(
            _candidate("NAMESPACE", "Namespace/monitoring"),
            _candidate("NODE", "Node/k3s-worker-01"),
        )
    )
    assert all("CHECK_SCOPE_LOGS_IF_NEEDED" not in _codes(x) for x in result["candidates"])
    assert "LOKI_CANDIDATE" not in _targets(result)


def test_incomplete_alert_or_event_evidence_withholds_log_drilldown_even_for_workload():
    workload = _candidate("WORKLOAD", "Deployment/apps/api")
    partial_alert = apply_scope_aware_drilldown(
        _artifact(deepcopy(workload), alert_status="PARTIAL")
    )
    partial_event = apply_scope_aware_drilldown(
        _artifact(deepcopy(workload), event_status="PARTIAL")
    )
    assert "LOKI_CANDIDATE" not in _targets(partial_alert)
    assert "LOKI_CANDIDATE" not in _targets(partial_event)


def test_event_change_and_drift_checks_are_preserved_unchanged():
    candidate = _candidate("PLATFORM", "Platform/k3s-main")
    preserved = [
        _check("VERIFY_RELATED_EVENT_OBJECT_STATE", "KUBERNETES_OBJECT"),
        _check("REVIEW_EXACT_RECENT_CHANGE", "KUBERNETES_HISTORY"),
        _check("VERIFY_EXACT_DECLARED_OBSERVED_DRIFT", "GIT_AND_KUBERNETES"),
    ]
    candidate["recommended_checks"].extend(deepcopy(preserved))

    result = apply_scope_aware_drilldown(_artifact(candidate))
    by_code = {x["code"]: x for x in result["candidates"][0]["recommended_checks"]}
    for original in preserved:
        assert by_code[original["code"]] == original


def test_policy_does_not_invent_a_log_check_when_builder_did_not_emit_one():
    candidate = _candidate("WORKLOAD", "Deployment/apps/api", with_log=False)
    result = apply_scope_aware_drilldown(_artifact(candidate))
    assert "CHECK_SCOPE_LOGS_IF_NEEDED" not in _codes(result["candidates"][0])
    assert "LOKI_CANDIDATE" not in _targets(result)


def test_scope_aware_output_validates_extension_schema():
    result = apply_scope_aware_drilldown(
        _artifact(_candidate("PLATFORM", "Platform/k3s-main"))
    )
    schema = json.loads(
        (ROOT / "schemas" / "incident-scope-aware-drilldown.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(result)
    assert result["mutation_allowed"] is False
    assert result["drilldown_policy"]["mode"] == "SCOPE_AWARE"
