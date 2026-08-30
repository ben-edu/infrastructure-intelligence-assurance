from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

ADAPTER_VERSION = "0.1"
DEFAULT_MAX_CANDIDATES = 20
DEFAULT_MAX_VERIFICATIONS = 20


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(value, 0)
    return 0


def _source_status(artifact: dict[str, Any]) -> tuple[str, dict[str, str]]:
    raw = artifact.get("source_status")
    if not isinstance(raw, dict):
        raise ValueError("incident candidates artifact must contain source_status")
    statuses: dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, str) and value:
            statuses[key] = value
    if not statuses:
        raise ValueError("incident candidates source_status must contain named statuses")
    overall = "COMPLETE" if all(value == "COMPLETE" for value in statuses.values()) else "PARTIAL"
    return overall, statuses


def _compact_scope(value: Any) -> dict[str, str | None]:
    if not isinstance(value, dict):
        return {"type": None, "subject": None}
    scope_type = value.get("type") if isinstance(value.get("type"), str) else None
    subject = value.get("subject") if isinstance(value.get("subject"), str) else None
    return {"type": scope_type, "subject": subject}


def _compact_candidates(artifact: dict[str, Any], *, max_candidates: int) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for candidate in artifact.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        state = candidate.get("state") if isinstance(candidate.get("state"), str) else "UNKNOWN"
        result.append(
            {
                "candidate_id": candidate.get("candidate_id") if isinstance(candidate.get("candidate_id"), str) else None,
                "state": state,
                "scope": _compact_scope(candidate.get("scope")),
                "alert_count": _safe_int(candidate.get("alert_count")),
                "related_warning_events_count": len(candidate.get("related_warning_events", []))
                if isinstance(candidate.get("related_warning_events"), list)
                else 0,
                "recent_changes_count": len(candidate.get("recent_changes", []))
                if isinstance(candidate.get("recent_changes"), list)
                else 0,
                "drift_attention_count": len(candidate.get("drift_attention", []))
                if isinstance(candidate.get("drift_attention"), list)
                else 0,
                "recommended_checks_count": len(candidate.get("recommended_checks", []))
                if isinstance(candidate.get("recommended_checks"), list)
                else 0,
            }
        )
        if len(result) >= max_candidates:
            break
    return result


def _compact_required_verification(
    artifact: dict[str, Any],
    *,
    max_verifications: int,
) -> tuple[list[dict[str, Any]], int]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in artifact.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        for item in candidate.get("recommended_checks", []):
            if not isinstance(item, dict) or item.get("live_verification_required") is not True:
                continue
            code = item.get("code") if isinstance(item.get("code"), str) else "INCIDENT_VERIFICATION_REQUIRED"
            target = item.get("target") if isinstance(item.get("target"), str) else "UNKNOWN"
            check = item.get("check") if isinstance(item.get("check"), str) else "Live verification is required before operational action."
            key = (code, target, check)
            if key in seen:
                continue
            seen.add(key)
            if len(result) < max_verifications:
                result.append(
                    {
                        "source": "incident_candidates",
                        "code": code,
                        "target": target,
                        "check": check,
                        "live_verification_required": True,
                    }
                )
    return result, len(seen)


def build_incident_operator_adapter(
    artifact: dict[str, Any],
    *,
    now: datetime | None = None,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    max_verifications: int = DEFAULT_MAX_VERIFICATIONS,
) -> dict[str, Any]:
    """Project compact operator-facing incident evidence without promoting candidates to confirmed incidents."""
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    if max_verifications < 1:
        raise ValueError("max_verifications must be positive")

    cluster_id = artifact.get("cluster_id")
    if not isinstance(cluster_id, str) or not cluster_id:
        raise ValueError("incident candidates artifact must identify a cluster")

    summary = artifact.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("incident candidates artifact must contain a summary object")

    overall_status, source_statuses = _source_status(artifact)

    incident_candidates = _safe_int(summary.get("incident_candidates"))
    active_candidates = _safe_int(summary.get("active_candidates"))
    suppressed_candidates = _safe_int(summary.get("suppressed_candidates"))
    unknown_candidates = _safe_int(summary.get("unknown_candidates"))
    related_events = _safe_int(summary.get("candidates_with_related_warning_events"))
    exact_recent_change = _safe_int(summary.get("candidates_with_exact_recent_change"))
    exact_drift = _safe_int(summary.get("candidates_with_exact_drift"))
    requiring_verification = _safe_int(summary.get("candidates_requiring_live_verification"))

    attention: list[dict[str, Any]] = []
    if overall_status != "COMPLETE":
        attention.append(
            {
                "source": "incident_candidates",
                "code": "INCIDENT_SOURCE_INCOMPLETE",
                "severity": "UNKNOWN",
                "count": sum(1 for value in source_statuses.values() if value != "COMPLETE"),
                "statement": "One or more incident-candidate source domains are incomplete; candidate absence is not negative evidence.",
            }
        )
    if active_candidates:
        attention.append(
            {
                "source": "incident_candidates",
                "code": "ACTIVE_INCIDENT_CANDIDATES",
                "severity": "SIGNAL",
                "count": active_candidates,
                "statement": "One or more active incident candidates group current signals by identical supported scope; candidates are not confirmed incidents or root causes.",
            }
        )
    if unknown_candidates:
        attention.append(
            {
                "source": "incident_candidates",
                "code": "INCIDENT_CANDIDATE_STATE_UNKNOWN",
                "severity": "UNKNOWN",
                "count": unknown_candidates,
                "statement": "One or more incident candidates have unknown handling state.",
            }
        )

    compact_candidates = _compact_candidates(artifact, max_candidates=max_candidates)
    required, required_total = _compact_required_verification(
        artifact,
        max_verifications=max_verifications,
    )
    now = now or datetime.now(timezone.utc)

    return {
        "incident_operator_adapter_version": ADAPTER_VERSION,
        "generated_at": _rfc3339(now),
        "cluster_id": cluster_id,
        "mutation_allowed": False,
        "scope": "INCIDENT_CANDIDATES_EXISTING_EVIDENCE_ONLY",
        "source_status": overall_status,
        "source_statuses": source_statuses,
        "summary": {
            "incident_candidates": incident_candidates,
            "active_candidates": active_candidates,
            "suppressed_candidates": suppressed_candidates,
            "unknown_candidates": unknown_candidates,
            "candidates_with_related_warning_events": related_events,
            "candidates_with_exact_recent_change": exact_recent_change,
            "candidates_with_exact_drift": exact_drift,
            "candidates_requiring_live_verification": requiring_verification,
            "attention_total": len(attention),
            "required_verification_categories_total": required_total,
            "projected_candidates": len(compact_candidates),
        },
        "attention": attention,
        "candidates": compact_candidates,
        "required_live_verification": required,
        "source_artifacts": ["incident-candidates.json"],
        "truncation": {
            "candidates_truncated": incident_candidates > len(compact_candidates),
            "required_live_verification_truncated": required_total > len(required),
        },
        "trust": {
            "candidate_is_confirmed_incident": False,
            "candidate_is_root_cause": False,
            "suppressed_means_resolved": False,
            "live_verification_required_before_action": True,
        },
    }
