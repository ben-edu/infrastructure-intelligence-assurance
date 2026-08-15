from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from .incident_candidates import render_incident_candidates_markdown
from .io_utils import atomic_write_json, atomic_write_text

RULE_INTEGRATION_VERSION = "0.1"
INCIDENT_RULE_CONTEXT_VERSION = "0.4"
REQUIRED_INCIDENT_VERSION = "0.3"
REQUIRED_RULE_CONTEXT_VERSION = "0.1"
GENERIC_PLATFORM_CODE = "VERIFY_PLATFORM_SIGNAL_INPUTS"
GENERIC_PLATFORM_TARGET = "PROMETHEUS_KUBERNETES"
RULE_INPUT_CODE = "VERIFY_PROMETHEUS_RULE_INPUTS"
RULE_INPUT_TARGET = "PROMETHEUS_RULE_INPUTS"

_ALLOWED_RULE_FIELDS = (
    "rule_id",
    "evidence_id",
    "alertname",
    "group_name",
    "rule_type",
    "state",
    "health",
    "duration_seconds",
    "keep_firing_for_seconds",
    "evaluation_time_seconds",
    "last_evaluation",
    "expression_persisted",
)


def _unique(values: list[str]) -> list[str]:
    return list(
        dict.fromkeys(
            value
            for value in values
            if isinstance(value, str) and value
        )
    )


def _candidate_alert_names(candidate: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(alert.get("alertname"))
            for alert in candidate.get("alerts", [])
            if isinstance(alert.get("alertname"), str)
            and alert.get("alertname")
        }
    )


def _rule_projection(rule: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(rule.get(field)) for field in _ALLOWED_RULE_FIELDS}


def _context_selection(
    *,
    source_status: str,
    candidate: dict[str, Any],
    context: dict[str, Any] | None,
    rules_by_id: dict[str, dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], list[str], list[str]]:
    candidate_names = _candidate_alert_names(candidate)

    if source_status != "COMPLETE":
        return "SOURCE_INCOMPLETE", [], candidate_names, []

    if context is None:
        return "CANDIDATE_CONTEXT_NOT_OBSERVED", [], candidate_names, []

    context_names = sorted(
        name
        for name in context.get("alert_names", [])
        if isinstance(name, str) and name
    )
    if context_names != candidate_names:
        return "CANDIDATE_ALERT_SET_MISMATCH", [], candidate_names, []

    unmatched = sorted(
        name
        for name in context.get("unmatched_alert_names", [])
        if isinstance(name, str) and name
    )
    matched_ids = sorted(
        rule_id
        for rule_id in context.get("matched_rule_ids", [])
        if isinstance(rule_id, str) and rule_id
    )
    matched_rules = [
        _rule_projection(rules_by_id[rule_id])
        for rule_id in matched_ids
        if rule_id in rules_by_id
    ]
    missing_rule_ids = [
        rule_id for rule_id in matched_ids if rule_id not in rules_by_id
    ]

    if missing_rule_ids:
        return "MATCHED_RULE_RECORD_MISSING", [], unmatched, missing_rule_ids

    matched_names = sorted(
        {
            str(rule.get("alertname"))
            for rule in matched_rules
            if isinstance(rule.get("alertname"), str)
            and rule.get("alertname")
        }
    )

    if unmatched:
        return "PARTIAL_EXACT_RULE_MATCH", matched_rules, unmatched, []

    if not matched_rules:
        return "NO_EXACT_RULE_MATCH", [], candidate_names, []

    if matched_names != candidate_names:
        return "RULE_ALERT_SET_MISMATCH", matched_rules, candidate_names, []

    return "COMPLETE_EXACT_RULE_MATCH", matched_rules, [], []


