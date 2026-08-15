from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from .incident_candidates import render_incident_candidates_markdown
from .io_utils import atomic_write_json, atomic_write_text

DRILLDOWN_POLICY_VERSION = "0.1"
INCIDENT_DRILLDOWN_VERSION = "0.3"
LOG_CHECK_CODE = "CHECK_SCOPE_LOGS_IF_NEEDED"
LOG_TARGET = "LOKI_CANDIDATE"


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if isinstance(value, str) and value))


def _source_evidence_complete(artifact: dict[str, Any]) -> bool:
    status = artifact.get("source_status", {})
    return (
        status.get("alert_attention") == "COMPLETE"
        and status.get("kubernetes_events") == "COMPLETE"
    )


def _log_eligibility(candidate: dict[str, Any], *, source_complete: bool) -> tuple[bool, str]:
    if candidate.get("state") != "ACTIVE":
        return False, "CANDIDATE_NOT_ACTIVE"
    if not source_complete:
        return False, "UPSTREAM_ALERT_OR_EVENT_EVIDENCE_INCOMPLETE"

    scope = candidate.get("scope", {})
    scope_type = scope.get("type")
    impact = candidate.get("impact_context", {})

    if scope_type == "WORKLOAD":
        return True, "DIRECT_WORKLOAD_SCOPE"

    if scope_type == "SERVICE":
        routing = impact.get("service_routing", {})
        if (
            routing.get("selection") == "PREFERRED_ROUTING_EVIDENCE"
            and routing.get("state") == "RESOLVED_WORKLOAD_ROUTING"
            and impact.get("related_workloads_total", 0) > 0
        ):
            return True, "ROUTING_BACKED_SERVICE_WORKLOADS"
        return False, "SERVICE_HAS_NO_PREFERRED_WORKLOAD_ROUTING"

    return False, f"{scope_type or 'UNKNOWN'}_SCOPE_HAS_NO_DEFAULT_LOG_SUBJECT"


def _refine_log_check(check: dict[str, Any], candidate: dict[str, Any], reason: str) -> dict[str, Any]:
    refined = deepcopy(check)
    subject = str(candidate.get("scope", {}).get("subject") or "the candidate scope")
    scope_type = candidate.get("scope", {}).get("type")

    if scope_type == "WORKLOAD":
        refined["check"] = (
            f"If the current alert condition remains unexplained, inspect logs for {subject} around the alert time."
        )
        refined["rationale"] = (
            "This is a concrete workload scope with complete alert and Kubernetes Event evidence; logs may provide additional runtime evidence but are not queried by this slice."
        )
    elif scope_type == "SERVICE" and reason == "ROUTING_BACKED_SERVICE_WORKLOADS":
        workloads = [
            item.get("subject")
            for item in candidate.get("impact_context", {}).get("related_workloads", [])
            if item.get("subject")
        ]
        workload_text = ", ".join(workloads) if workloads else "the observed routed workload backends"
        refined["check"] = (
            f"If the current alert condition remains unexplained, inspect logs for {workload_text} around the alert time."
        )
        refined["rationale"] = (
            "Complete EndpointSlice/Pod/controller routing evidence identifies concrete workload backends for this Service; logs may provide additional runtime evidence but are not queried by this slice."
        )

    return refined


def apply_scope_aware_drilldown(artifact: dict[str, Any]) -> dict[str, Any]:
    """Refine existing incident drill-down checks without performing any live query."""
    result = deepcopy(artifact)
    if result.get("mutation_allowed") is not False:
        raise ValueError("Incident artifact must remain mutation_allowed=false")

    source_complete = _source_evidence_complete(result)
    retained = 0
    removed = 0
    platform_active_without_logs = 0

    for candidate in result.get("candidates", []):
        eligible, reason = _log_eligibility(candidate, source_complete=source_complete)
        refined_checks: list[dict[str, Any]] = []
        had_log_check = False

        for check in candidate.get("recommended_checks", []):
            if check.get("code") == LOG_CHECK_CODE or check.get("target") == LOG_TARGET:
                had_log_check = True
                if eligible:
                    refined_checks.append(_refine_log_check(check, candidate, reason))
                    retained += 1
                else:
                    removed += 1
                continue
            refined_checks.append(deepcopy(check))

        candidate["recommended_checks"] = refined_checks

        if (
            candidate.get("state") == "ACTIVE"
            and candidate.get("scope", {}).get("type") == "PLATFORM"
            and not any(item.get("target") == LOG_TARGET for item in refined_checks)
        ):
            platform_active_without_logs += 1

        caveats = list(candidate.get("caveats", []))
        if had_log_check and not eligible:
            caveats.append(
                f"Default log drill-down was withheld by scope-aware policy: {reason}."
            )
        candidate["caveats"] = _unique(caveats)

    result["incident_candidates_version"] = INCIDENT_DRILLDOWN_VERSION
    result["drilldown_policy"] = {
        "version": DRILLDOWN_POLICY_VERSION,
        "mode": "SCOPE_AWARE",
        "default_log_scopes": ["WORKLOAD", "SERVICE_WITH_PREFERRED_ROUTING"],
        "requires_complete_alert_and_event_evidence": True,
    }

    summary = dict(result.get("summary", {}))
    summary["scope_aware_log_recommendations_retained"] = retained
    summary["scope_aware_log_recommendations_removed"] = removed
    summary["platform_active_candidates_without_default_log_recommendation"] = (
        platform_active_without_logs
    )
    result["summary"] = summary

    recommendation_targets = Counter(
        check.get("target")
        for candidate in result.get("candidates", [])
        for check in candidate.get("recommended_checks", [])
        if check.get("target")
    )
    result["recommended_next_evidence_targets"] = [
        {"target": target, "candidate_checks": count}
        for target, count in sorted(
            recommendation_targets.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    caveats = list(result.get("caveats", []))
    caveats.append(
        "Default log drill-down is scope-aware: it is retained only for direct Workload scope or a Service with complete preferred workload routing, and only when alert and Kubernetes Event evidence are complete. Platform, Namespace, and Node scopes are not assigned a default Loki candidate without a concrete supported log-bearing subject."
    )
    result["caveats"] = _unique(caveats)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply scope-aware derived drill-down recommendations to incident candidates."
    )
    parser.add_argument("--incident", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    artifact = json.loads(args.incident.read_text(encoding="utf-8"))
    refined = apply_scope_aware_drilldown(artifact)
    atomic_write_json(args.incident, refined)
    if args.summary:
        atomic_write_text(args.summary, render_incident_candidates_markdown(refined))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
