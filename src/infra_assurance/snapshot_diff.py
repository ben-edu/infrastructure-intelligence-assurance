from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .evidence import freshness

DIFF_VERSION = "0.1"


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _subject_key(subject: dict[str, Any]) -> tuple[Any, ...]:
    return (
        subject["system"],
        subject["cluster"],
        subject.get("api_group", ""),
        subject["kind"],
        subject.get("namespace"),
        subject["name"],
    )


def _kind_key(subject: dict[str, Any]) -> tuple[str, str]:
    return (subject.get("api_group", ""), subject["kind"])


def _label(subject: dict[str, Any]) -> str:
    namespace = f"{subject['namespace']}/" if subject.get("namespace") else ""
    return f"{subject['kind']}/{namespace}{subject['name']}"


def _resources(snapshot: dict[str, Any]) -> dict[tuple[Any, ...], dict[str, Any]]:
    result: dict[tuple[Any, ...], dict[str, Any]] = {}
    for envelope in snapshot.get("evidence", []):
        subject = envelope.get("subject", {})
        if str(subject.get("kind", "")).endswith("Collection"):
            continue
        if envelope.get("existence") != "PRESENT" or envelope.get("observation_status") != "COMPLETE":
            continue
        result[_subject_key(subject)] = envelope
    return result


