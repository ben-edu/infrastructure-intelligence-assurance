from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from .backup_operator_adapter import build_backup_operator_adapter
from .io_utils import atomic_write_json, atomic_write_text
from .operator_attention import (
    build_operator_attention_summary,
    load_json_artifact,
    render_operator_attention_markdown,
)

CROSS_DOMAIN_SCOPE = "KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY"


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


def _backup_attention_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "backup_assurance",
        "code": str(item.get("code") or "BACKUP_ASSURANCE_ATTENTION"),
        "severity": str(item.get("severity") or "UNKNOWN"),
        "subject": None,
        "statement": item.get("statement") if isinstance(item.get("statement"), str) else None,
        "evidence_ids": [],
        "count": item.get("count") if isinstance(item.get("count"), int) else None,
    }


def _backup_verification_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "backup_assurance",
        "code": str(item.get("code") or "BACKUP_VERIFICATION_REQUIRED"),
        "check": item.get("check") if isinstance(item.get("check"), str) else None,
        "reason": "Authoritative backup/recovery evidence is required before making a stronger assurance claim.",
        "target": item.get("target") if isinstance(item.get("target"), str) else None,
        "authoritative_source_required": bool(item.get("authoritative_source_required", True)),
    }


def build_operator_attention_with_backup(
    inventory: dict[str, Any],
    context: dict[str, Any],
    change_context: dict[str, Any],
    backup_assurance: dict[str, Any],
    *,
    now: datetime | None = None,
    max_items: int = 20,
) -> dict[str, Any]:
    """Combine the accepted Kubernetes operator projection with compact backup-assurance gaps."""
    operator = build_operator_attention_summary(
        inventory,
        context,
        change_context,
        now=now,
        max_items=max_items,
    )
    backup = build_backup_operator_adapter(backup_assurance, now=now)

    if operator["cluster_id"] != backup["cluster_id"]:
        raise ValueError("operator and backup assurance inputs must target the same cluster")

    operator_attention = list(operator["attention_now"])
    backup_attention = [_backup_attention_item(item) for item in backup["attention"]]
    attention_all = _dedupe(
        operator_attention + backup_attention,
        ("source", "code", "subject", "statement", "count"),
    )

    operator_required = list(operator["required_live_verification"])
    backup_required = [
        _backup_verification_item(item)
        for item in backup["required_live_verification"]
    ]
    required_all = _dedupe(
        operator_required + backup_required,
        ("source", "code", "check", "target"),
    )

    operator_attention_total = int(operator["summary"].get("attention_now_total", 0) or 0)
    operator_required_total = int(operator["summary"].get("required_live_verification_total", 0) or 0)
    combined_attention_total = operator_attention_total + len(backup_attention)
    combined_required_total = operator_required_total + len(backup_required)

    result = dict(operator)
    result["scope"] = CROSS_DOMAIN_SCOPE
    result["attention_now"] = attention_all[:max_items]
    result["required_live_verification"] = required_all[:max_items]
    result["source_artifacts"] = [
        "inventory.json",
        "context.json",
        "change-context.json",
        "backup-assurance.json",
    ]

    summary = dict(operator["summary"])
    summary["attention_now_total"] = combined_attention_total
    summary["required_live_verification_total"] = combined_required_total
    summary["backup_assets_total"] = backup["summary"]["assets_total"]
    summary["backup_protection_unknown"] = backup["summary"]["protection_unknown"]
    summary["backup_restore_verification_unknown"] = backup["summary"]["restore_verification_unknown"]
    summary["backup_unprotected_claims"] = backup["summary"]["unprotected_claims"]
    result["summary"] = summary

    truncation = dict(operator["truncation"])
    truncation["attention_now_truncated"] = combined_attention_total > max_items
    truncation["required_live_verification_truncated"] = combined_required_total > max_items
    result["truncation"] = truncation

    result["backup_assurance"] = {
        "source_status": backup["source_status"],
        "summary": backup["summary"],
        "trust": backup["trust"],
    }
    return result


def render_operator_attention_with_backup_markdown(summary: dict[str, Any]) -> str:
    """Render the existing operator Markdown with an explicit cross-domain trust boundary."""
    rendered = render_operator_attention_markdown(summary)
    counts = summary["summary"]
    backup_block = "\n".join(
        [
            "## Backup assurance",
            "",
            f"- Backup assets: {counts['backup_assets_total']}",
            f"- Protection unknown: {counts['backup_protection_unknown']}",
            f"- Restore verification unknown: {counts['backup_restore_verification_unknown']}",
            f"- Unprotected claims: {counts['backup_unprotected_claims']}",
            "",
        ]
    )
    rendered = rendered.replace("\n## Trust boundary\n", f"\n{backup_block}\n## Trust boundary\n", 1)
    return rendered.replace(
        "existing Kubernetes evidence artifacts only",
        "existing Kubernetes and backup-assurance evidence artifacts only",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the cross-domain read-only operator-attention projection from already-generated "
            "Kubernetes and backup-assurance evidence artifacts. This command performs no live infrastructure query."
        )
    )
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--change-context", type=Path, required=True)
    parser.add_argument("--backup-assurance", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path)
    parser.add_argument("--max-items", type=int, default=20)
    args = parser.parse_args()

    if args.max_items < 1:
        parser.error("--max-items must be positive")

    summary = build_operator_attention_with_backup(
        load_json_artifact(args.inventory),
        load_json_artifact(args.context),
        load_json_artifact(args.change_context),
        load_json_artifact(args.backup_assurance),
        max_items=args.max_items,
    )
    atomic_write_json(args.out, summary)
    if args.summary_out:
        atomic_write_text(args.summary_out, render_operator_attention_with_backup_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