def _integration_context(
    *,
    source_status: str,
    candidate: dict[str, Any],
    context: dict[str, Any] | None,
    rules_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    selection, matched_rules, unmatched, missing_rule_ids = _context_selection(
        source_status=source_status,
        candidate=candidate,
        context=context,
        rules_by_id=rules_by_id,
    )
    evidence_ids = _unique(
        [
            rule.get("evidence_id")
            for rule in matched_rules
            if rule.get("evidence_id")
        ]
    )
    return {
        "source_status": source_status,
        "selection": selection,
        "alert_names": _candidate_alert_names(candidate),
        "matched_rules": matched_rules,
        "unmatched_alert_names": unmatched,
        "missing_rule_ids": missing_rule_ids,
        "basis": (
            ["CANDIDATE_ID", "EXACT_ALERTNAME_PROMETHEUS_RULE_MATCH"]
            if selection == "COMPLETE_EXACT_RULE_MATCH"
            else []
        ),
        "required_live_verification": (
            [
                {
                    "target": RULE_INPUT_TARGET,
                    "statement": (
                        "Exact Prometheus rule metadata is observed, but current "
                        "rule-input metric values are not collected and require "
                        "separate live verification before causal interpretation."
                    ),
                }
            ]
            if selection == "COMPLETE_EXACT_RULE_MATCH"
            else []
        ),
        "evidence_ids": evidence_ids,
    }


def _refine_platform_recommendations(
    candidate: dict[str, Any],
    *,
    rule_context: dict[str, Any],
) -> int:
    if candidate.get("state") != "ACTIVE":
        return 0
    if candidate.get("scope", {}).get("type") != "PLATFORM":
        return 0
    if rule_context.get("selection") != "COMPLETE_EXACT_RULE_MATCH":
        return 0

    refined: list[dict[str, Any]] = []
    replaced = 0
    for check in candidate.get("recommended_checks", []):
        if (
            check.get("code") == GENERIC_PLATFORM_CODE
            and check.get("target") == GENERIC_PLATFORM_TARGET
        ):
            evidence_ids = _unique(
                list(check.get("evidence_ids", []))
                + list(rule_context.get("evidence_ids", []))
            )
            refined.append(
                {
                    "code": RULE_INPUT_CODE,
                    "target": RULE_INPUT_TARGET,
                    "check": (
                        "Verify the current metric inputs for the exact matched "
                        "Prometheus alert rules before causal interpretation."
                    ),
                    "rationale": (
                        "Complete exact rule metadata is available for the current "
                        "active alert names, but the PromQL expressions and current "
                        "input metric values are intentionally not collected by the "
                        "accepted rule-context source."
                    ),
                    "live_verification_required": True,
                    "evidence_ids": evidence_ids,
                }
            )
            replaced += 1
            continue
        refined.append(deepcopy(check))

    candidate["recommended_checks"] = refined
    return replaced


def _unknown_for_context(
    candidate: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any] | None:
    selection = context.get("selection")
    if selection == "COMPLETE_EXACT_RULE_MATCH":
        return None

    subject = candidate.get("scope", {}).get("subject")
    statements = {
        "SOURCE_INCOMPLETE": (
            "Prometheus rule context was not COMPLETE; generic Platform "
            "verification is retained and no exact rule metadata is promoted."
        ),
        "CANDIDATE_CONTEXT_NOT_OBSERVED": (
            "No candidate-specific Prometheus rule context was observed for this "
            "active candidate."
        ),
        "CANDIDATE_ALERT_SET_MISMATCH": (
            "The active candidate alert-name set did not exactly match the "
            "candidate context produced by the Prometheus rule source."
        ),
        "MATCHED_RULE_RECORD_MISSING": (
            "Candidate rule context referenced a rule ID that was not present in "
            "the accepted rule artifact."
        ),
        "PARTIAL_EXACT_RULE_MATCH": (
            "At least one active candidate alert name had no exact matched "
            "Prometheus rule record."
        ),
        "NO_EXACT_RULE_MATCH": (
            "No exact Prometheus rule record matched the active candidate alert names."
        ),
        "RULE_ALERT_SET_MISMATCH": (
            "Matched Prometheus rule records did not cover the exact active "
            "candidate alert-name set."
        ),
    }
    statement = statements.get(str(selection))
    if not statement:
        return None
    return {
        "code": f"PROMETHEUS_RULE_INTEGRATION_{selection}",
        "subject": subject,
        "statement": statement,
        "evidence_ids": list(context.get("evidence_ids", [])),
    }


def integrate_prometheus_rule_context(
    incidents: dict[str, Any],
    rule_artifact: dict[str, Any],
) -> dict[str, Any]:
    """Attach accepted rule metadata to active candidates without live queries."""
    if incidents.get("cluster_id") != rule_artifact.get("cluster_id"):
        raise ValueError(
            "Incident candidates and Prometheus rule context must target the same cluster"
        )
    if incidents.get("incident_candidates_version") != REQUIRED_INCIDENT_VERSION:
        raise ValueError(
            f"Rule integration requires incident candidates v{REQUIRED_INCIDENT_VERSION}"
        )
    if (
        rule_artifact.get("prometheus_rule_context_version")
        != REQUIRED_RULE_CONTEXT_VERSION
    ):
        raise ValueError(
            f"Rule integration requires Prometheus rule context v{REQUIRED_RULE_CONTEXT_VERSION}"
        )
    if incidents.get("mutation_allowed") is not False:
        raise ValueError("Incident artifact must remain mutation_allowed=false")
    if rule_artifact.get("mutation_allowed") is not False:
        raise ValueError("Rule-context artifact must remain mutation_allowed=false")

    result = deepcopy(incidents)
    source_status = str(
        rule_artifact.get("source", {}).get("status")
        or "FAILED_TO_OBSERVE"
    )
    rules_by_id = {
        str(rule.get("rule_id")): rule
        for rule in rule_artifact.get("rules", [])
        if rule.get("rule_id")
    }
    contexts_by_candidate = {
        str(item.get("candidate_id")): item
        for item in rule_artifact.get("candidate_context", [])
        if item.get("candidate_id")
    }

    result["incident_candidates_version"] = INCIDENT_RULE_CONTEXT_VERSION
    result.setdefault("source_status", {})[
        "prometheus_rule_context"
    ] = source_status
    result["prometheus_rule_context_integration"] = {
        "version": RULE_INTEGRATION_VERSION,
        "mode": "EXACT_COMPLETE_ONLY",
        "source_status": source_status,
        "source_generated_at": rule_artifact.get("generated_at"),
    }

    refined_platform_checks = 0
    complete_context_candidates = 0
    active_candidates_considered = 0
    unknowns: list[dict[str, Any]] = []

    for candidate in result.get("candidates", []):
        if candidate.get("state") != "ACTIVE":
            continue
        active_candidates_considered += 1
        candidate_id = str(candidate.get("candidate_id") or "")
        context = _integration_context(
            source_status=source_status,
            candidate=candidate,
            context=contexts_by_candidate.get(candidate_id),
            rules_by_id=rules_by_id,
        )
        candidate["prometheus_rule_context"] = context

        if context["selection"] == "COMPLETE_EXACT_RULE_MATCH":
            complete_context_candidates += 1
            candidate["evidence_ids"] = _unique(
                list(candidate.get("evidence_ids", []))
                + list(context.get("evidence_ids", []))
            )
        else:
            unknown = _unknown_for_context(candidate, context)
            if unknown is not None:
                unknowns.append(unknown)

        refined_platform_checks += _refine_platform_recommendations(
            candidate,
            rule_context=context,
        )

        caveats = list(candidate.get("caveats", []))
        if context["selection"] == "COMPLETE_EXACT_RULE_MATCH":
            caveats.append(
                "Exact Prometheus rule metadata is attached as investigation "
                "context only; current rule-input metric values and root cause "
                "remain unverified."
            )
        else:
            caveats.append(
                "Prometheus rule context was not complete and exact for this "
                "candidate; generic verification remains authoritative."
            )
        candidate["caveats"] = _unique(caveats)

    summary = dict(result.get("summary", {}))
    summary.update(
        {
            "active_candidates_considered_for_prometheus_rule_context": (
                active_candidates_considered
            ),
            "active_candidates_with_complete_prometheus_rule_context": (
                complete_context_candidates
            ),
            "platform_checks_refined_to_prometheus_rule_inputs": (
                refined_platform_checks
            ),
            "prometheus_rule_integration_unknowns": len(unknowns),
        }
    )
    result["summary"] = summary
    result["prometheus_rule_context_integration_unknowns"] = unknowns

    recommendation_targets = Counter(
        check.get("target")
        for candidate in result.get("candidates", [])
        for check in candidate.get("recommended_checks", [])
        if check.get("target")
    )
    result["recommended_next_evidence_targets"] = [
        {
            "target": target,
            "candidate_checks": count,
        }
        for target, count in sorted(
            recommendation_targets.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    caveats = list(result.get("caveats", []))
    caveats.append(
        "Prometheus rule-context integration is derived-only and promotes rule "
        "metadata only when the source is COMPLETE and candidate identity plus "
        "alert-name coverage match exactly. Rule metadata is not metric-input "
        "evidence or root-cause proof."
    )
    result["caveats"] = _unique(caveats)
    return result


def render_rule_integration_markdown(artifact: dict[str, Any]) -> str:
    base = render_incident_candidates_markdown(artifact).rstrip()
    integration = artifact.get(
        "prometheus_rule_context_integration",
        {},
    )
    lines = [
        "",
        "",
        "## Prometheus rule context integration",
        "",
        f"- Source status: {integration.get('source_status', 'FAILED_TO_OBSERVE')}",
        f"- Mode: {integration.get('mode', 'UNKNOWN')}",
        (
            "- Active candidates with complete exact rule context: "
            f"{artifact.get('summary', {}).get('active_candidates_with_complete_prometheus_rule_context', 0)}"
        ),
        (
            "- Platform checks refined to PROMETHEUS_RULE_INPUTS: "
            f"{artifact.get('summary', {}).get('platform_checks_refined_to_prometheus_rule_inputs', 0)}"
        ),
        "",
    ]
    active = [
        candidate
        for candidate in artifact.get("candidates", [])
        if candidate.get("state") == "ACTIVE"
    ]
    if not active:
        lines.append("- No active candidate.")
    for candidate in active:
        context = candidate.get("prometheus_rule_context", {})
        scope = candidate.get("scope", {})
        lines.append(
            f"- {scope.get('type')} {scope.get('subject')} "
            f"selection={context.get('selection', 'NOT_ATTACHED')} "
            f"matched_rules={len(context.get('matched_rules', []))} "
            f"unmatched={','.join(context.get('unmatched_alert_names', [])) or 'none'}"
        )
        for rule in context.get("matched_rules", [])[:10]:
            lines.append(
                f"  - Rule {rule.get('alertname')} group={rule.get('group_name')} "
                f"state={rule.get('state')} health={rule.get('health')} "
                f"duration={rule.get('duration_seconds')}"
            )
    lines += [
        "",
        "Rule metadata narrows the next evidence target but does not prove current metric inputs, cause, or business impact.",
    ]
    return base + "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Integrate accepted Prometheus rule context into incident drill-down "
            "without performing a live query."
        )
    )
    parser.add_argument("--incident", type=Path, required=True)
    parser.add_argument("--rule-context", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    incidents = json.loads(args.incident.read_text(encoding="utf-8"))
    rules = json.loads(args.rule_context.read_text(encoding="utf-8"))
    integrated = integrate_prometheus_rule_context(incidents, rules)
    atomic_write_json(args.incident, integrated)
    if args.summary:
        atomic_write_text(
            args.summary,
            render_rule_integration_markdown(integrated),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
