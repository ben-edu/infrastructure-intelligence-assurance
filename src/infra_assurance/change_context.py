from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

CHANGE_CONTEXT_VERSION = "0.1"
DEFAULT_MAX_ITEMS = 50


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_change_context(
    diff: dict[str, Any],
    drift: dict[str, Any],
    *,
    now: datetime | None = None,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if max_items < 1:
        raise ValueError("max_items must be positive")

    recent_changes = diff.get("changes", [])[:max_items]
    drift_results = [item for item in drift.get("results", []) if item.get("classification") != "IN_SYNC"][:max_items]
    unknowns: list[dict[str, Any]] = []

    unknowns.extend(diff.get("unknowns", [])[:max_items])
    unknowns.extend(drift.get("unknowns", [])[:max_items])
    for error in drift.get("loader_errors", [])[:max_items]:
        unknowns.append(
            {
                "code": "DECLARED_STATE_LOAD_ERROR",
                "statement": f"Declared evidence could not be loaded from {error.get('file')}: {error.get('error')}",
                "evidence_ids": [],
            }
        )

    required = []
    seen_required: set[tuple[str, str]] = set()
    for item in diff.get("required_live_verification", []) + drift.get("required_live_verification", []):
        key = (item.get("code", ""), item.get("check", ""))
        if key in seen_required:
            continue
        seen_required.add(key)
        required.append(item)

    return {
        "change_context_version": CHANGE_CONTEXT_VERSION,
        "task": {
            "type": "infrastructure_change_awareness",
            "scope": {"cluster": diff["cluster_id"]},
            "mutation_allowed": False,
        },
        "generated_at": _rfc3339(now),
        "history": {
            "baseline": diff["baseline"],
            "previous_snapshot_id": diff.get("previous_snapshot_id"),
            "current_snapshot_id": diff["current_snapshot_id"],
            "summary": diff["summary"],
        },
        "drift": {
            "status": drift["status"],
            "summary": drift["summary"],
        },
        "recent_changes": recent_changes,
        "drift_attention": drift_results,
        "unknowns": unknowns[:max_items],
        "required_live_verification": required[:max_items],
        "truncation": {
            "max_items_per_section": max_items,
            "recent_changes_truncated": len(diff.get("changes", [])) > max_items,
            "drift_attention_truncated": len([item for item in drift.get("results", []) if item.get("classification") != "IN_SYNC"]) > max_items,
            "unknowns_truncated": len(unknowns) > max_items,
            "required_verification_truncated": len(required) > max_items,
        },
    }


def render_change_context_markdown(context: dict[str, Any]) -> str:
    history = context["history"]
    drift = context["drift"]
    lines = [
        "# Infrastructure Change Context",
        "",
        f"Cluster: `{context['task']['scope']['cluster']}`",
        f"Generated: `{context['generated_at']}`",
        "Mutation allowed: `false`",
        "",
        "## History",
        "",
        f"- Baseline: {history['baseline']}",
        f"- Previous snapshot: `{history['previous_snapshot_id'] or 'none'}`",
        f"- Current snapshot: `{history['current_snapshot_id']}`",
        f"- Added: {history['summary']['added']}",
        f"- Removed: {history['summary']['removed']}",
        f"- Modified: {history['summary']['modified']}",
        f"- Newly observed: {history['summary']['newly_observed']}",
        f"- Unsafe comparison kinds: {history['summary']['unknown_kinds']}",
        "",
        "## Recent changes",
        "",
    ]
    if context["recent_changes"]:
        for item in context["recent_changes"]:
            lines.append(f"- [{item['classification']}] {item['subject']}")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Declared vs observed drift",
            "",
            f"- Status: `{drift['status']}`",
            f"- Declared records: {drift['summary']['declared_records']}",
            f"- In sync: {drift['summary']['in_sync']}",
            f"- Drift: {drift['summary']['drift']}",
            f"- Unknown: {drift['summary']['unknown']}",
            "",
            "## Drift attention",
            "",
        ]
    )
    if context["drift_attention"]:
        for item in context["drift_attention"]:
            lines.append(f"- [{item['classification']}] {item['subject']}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Unknown or failed evidence", ""])
    if context["unknowns"]:
        for item in context["unknowns"]:
            lines.append(f"- [{item['code']}] {item['statement']}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Required live verification", ""])
    if context["required_live_verification"]:
        for item in context["required_live_verification"]:
            lines.append(f"- [{item['code']}] {item['check']}")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "This compact projection summarizes historical change and declared-vs-observed drift. It does not replace immutable snapshot evidence or either declared/observed evidence plane.",
            "",
        ]
    )
    return "\n".join(lines)