def _collections(snapshot: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for envelope in snapshot.get("evidence", []):
        subject = envelope.get("subject", {})
        kind = subject.get("kind", "")
        if kind.endswith("Collection"):
            result[(subject.get("api_group", ""), kind.removesuffix("Collection"))] = envelope
    return result


def _current_collection_state(envelope: dict[str, Any] | None, now: datetime) -> str:
    if envelope is None:
        return "MISSING"
    status = envelope.get("observation_status")
    if status == "FAILED_TO_OBSERVE":
        return "FAILED"
    if status != "COMPLETE":
        return "PARTIAL"
    try:
        return "CURRENT_COMPLETE" if freshness(envelope, now) == "CURRENT" else "STALE"
    except ValueError:
        return "MISSING_EXPIRY"


def _previous_collection_complete(envelope: dict[str, Any] | None) -> bool:
    return bool(envelope and envelope.get("observation_status") == "COMPLETE")


def _field_changes(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    keys = sorted(set(previous) | set(current))
    for key in keys:
        before = previous.get(key)
        after = current.get(key)
        if before != after:
            changes.append({"field": key, "previous": before, "current": after})
    return changes


def build_snapshot_diff(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    *,
    previous_snapshot_id: str | None,
    current_snapshot_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if previous is not None and previous.get("cluster_id") != current.get("cluster_id"):
        raise ValueError("cannot diff snapshots from different clusters")

    if previous is None:
        return {
            "diff_version": DIFF_VERSION,
            "cluster_id": current["cluster_id"],
            "generated_at": _rfc3339(now),
            "baseline": True,
            "previous_snapshot_id": None,
            "current_snapshot_id": current_snapshot_id,
            "previous_generated_at": None,
            "current_generated_at": current["generated_at"],
            "summary": {
                "added": 0,
                "removed": 0,
                "modified": 0,
                "unchanged": 0,
                "newly_observed": 0,
                "unknown_kinds": 0,
            },
            "changes": [],
            "unknowns": [],
            "collection_failures": [],
            "required_live_verification": [],
        }

    previous_resources = _resources(previous)
    current_resources = _resources(current)
    previous_collections = _collections(previous)
    current_collections = _collections(current)

    changes: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    collection_failures: list[dict[str, Any]] = []
    required: list[dict[str, Any]] = []
    blocked_kinds: set[tuple[str, str]] = set()

    for kind_key in sorted(set(previous_collections) | set(current_collections)):
        api_group, kind = kind_key
        current_collection = current_collections.get(kind_key)
        state = _current_collection_state(current_collection, now)
        if state == "CURRENT_COMPLETE":
            continue
        blocked_kinds.add(kind_key)
        evidence_ids = [current_collection["evidence_id"]] if current_collection else []
        unknowns.append(
            {
                "code": f"CURRENT_COLLECTION_{state}",
                "api_group": api_group,
                "resource_kind": kind,
                "statement": f"Current {kind} membership cannot be compared safely because collection state is {state}.",
                "evidence_ids": evidence_ids,
            }
        )
        required.append(
            {
                "code": f"VERIFY_CURRENT_{kind.upper()}_COLLECTION",
                "check": f"Refresh the {kind} collection successfully before interpreting additions, removals, or current field changes.",
                "reason": f"Current collection state is {state}.",
            }
        )
        if current_collection and current_collection.get("observation_status") == "FAILED_TO_OBSERVE":
            collection_failures.append(
                {
                    "api_group": api_group,
                    "resource_kind": kind,
                    "evidence_id": current_collection["evidence_id"],
                    "error_codes": [item["code"] for item in current_collection.get("errors", [])],
                }
            )

    all_keys = sorted(set(previous_resources) | set(current_resources), key=str)
    unchanged = 0
    counts = {"ADDED": 0, "REMOVED": 0, "MODIFIED": 0, "NEWLY_OBSERVED": 0}

    for key in all_keys:
        previous_envelope = previous_resources.get(key)
        current_envelope = current_resources.get(key)
        sample = current_envelope or previous_envelope
        assert sample is not None
        kind_key = _kind_key(sample["subject"])
        if kind_key in blocked_kinds:
            continue

        if previous_envelope and current_envelope:
            field_changes = _field_changes(previous_envelope.get("data", {}), current_envelope.get("data", {}))
            if not field_changes:
                unchanged += 1
                continue
            classification = "MODIFIED"
            counts[classification] += 1
            changes.append(
                {
                    "classification": classification,
                    "subject": _label(current_envelope["subject"]),
                    "evidence_ids": [previous_envelope["evidence_id"], current_envelope["evidence_id"]],
                    "field_changes": field_changes,
                }
            )
            continue

        if current_envelope and not previous_envelope:
            previous_complete = _previous_collection_complete(previous_collections.get(kind_key))
            classification = "ADDED" if previous_complete else "NEWLY_OBSERVED"
            counts[classification] += 1
            evidence_ids = [current_envelope["evidence_id"]]
            previous_collection = previous_collections.get(kind_key)
            if previous_collection:
                evidence_ids.append(previous_collection["evidence_id"])
            changes.append(
                {
                    "classification": classification,
                    "subject": _label(current_envelope["subject"]),
                    "evidence_ids": evidence_ids,
                    "field_changes": [],
                }
            )
            continue

        if previous_envelope and not current_envelope:
            classification = "REMOVED"
            counts[classification] += 1
            current_collection = current_collections.get(kind_key)
            evidence_ids = [previous_envelope["evidence_id"]]
            if current_collection:
                evidence_ids.append(current_collection["evidence_id"])
            changes.append(
                {
                    "classification": classification,
                    "subject": _label(previous_envelope["subject"]),
                    "evidence_ids": evidence_ids,
                    "field_changes": [],
                }
            )

    return {
        "diff_version": DIFF_VERSION,
        "cluster_id": current["cluster_id"],
        "generated_at": _rfc3339(now),
        "baseline": False,
        "previous_snapshot_id": previous_snapshot_id,
        "current_snapshot_id": current_snapshot_id,
        "previous_generated_at": previous["generated_at"],
        "current_generated_at": current["generated_at"],
        "summary": {
            "added": counts["ADDED"],
            "removed": counts["REMOVED"],
            "modified": counts["MODIFIED"],
            "unchanged": unchanged,
            "newly_observed": counts["NEWLY_OBSERVED"],
            "unknown_kinds": len(blocked_kinds),
        },
        "changes": changes,
        "unknowns": unknowns,
        "collection_failures": collection_failures,
        "required_live_verification": required,
    }


def render_snapshot_diff_markdown(diff: dict[str, Any]) -> str:
    lines = [
        "# Kubernetes Snapshot Diff",
        "",
        f"Cluster: `{diff['cluster_id']}`",
        f"Generated: `{diff['generated_at']}`",
        f"Current snapshot: `{diff['current_snapshot_id']}`",
        f"Previous snapshot: `{diff['previous_snapshot_id'] or 'none'}`",
        "",
    ]
    if diff["baseline"]:
        lines.extend(["## Status", "", "- Initial historical baseline; no previous snapshot exists yet.", ""])
        return "\n".join(lines)

    summary = diff["summary"]
    lines.extend(
        [
            "## Change summary",
            "",
            f"- Added: {summary['added']}",
            f"- Removed: {summary['removed']}",
            f"- Modified: {summary['modified']}",
            f"- Newly observed: {summary['newly_observed']}",
            f"- Unchanged: {summary['unchanged']}",
            f"- Resource kinds with unsafe current comparison: {summary['unknown_kinds']}",
            "",
            "## Changes",
            "",
        ]
    )
    if diff["changes"]:
        for item in diff["changes"]:
            lines.append(f"- [{item['classification']}] {item['subject']}")
            for field in item["field_changes"]:
                lines.append(f"  - {field['field']}: {field['previous']!r} -> {field['current']!r}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Unknown or failed comparison", ""])
    if diff["unknowns"]:
        for item in diff["unknowns"]:
            lines.append(f"- [{item['code']}] {item['statement']}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Trust boundary", ""])
    lines.append("A resource is never classified as removed when its current collection is failed, stale, partial, or missing.")
    lines.append("")
    return "\n".join(lines)
