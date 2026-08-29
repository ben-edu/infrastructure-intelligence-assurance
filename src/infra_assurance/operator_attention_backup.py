from __future__ import annotations

from datetime import datetime
from typing import Any

from .backup_operator_adapter import build_backup_operator_adapter
from .operator_attention import build_operator_attention_summary

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
    summary["attention_now_total"] = len(attention_all)
    summary["required_live_verification_total"] = len(required_all)
    summary["backup_assets_total"] = backup["summary"]["assets_total"]
    summary["backup_protection_unknown"] = backup["summary"]["protection_unknown"]
    summary["backup_restore_verification_unknown"] = backup["summary"]["restore_verification_unknown"]
    summary["backup_unprotected_claims"] = backup["summary"]["unprotected_claims"]
    result["summary"] = summary

    truncation = dict(operator["truncation"])
    truncation["attention_now_truncated"] = len(attention_all) > max_items
    truncation["required_live_verification_truncated"] = len(required_all) > max_items
    result["truncation"] = truncation

    result["backup_assurance"] = {
        "source_status": backup["source_status"],
        "summary": backup["summary"],
        "trust": backup["trust"],
    }
    return result
