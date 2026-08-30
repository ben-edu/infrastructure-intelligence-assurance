from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_json, atomic_write_text
from .operator_attention import load_json_artifact
from .operator_attention_incident import CROSS_DOMAIN_SCOPE
from .planning_preflight import build_deployment_preflight, render_preflight_markdown

INTEGRATION_VERSION = "0.1"
INTEGRATION_SCOPE = "KUBERNETES_DEPLOYMENT_PREFLIGHT_WITH_OPERATOR_CONTEXT"


def _subject_matches_namespace(subject: Any, namespace: str) -> bool:
    if not isinstance(subject, str) or not subject:
        return False
    return subject == f"Namespace/{namespace}" or f"/{namespace}/" in subject


def _compact_attention(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": item.get("source") if isinstance(item.get("source"), str) else None,
        "code": item.get("code") if isinstance(item.get("code"), str) else "ATTENTION",
        "severity": item.get("severity") if isinstance(item.get("severity"), str) else "UNKNOWN",
        "subject": item.get("subject") if isinstance(item.get("subject"), str) else None,
        "statement": item.get("statement") if isinstance(item.get("statement"), str) else None,
    }


def _compact_change(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "classification": item.get("classification") if isinstance(item.get("classification"), str) else "UNKNOWN",
        "subject": item.get("subject") if isinstance(item.get("subject"), str) else None,
    }


def _compact_unknown(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": item.get("source") if isinstance(item.get("source"), str) else None,
        "code": item.get("code") if isinstance(item.get("code"), str) else "UNKNOWN_EVIDENCE",
        "subject": item.get("subject") if isinstance(item.get("subject"), str) else None,
        "statement": item.get("statement") if isinstance(item.get("statement"), str) else None,
    }


def _incident_candidate_relevant(candidate: dict[str, Any], namespace: str) -> bool:
    scope = candidate.get("scope")
    if not isinstance(scope, dict):
        return False
    scope_type = scope.get("type")
    subject = scope.get("subject")
    if scope_type == "PLATFORM":
        return True
    return _subject_matches_namespace(subject, namespace)


def _compact_incident_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    scope = candidate.get("scope") if isinstance(candidate.get("scope"), dict) else {}
    return {
        "candidate_id": candidate.get("candidate_id") if isinstance(candidate.get("candidate_id"), str) else None,
        "state": candidate.get("state") if isinstance(candidate.get("state"), str) else "UNKNOWN",
        "scope_type": scope.get("type") if isinstance(scope.get("type"), str) else None,
        "subject": scope.get("subject") if isinstance(scope.get("subject"), str) else None,
        "alert_count": int(candidate.get("alert_count", 0) or 0),
        "related_warning_events_count": int(candidate.get("related_warning_events_count", 0) or 0),
        "recommended_checks_count": int(candidate.get("recommended_checks_count", 0) or 0),
    }


def _verification(code: str, check: str, reason: str) -> dict[str, Any]:
    return {"code": code, "check": check, "reason": reason, "evidence_ids": []}


def _statement(code: str, statement: str) -> dict[str, Any]:
    return {"code": code, "statement": statement, "evidence_ids": []}


