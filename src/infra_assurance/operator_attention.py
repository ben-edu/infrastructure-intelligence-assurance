from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUMMARY_VERSION = "0.1"
DEFAULT_MAX_ITEMS = 20
DEFAULT_EVIDENCE_DIR = Path("/var/lib/infra-assurance/evidence")
DEFAULT_SOURCES = {
    "inventory": DEFAULT_EVIDENCE_DIR / "inventory.json",
    "context": DEFAULT_EVIDENCE_DIR / "context.json",
    "change_context": DEFAULT_EVIDENCE_DIR / "change-context.json",
}
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _evidence_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)][:50]


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


def _inventory_attention(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for entity in inventory.get("entities", []):
        if not isinstance(entity, dict):
            continue
        for item in entity.get("attention", []):
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    "source": str(item.get("source") or "inventory"),
                    "code": str(item.get("code") or "ATTENTION"),
                    "severity": str(item.get("severity") or "UNKNOWN"),
                    "subject": item.get("subject") if isinstance(item.get("subject"), str) else None,
                    "statement": item.get("statement") if isinstance(item.get("statement"), str) else None,
                    "evidence_ids": _evidence_ids(item.get("evidence_ids")),
                }
            )
    return result


def _context_attention(context: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for failure in context.get("observation_failures", []):
        if not isinstance(failure, dict):
            continue
        result.append(
            {
                "source": "observation",
                "code": "OBSERVATION_FAILED",
                "severity": "UNKNOWN",
                "subject": failure.get("subject") if isinstance(failure.get("subject"), str) else None,
                "statement": "Current state is unknown because the latest observation failed.",
                "evidence_ids": [failure["evidence_id"]] if isinstance(failure.get("evidence_id"), str) else [],
            }
        )
    for inference in context.get("inferences", []):
        if not isinstance(inference, dict) or not isinstance(inference.get("statement"), str):
            continue
        result.append(
            {
                "source": "operational_context",
                "code": "OPERATIONAL_INFERENCE",
                "severity": "ATTENTION",
                "subject": None,
                "statement": inference["statement"],
                "evidence_ids": _evidence_ids(inference.get("evidence_ids")),
            }
        )
    return result


def _recent_changes(change_context: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in change_context.get("recent_changes", []):
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "classification": str(item.get("classification") or "UNKNOWN"),
                "subject": item.get("subject") if isinstance(item.get("subject"), str) else None,
                "evidence_ids": _evidence_ids(item.get("evidence_ids")),
            }
        )
    return result


def _unknowns(context: dict[str, Any], change_context: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in context.get("unknowns", []):
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "source": "operational_context",
                "code": "CURRENT_STATE_UNKNOWN",
                "subject": item.get("subject") if isinstance(item.get("subject"), str) else None,
                "statement": item.get("reason") if isinstance(item.get("reason"), str) else None,
                "evidence_ids": [],
            }
        )
    for item in change_context.get("unknowns", []):
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "source": "change_context",
                "code": str(item.get("code") or "UNKNOWN_EVIDENCE"),
                "subject": item.get("subject") if isinstance(item.get("subject"), str) else None,
                "statement": item.get("statement") if isinstance(item.get("statement"), str) else None,
                "evidence_ids": _evidence_ids(item.get("evidence_ids")),
            }
        )
    return result


def _required_verification(context: dict[str, Any], change_context: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in context.get("required_live_verification", []):
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "source": "operational_context",
                "code": "LIVE_VERIFICATION_REQUIRED",
                "check": item.get("question") if isinstance(item.get("question"), str) else None,
                "reason": item.get("reason") if isinstance(item.get("reason"), str) else None,
            }
        )
    for item in change_context.get("required_live_verification", []):
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "source": "change_context",
                "code": str(item.get("code") or "LIVE_VERIFICATION_REQUIRED"),
                "check": item.get("check") if isinstance(item.get("check"), str) else None,
                "reason": item.get("reason") if isinstance(item.get("reason"), str) else None,
            }
        )
    return result


def _cluster_id(inventory: dict[str, Any], context: dict[str, Any], change_context: dict[str, Any]) -> str:
    values = {
        value
        for value in (
            inventory.get("cluster_id"),
            context.get("task", {}).get("scope", {}).get("cluster") if isinstance(context.get("task"), dict) else None,
            change_context.get("task", {}).get("scope", {}).get("cluster") if isinstance(change_context.get("task"), dict) else None,
        )
        if isinstance(value, str) and value
    }
    if len(values) != 1:
        raise ValueError("operator attention inputs must target exactly one matching cluster")
    return next(iter(values))


def build_operator_attention_summary(
    inventory: dict[str, Any],
    context: dict[str, Any],
    change_context: dict[str, Any],
    *,
    now: datetime | None = None,
    max_items: int = DEFAULT_MAX_ITEMS,
) -> dict[str, Any]:
    """Build a compact read-only operator attention projection from existing evidence artifacts."""
    if max_items < 1:
        raise ValueError("max_items must be positive")
    cluster_id = _cluster_id(inventory, context, change_context)
    now = now or datetime.now(timezone.utc)

    attention_all = _dedupe(
        _inventory_attention(inventory) + _context_attention(context),
        ("source", "code", "subject", "statement"),
    )
    changes_all = _dedupe(_recent_changes(change_context), ("classification", "subject"))
    unknowns_all = _dedupe(
        _unknowns(context, change_context),
        ("source", "code", "subject", "statement"),
    )
    required_all = _dedupe(
        _required_verification(context, change_context),
        ("source", "code", "check", "reason"),
    )

    inventory_summary = inventory.get("summary", {}) if isinstance(inventory.get("summary"), dict) else {}
    return {
        "operator_attention_version": SUMMARY_VERSION,
        "generated_at": _rfc3339(now),
        "cluster_id": cluster_id,
        "mutation_allowed": False,
        "scope": "KUBERNETES_EXISTING_EVIDENCE_ONLY",
        "summary": {
            "workloads_total": int(inventory_summary.get("workloads_total", 0) or 0),
            "workloads_with_attention": int(inventory_summary.get("workloads_with_attention", 0) or 0),
            "attention_now_total": len(attention_all),
            "recent_changes_total": len(changes_all),
            "unknowns_total": len(unknowns_all),
            "required_live_verification_total": len(required_all),
        },
        "attention_now": attention_all[:max_items],
        "recent_changes": changes_all[:max_items],
        "unknowns": unknowns_all[:max_items],
        "required_live_verification": required_all[:max_items],
        "truncation": {
            "max_items_per_section": max_items,
            "attention_now_truncated": len(attention_all) > max_items,
            "recent_changes_truncated": len(changes_all) > max_items,
            "unknowns_truncated": len(unknowns_all) > max_items,
            "required_live_verification_truncated": len(required_all) > max_items,
        },
        "source_artifacts": ["inventory.json", "context.json", "change-context.json"],
    }


def load_json_artifact(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError(f"symlink source rejected: {path.name}")
    stat = path.stat()
    if not path.is_file():
        raise ValueError(f"source is not a regular file: {path.name}")
    if stat.st_size > MAX_ARTIFACT_BYTES:
        raise ValueError(f"source exceeds safe size ceiling: {path.name}")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"source top-level shape must be an object: {path.name}")
    return payload


def load_default_sources(paths: dict[str, Path] = DEFAULT_SOURCES) -> dict[str, dict[str, Any]]:
    required = {"inventory", "context", "change_context"}
    if set(paths) != required:
        raise ValueError("operator attention source map must contain exactly the required source keys")
    return {name: load_json_artifact(path) for name, path in paths.items()}
