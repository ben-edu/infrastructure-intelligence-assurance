from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from .incident_operator_adapter import build_incident_operator_adapter
from .io_utils import atomic_write_json, atomic_write_text
from .operator_attention import load_json_artifact
from .operator_attention_backup import render_operator_attention_with_backup_markdown

CROSS_DOMAIN_SCOPE = "KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY"
EXPECTED_OPERATOR_SCOPE = "KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY"


def _dedupe(items: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in items:
        key = tuple(item.get(name) for name in keys)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _incident_attention_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "incident_candidates",
        "code": str(item.get("code") or "INCIDENT_CANDIDATE_ATTENTION"),
        "severity": str(item.get("severity") or "UNKNOWN"),
        "subject": None,
        "statement": item.get("statement") if isinstance(item.get("statement"), str) else None,
        "evidence_ids": [],
        "count": item.get("count") if isinstance(item.get("count"), int) else None,
    }


def _incident_verification_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "incident_candidates",
        "code": str(item.get("code") or "INCIDENT_VERIFICATION_REQUIRED"),
        "check": item.get("check") if isinstance(item.get("check"), str) else None,
        "reason": "Incident-candidate evidence requires live verification before operational action.",
        "target": item.get("target") if isinstance(item.get("target"), str) else None,
        "live_verification_required": True,
    }


def build_operator_attention_with_incidents(
    operator_attention: dict[str, Any],
    incident_candidates: dict[str, Any],
    *,
    now: datetime | None = None,
    max_items: int = 20,
    max_incident_candidates: int = 20,
) -> dict[str, Any]:
    """Add compact incident-candidate evidence to an accepted Kubernetes+backup operator artifact."""
    if max_items < 1:
        raise ValueError("max_items must be positive")
    if max_incident_candidates < 1:
        raise ValueError("max_incident_candidates must be positive")

    operator_cluster = operator_attention.get("cluster_id")
    operator_scope = operator_attention.get("scope")
    if not isinstance(operator_cluster, str) or not operator_cluster:
        raise ValueError("operator attention artifact must identify a cluster")
    if operator_scope != EXPECTED_OPERATOR_SCOPE:
        raise ValueError("operator attention input must use the accepted Kubernetes+backup scope")
    if operator_attention.get("mutation_allowed") is not False:
        raise ValueError("operator attention input must preserve mutation_allowed=false")

    incident = build_incident_operator_adapter(
        incident_candidates,
        now=now,
        max_candidates=max_incident_candidates,
    )
    if operator_cluster != incident["cluster_id"]:
        raise ValueError("operator attention and incident candidates must target the same cluster")

    existing_attention = list(operator_attention.get("attention_now", []))
    incident_attention = [_incident_attention_item(item) for item in incident["attention"]]
    attention_all = _dedupe(
        existing_attention + incident_attention,
        ("source", "code", "subject", "statement", "count"),
    )

    existing_required = list(operator_attention.get("required_live_verification", []))
    incident_required = [
        _incident_verification_item(item)
        for item in incident["required_live_verification"]
    ]
    required_all = _dedupe(
        existing_required + incident_required,
        ("source", "code", "check", "target"),
    )

    existing_summary = operator_attention.get("summary")
    existing_truncation = operator_attention.get("truncation")
    if not isinstance(existing_summary, dict):
        raise ValueError("operator attention artifact must contain a summary object")
    if not isinstance(existing_truncation, dict):
        raise ValueError("operator attention artifact must contain truncation metadata")

    existing_attention_total = int(existing_summary.get("attention_now_total", 0) or 0)
    existing_required_total = int(existing_summary.get("required_live_verification_total", 0) or 0)
    combined_attention_total = existing_attention_total + len(incident_attention)
    combined_required_total = existing_required_total + len(incident_required)

    result = dict(operator_attention)
    result["scope"] = CROSS_DOMAIN_SCOPE
    result["attention_now"] = attention_all[:max_items]
    result["required_live_verification"] = required_all[:max_items]

    source_artifacts = [
        item
        for item in operator_attention.get("source_artifacts", [])
        if isinstance(item, str)
    ]
    if "incident-candidates.json" not in source_artifacts:
        source_artifacts.append("incident-candidates.json")
    result["source_artifacts"] = source_artifacts

    summary = dict(existing_summary)
    summary["attention_now_total"] = combined_attention_total
    summary["required_live_verification_total"] = combined_required_total
    summary["incident_candidates_total"] = incident["summary"]["incident_candidates"]
    summary["incident_active_candidates"] = incident["summary"]["active_candidates"]
    summary["incident_suppressed_candidates"] = incident["summary"]["suppressed_candidates"]
    summary["incident_unknown_candidates"] = incident["summary"]["unknown_candidates"]
    summary["incident_candidates_with_related_warning_events"] = incident["summary"][
        "candidates_with_related_warning_events"
    ]
    summary["incident_candidates_requiring_live_verification"] = incident["summary"][
        "candidates_requiring_live_verification"
    ]
    result["summary"] = summary

    truncation = dict(existing_truncation)
    truncation["attention_now_truncated"] = combined_attention_total > max_items
    truncation["required_live_verification_truncated"] = combined_required_total > max_items
    truncation["incident_candidates_truncated"] = incident["truncation"]["candidates_truncated"]
    result["truncation"] = truncation

    result["incident_candidates"] = {
        "source_status": incident["source_status"],
        "source_statuses": incident["source_statuses"],
        "summary": incident["summary"],
        "candidates": incident["candidates"],
        "trust": incident["trust"],
        "truncation": incident["truncation"],
    }
    return result


def render_operator_attention_with_incidents_markdown(summary: dict[str, Any]) -> str:
    """Render the accepted Kubernetes+backup Markdown with compact incident-candidate context."""
    rendered = render_operator_attention_with_backup_markdown(summary)
    counts = summary["summary"]
    incident = summary["incident_candidates"]
    block = "\n".join(
        [
            "## Incident candidates",
            "",
            f"- Source status: {incident['source_status']}",
            f"- Candidates: {counts['incident_candidates_total']}",
            f"- Active: {counts['incident_active_candidates']}",
            f"- Suppressed: {counts['incident_suppressed_candidates']}",
            f"- Unknown: {counts['incident_unknown_candidates']}",
            f"- With related Warning Events: {counts['incident_candidates_with_related_warning_events']}",
            "- Candidate grouping is not incident confirmation or root-cause proof.",
            "",
        ]
    )
    return rendered.replace("\n## Trust boundary\n", f"\n{block}\n## Trust boundary\n", 1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Combine an accepted Kubernetes+backup operator-attention artifact with existing incident-candidate "
            "evidence. This command performs no live infrastructure query."
        )
    )
    parser.add_argument("--operator-attention", type=Path, required=True)
    parser.add_argument("--incident-candidates", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path)
    parser.add_argument("--max-items", type=int, default=20)
    parser.add_argument("--max-incident-candidates", type=int, default=20)
    args = parser.parse_args()

    if args.max_items < 1:
        parser.error("--max-items must be positive")
    if args.max_incident_candidates < 1:
        parser.error("--max-incident-candidates must be positive")

    summary = build_operator_attention_with_incidents(
        load_json_artifact(args.operator_attention),
        load_json_artifact(args.incident_candidates),
        max_items=args.max_items,
        max_incident_candidates=args.max_incident_candidates,
    )
    atomic_write_json(args.out, summary)
    if args.summary_out:
        atomic_write_text(args.summary_out, render_operator_attention_with_incidents_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