def _dedupe_by_code_and_text(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any]] = set()
    for item in items:
        key = (item.get("code"), item.get("check"), item.get("statement"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _safest_next_action(
    preflight: dict[str, Any],
    *,
    relevant_attention: list[dict[str, Any]],
    active_incidents: list[dict[str, Any]],
) -> dict[str, Any]:
    if preflight.get("unknowns"):
        first = preflight["unknowns"][0]
        return {
            "code": "REFRESH_OR_REPAIR_REQUIRED_EVIDENCE",
            "action": "Resolve the first unknown, stale, failed, or mismatched evidence condition before change review.",
            "reason": first.get("statement") or first.get("code"),
            "live_verification_required": True,
            "mutation_allowed": False,
        }
    if preflight.get("conflicts"):
        first = preflight["conflicts"][0]
        return {
            "code": "RESOLVE_OBSERVED_CHANGE_CONFLICT",
            "action": "Resolve the first observed current-state conflict before considering the candidate change.",
            "reason": first.get("statement") or first.get("code"),
            "live_verification_required": True,
            "mutation_allowed": False,
        }
    if active_incidents:
        first = active_incidents[0]
        subject = first.get("subject") or first.get("scope_type") or "current platform scope"
        return {
            "code": "VERIFY_ACTIVE_INCIDENT_CONTEXT",
            "action": f"Verify the active incident-candidate condition for {subject} is current and understood before approving the change.",
            "reason": "Active incident candidates are signal groupings, not confirmed incidents or root causes, but overlapping platform or target-namespace conditions must be verified before change approval.",
            "live_verification_required": True,
            "mutation_allowed": False,
        }
    if relevant_attention:
        first = relevant_attention[0]
        return {
            "code": "VERIFY_RELEVANT_OPERATOR_ATTENTION",
            "action": "Verify the first operator-attention condition intersecting the target namespace before change approval.",
            "reason": first.get("statement") or first.get("code"),
            "live_verification_required": True,
            "mutation_allowed": False,
        }
    required = preflight.get("required_live_verification", [])
    if required:
        first = required[0]
        return {
            "code": "COMPLETE_PRE_CHANGE_LIVE_VERIFICATION",
            "action": first.get("check") or "Complete the required live verification before change approval.",
            "reason": first.get("reason") or "The candidate plan remains non-executable until required verification is complete.",
            "live_verification_required": True,
            "mutation_allowed": False,
        }
    return {
        "code": "REVIEW_NON_EXECUTABLE_CANDIDATE_PLAN",
        "action": "Review the non-executable candidate plan and its trust boundary before any future approval workflow.",
        "reason": "This planning artifact does not authorize infrastructure mutation.",
        "live_verification_required": False,
        "mutation_allowed": False,
    }


def enrich_deployment_preflight_with_operator_context(
    preflight: dict[str, Any],
    operator_attention: dict[str, Any],
) -> dict[str, Any]:
    """Enrich an accepted deployment preflight with compact current operator context."""
    if preflight.get("mutation_allowed") is not False:
        raise ValueError("planning preflight must preserve mutation_allowed=false")
    if operator_attention.get("mutation_allowed") is not False:
        raise ValueError("operator attention must preserve mutation_allowed=false")
    if operator_attention.get("scope") != CROSS_DOMAIN_SCOPE:
        raise ValueError("operator attention must use the accepted Kubernetes+backup+incident scope")
    if preflight.get("cluster_id") != operator_attention.get("cluster_id"):
        raise ValueError("planning preflight and operator attention must target the same cluster")

    request = preflight.get("request")
    if not isinstance(request, dict) or not isinstance(request.get("namespace"), str):
        raise ValueError("planning preflight must contain a target namespace")
    namespace = request["namespace"]

    relevant_attention = [
        _compact_attention(item)
        for item in operator_attention.get("attention_now", [])
        if isinstance(item, dict) and _subject_matches_namespace(item.get("subject"), namespace)
    ]
    relevant_changes = [
        _compact_change(item)
        for item in operator_attention.get("recent_changes", [])
        if isinstance(item, dict) and _subject_matches_namespace(item.get("subject"), namespace)
    ]
    relevant_unknowns = [
        _compact_unknown(item)
        for item in operator_attention.get("unknowns", [])
        if isinstance(item, dict) and _subject_matches_namespace(item.get("subject"), namespace)
    ]

    incident = operator_attention.get("incident_candidates")
    if not isinstance(incident, dict):
        raise ValueError("operator attention must contain compact incident-candidate context")
    incident_trust = incident.get("trust")
    if not isinstance(incident_trust, dict):
        raise ValueError("operator attention incident context must contain trust metadata")
    if incident_trust.get("candidate_is_confirmed_incident") is not False:
        raise ValueError("incident candidates must not be promoted to confirmed incidents")
    if incident_trust.get("candidate_is_root_cause") is not False:
        raise ValueError("incident candidates must not be promoted to root cause")
    if incident_trust.get("suppressed_means_resolved") is not False:
        raise ValueError("suppressed incident candidates must not be treated as resolved")

    relevant_incidents = [
        _compact_incident_candidate(item)
        for item in incident.get("candidates", [])
        if isinstance(item, dict) and _incident_candidate_relevant(item, namespace)
    ]
    active_incidents = [item for item in relevant_incidents if item.get("state") == "ACTIVE"]

    result = dict(preflight)
    result["operator_context_integration_version"] = INTEGRATION_VERSION
    result["scope"] = INTEGRATION_SCOPE

    summary = operator_attention.get("summary") if isinstance(operator_attention.get("summary"), dict) else {}
    backup = operator_attention.get("backup_assurance") if isinstance(operator_attention.get("backup_assurance"), dict) else {}
    backup_trust = backup.get("trust") if isinstance(backup.get("trust"), dict) else {}
    result["operator_context"] = {
        "source_scope": operator_attention.get("scope"),
        "generated_at": operator_attention.get("generated_at"),
        "target_namespace": namespace,
        "summary": {
            "attention_now_total": int(summary.get("attention_now_total", 0) or 0),
            "recent_changes_total": int(summary.get("recent_changes_total", 0) or 0),
            "unknowns_total": int(summary.get("unknowns_total", 0) or 0),
            "required_live_verification_total": int(summary.get("required_live_verification_total", 0) or 0),
            "backup_assets_total": int(summary.get("backup_assets_total", 0) or 0),
            "backup_protection_unknown": int(summary.get("backup_protection_unknown", 0) or 0),
            "backup_restore_verification_unknown": int(summary.get("backup_restore_verification_unknown", 0) or 0),
            "backup_unprotected_claims": int(summary.get("backup_unprotected_claims", 0) or 0),
            "incident_candidates_total": int(summary.get("incident_candidates_total", 0) or 0),
            "incident_active_candidates": int(summary.get("incident_active_candidates", 0) or 0),
            "incident_suppressed_candidates": int(summary.get("incident_suppressed_candidates", 0) or 0),
        },
        "relevant_attention": relevant_attention,
        "relevant_recent_changes": relevant_changes,
        "relevant_unknowns": relevant_unknowns,
        "relevant_incident_candidates": relevant_incidents,
        "incident_source_status": incident.get("source_status"),
        "truncation": dict(operator_attention.get("truncation", {})) if isinstance(operator_attention.get("truncation"), dict) else {},
        "trust": {
            "candidate_is_confirmed_incident": False,
            "candidate_is_root_cause": False,
            "suppressed_means_resolved": False,
            "live_verification_required_before_action": incident_trust.get("live_verification_required_before_action") is True,
            "backup_unknown_is_not_unprotected": backup_trust.get("unknown_is_not_unprotected") is True,
            "recovery_test_overdue_claimed": backup_trust.get("recovery_test_overdue_claimed") is True,
        },
    }

    inferences = list(preflight.get("inferences", []))
    for item in relevant_attention:
        inferences.append(
            _statement(
                "RELEVANT_OPERATOR_ATTENTION",
                f"Current operator attention intersects the target namespace: {item.get('code')} — {item.get('subject') or namespace}.",
            )
        )
    for item in relevant_changes:
        inferences.append(
            _statement(
                "RELEVANT_RECENT_CHANGE",
                f"A recent change intersects the target namespace: {item.get('classification')} — {item.get('subject') or namespace}.",
            )
        )
    for item in relevant_unknowns:
        inferences.append(
            _statement(
                "RELEVANT_OPERATOR_UNKNOWN",
                f"Current operator evidence contains an unknown state intersecting the target namespace: {item.get('code')}.",
            )
        )
    for candidate in active_incidents:
        inferences.append(
            _statement(
                "RELEVANT_ACTIVE_INCIDENT_CANDIDATE",
                f"An ACTIVE incident candidate overlaps the planned change scope ({candidate.get('subject') or candidate.get('scope_type')}); this is not incident confirmation or root-cause proof.",
            )
        )
    result["inferences"] = _dedupe_by_code_and_text(inferences)

    required = list(preflight.get("required_live_verification", []))
    for candidate in active_incidents:
        required.append(
            _verification(
                "VERIFY_ACTIVE_INCIDENT_CONTEXT_BEFORE_CHANGE",
                f"Verify the ACTIVE incident-candidate condition for {candidate.get('subject') or candidate.get('scope_type')} is current and understood before approving the change.",
                "An overlapping active signal group can increase change risk, but the candidate is not itself a confirmed incident or root cause.",
            )
        )
    for item in relevant_unknowns:
        required.append(
            _verification(
                "VERIFY_RELEVANT_OPERATOR_UNKNOWN_BEFORE_CHANGE",
                f"Resolve or freshly verify the operator unknown {item.get('code')} for {item.get('subject') or namespace}.",
                "Unknown operator evidence intersecting the target namespace must not be treated as a healthy or absent condition.",
            )
        )
    result["required_live_verification"] = _dedupe_by_code_and_text(required)

    post_change = list(preflight.get("post_change_verification", []))
    post_change.append(
        _statement(
            "VERIFY_OPERATOR_ATTENTION_AFTER_CHANGE",
            "After an approved future change, regenerate operator attention and verify that no new target-scope attention, unknown state, or active incident candidate was introduced.",
        )
    )
    if request.get("pvc"):
        post_change.append(
            _statement(
                "VERIFY_BACKUP_PROTECTION_EVIDENCE_AFTER_CHANGE",
                "After an approved future stateful change, collect authoritative backup/recovery evidence for the new state before describing it as protected or recoverable.",
            )
        )
    result["post_change_verification"] = _dedupe_by_code_and_text(post_change)

    result["safest_next_action"] = _safest_next_action(
        result,
        relevant_attention=relevant_attention,
        active_incidents=active_incidents,
    )
    return result


def build_deployment_preflight_with_operator_context(
    snapshot: dict[str, Any],
    operational_context: dict[str, Any],
    topology: dict[str, Any],
    operator_attention: dict[str, Any],
    request: dict[str, Any],
    *,
    now: Any = None,
) -> dict[str, Any]:
    base = build_deployment_preflight(snapshot, operational_context, topology, request, now=now)
    return enrich_deployment_preflight_with_operator_context(base, operator_attention)


def render_operator_aware_preflight_markdown(preflight: dict[str, Any]) -> str:
    rendered = render_preflight_markdown(preflight)
    operator = preflight["operator_context"]
    action = preflight["safest_next_action"]
    block = "\n".join(
        [
            "## Operator context",
            "",
            f"- Source scope: `{operator['source_scope']}`",
            f"- Incident source status: `{operator['incident_source_status']}`",
            f"- Relevant attention: {len(operator['relevant_attention'])}",
            f"- Relevant recent changes: {len(operator['relevant_recent_changes'])}",
            f"- Relevant unknowns: {len(operator['relevant_unknowns'])}",
            f"- Relevant incident candidates: {len(operator['relevant_incident_candidates'])}",
            "- Incident candidates are not confirmed incidents or root-cause conclusions.",
            "- Suppressed incident candidates are not treated as resolved.",
            "- Backup UNKNOWN is not treated as UNPROTECTED.",
            "",
            "## Safest next action",
            "",
            f"- [{action['code']}] {action['action']}",
            f"  Reason: {action['reason']}",
            "- Mutation allowed: `false`",
            "",
        ]
    )
    return rendered.replace("\n## Trust boundary\n", f"\n{block}\n## Trust boundary\n", 1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the existing read-only deployment preflight enriched with accepted operator-attention evidence."
    )
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--topology", type=Path, required=True)
    parser.add_argument("--operator-attention", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args()

    request = json.loads(args.request.read_text(encoding="utf-8"))
    summary = build_deployment_preflight_with_operator_context(
        load_json_artifact(args.evidence),
        load_json_artifact(args.context),
        load_json_artifact(args.topology),
        load_json_artifact(args.operator_attention),
        request,
    )
    atomic_write_json(args.out, summary)
    if args.summary_out:
        atomic_write_text(args.summary_out, render_operator_aware_preflight_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
