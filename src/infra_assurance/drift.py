from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence import freshness

DRIFT_VERSION = "0.1"


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


def _collections(snapshot: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for envelope in snapshot.get("evidence", []):
        subject = envelope.get("subject", {})
        kind = subject.get("kind", "")
        if kind.endswith("Collection"):
            result[(subject.get("api_group", ""), kind.removesuffix("Collection"))] = envelope
    return result


def _observed_resources(snapshot: dict[str, Any]) -> dict[tuple[Any, ...], dict[str, Any]]:
    result: dict[tuple[Any, ...], dict[str, Any]] = {}
    for envelope in snapshot.get("evidence", []):
        subject = envelope.get("subject", {})
        if str(subject.get("kind", "")).endswith("Collection"):
            continue
        if envelope.get("plane") != "observed":
            continue
        if envelope.get("existence") == "PRESENT" and envelope.get("observation_status") == "COMPLETE":
            result[_subject_key(subject)] = envelope
    return result


def _validate_declared_record(record: dict[str, Any]) -> str | None:
    if record.get("plane") != "declared":
        return "record plane must be declared"
    provenance = record.get("provenance", {})
    if provenance.get("source_type") != "git":
        return "declared record provenance source_type must be git"
    if not provenance.get("revision"):
        return "declared Git record must include a revision"
    if not record.get("subject") or not record.get("evidence_id"):
        return "declared record is missing subject or evidence_id"
    return None


def load_declared_records(directory: Path) -> dict[str, Any]:
    """Load normalized Git-declared envelopes only; arbitrary manifests are intentionally unsupported."""
    if not directory.exists():
        return {"status": "DECLARED_STATE_UNAVAILABLE", "records": [], "errors": []}

    files = sorted(path for path in directory.rglob("*.json") if path.is_file())
    if not files:
        return {"status": "DECLARED_STATE_UNAVAILABLE", "records": [], "errors": []}

    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for path in files:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append({"file": str(path), "error": f"invalid JSON: {exc}"})
            continue

        candidates = value.get("records") if isinstance(value, dict) and "records" in value else [value]
        if not isinstance(candidates, list):
            errors.append({"file": str(path), "error": "records must be a list"})
            continue

        for candidate in candidates:
            if not isinstance(candidate, dict):
                errors.append({"file": str(path), "error": "declared record must be an object"})
                continue
            validation_error = _validate_declared_record(candidate)
            if validation_error:
                errors.append({"file": str(path), "error": validation_error})
                continue
            records.append(candidate)

    if not records and errors:
        status = "DECLARED_STATE_ERRORS"
    else:
        status = "AVAILABLE" if records else "DECLARED_STATE_UNAVAILABLE"
    return {"status": status, "records": records, "errors": errors}


def _collection_state(envelope: dict[str, Any] | None, now: datetime) -> str:
    if envelope is None:
        return "MISSING"
    if envelope.get("observation_status") == "FAILED_TO_OBSERVE":
        return "FAILED"
    if envelope.get("observation_status") != "COMPLETE":
        return "PARTIAL"
    try:
        return "CURRENT_COMPLETE" if freshness(envelope, now) == "CURRENT" else "STALE"
    except ValueError:
        return "MISSING_EXPIRY"


def _declared_state(record: dict[str, Any], now: datetime) -> str:
    status = record.get("observation_status")
    if status == "FAILED_TO_OBSERVE":
        return "FAILED"
    if status != "COMPLETE":
        return "PARTIAL"
    try:
        return "CURRENT_COMPLETE" if freshness(record, now) == "CURRENT" else "STALE"
    except ValueError:
        return "MISSING_EXPIRY"


def _compare_fields(kind: str, declared: dict[str, Any], observed: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    mismatches: list[dict[str, Any]] = []
    unknown_fields: list[str] = []
    for key, declared_value in declared.items():
        if key == "image" and kind in {"Deployment", "StatefulSet", "DaemonSet"}:
            images = observed.get("images")
            if not isinstance(images, list) or len(images) != 1:
                unknown_fields.append(key)
                continue
            observed_value = images[0]
        elif key in observed:
            observed_value = observed[key]
        else:
            unknown_fields.append(key)
            continue
        if declared_value != observed_value:
            mismatches.append({"field": key, "declared": declared_value, "observed": observed_value})
    return mismatches, unknown_fields


def build_drift_report(
    observed_snapshot: dict[str, Any],
    declared_load: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    records = declared_load.get("records", [])
    loader_errors = declared_load.get("errors", [])

    if declared_load.get("status") == "DECLARED_STATE_UNAVAILABLE":
        return {
            "drift_version": DRIFT_VERSION,
            "cluster_id": observed_snapshot["cluster_id"],
            "generated_at": _rfc3339(now),
            "status": "DECLARED_STATE_UNAVAILABLE",
            "summary": {"declared_records": 0, "in_sync": 0, "drift": 0, "unknown": 0, "loader_errors": 0},
            "results": [],
            "unknowns": [
                {
                    "code": "DECLARED_STATE_UNAVAILABLE",
                    "statement": "No normalized Git-declared evidence is configured; no declared-vs-observed drift claim can be made.",
                    "evidence_ids": [],
                }
            ],
            "loader_errors": [],
            "required_live_verification": [],
        }

    collections = _collections(observed_snapshot)
    observed = _observed_resources(observed_snapshot)
    results: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    required: list[dict[str, Any]] = []
    counts = {"IN_SYNC": 0, "DRIFT": 0, "UNKNOWN": 0}

    for declared in records:
        subject = declared["subject"]
        label = _label(subject)
        declared_state = _declared_state(declared, now)
        if declared_state != "CURRENT_COMPLETE":
            counts["UNKNOWN"] += 1
            unknowns.append(
                {
                    "code": f"DECLARED_EVIDENCE_{declared_state}",
                    "statement": f"Declared evidence for {label} is {declared_state}; drift cannot be evaluated safely.",
                    "evidence_ids": [declared["evidence_id"]],
                }
            )
            required.append(
                {
                    "code": "REFRESH_DECLARED_GIT_EVIDENCE",
                    "check": f"Refresh Git-declared evidence for {label} at a known revision.",
                    "reason": f"Declared evidence state is {declared_state}.",
                }
            )
            continue

        kind = subject["kind"]
        collection = collections.get(_kind_key(subject))
        observed_state = _collection_state(collection, now)
        if observed_state != "CURRENT_COMPLETE":
            counts["UNKNOWN"] += 1
            evidence_ids = [declared["evidence_id"]]
            if collection:
                evidence_ids.append(collection["evidence_id"])
            unknowns.append(
                {
                    "code": f"OBSERVED_COLLECTION_{observed_state}",
                    "statement": f"Observed {kind} collection is {observed_state}; drift for {label} is unknown.",
                    "evidence_ids": evidence_ids,
                }
            )
            required.append(
                {
                    "code": f"REFRESH_OBSERVED_{kind.upper()}_EVIDENCE",
                    "check": f"Refresh current {kind} evidence before evaluating drift for {label}.",
                    "reason": f"Observed collection state is {observed_state}.",
                }
            )
            continue

        observed_record = observed.get(_subject_key(subject))
        if declared.get("existence") == "ABSENT":
            if observed_record is None:
                classification = "IN_SYNC"
                field_mismatches: list[dict[str, Any]] = []
                unknown_fields: list[str] = []
            else:
                classification = "DRIFT"
                field_mismatches = [{"field": "existence", "declared": "ABSENT", "observed": "PRESENT"}]
                unknown_fields = []
        elif observed_record is None:
            classification = "DRIFT"
            field_mismatches = [{"field": "existence", "declared": "PRESENT", "observed": "ABSENT"}]
            unknown_fields = []
        else:
            field_mismatches, unknown_fields = _compare_fields(kind, declared.get("data", {}), observed_record.get("data", {}))
            if field_mismatches:
                classification = "DRIFT"
            elif unknown_fields:
                classification = "UNKNOWN"
            else:
                classification = "IN_SYNC"

        counts[classification] += 1
        evidence_ids = [declared["evidence_id"]]
        if observed_record:
            evidence_ids.append(observed_record["evidence_id"])
        elif collection:
            evidence_ids.append(collection["evidence_id"])
        results.append(
            {
                "classification": classification,
                "subject": label,
                "evidence_ids": evidence_ids,
                "field_mismatches": field_mismatches,
                "unknown_fields": unknown_fields,
                "declared_revision": declared["provenance"]["revision"],
                "declared_source": declared["provenance"]["source_id"],
            }
        )
        if classification == "UNKNOWN":
            required.append(
                {
                    "code": "EXPAND_OBSERVED_FIELD_COVERAGE",
                    "check": f"Collect comparable observed fields for {label}: {', '.join(unknown_fields)}.",
                    "reason": "Declared fields are not represented by the current normalized observed evidence.",
                }
            )

    status = "EVALUATED" if records else "DECLARED_STATE_ERRORS"
    return {
        "drift_version": DRIFT_VERSION,
        "cluster_id": observed_snapshot["cluster_id"],
        "generated_at": _rfc3339(now),
        "status": status,
        "summary": {
            "declared_records": len(records),
            "in_sync": counts["IN_SYNC"],
            "drift": counts["DRIFT"],
            "unknown": counts["UNKNOWN"],
            "loader_errors": len(loader_errors),
        },
        "results": results,
        "unknowns": unknowns,
        "loader_errors": loader_errors,
        "required_live_verification": required,
    }


def render_drift_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Declared vs Observed Drift",
        "",
        f"Cluster: `{report['cluster_id']}`",
        f"Generated: `{report['generated_at']}`",
        f"Status: `{report['status']}`",
        "",
    ]
    if report["status"] == "DECLARED_STATE_UNAVAILABLE":
        lines.extend(
            [
                "## Status",
                "",
                "- No normalized Git-declared evidence is configured. Drift is unknown, not zero.",
                "",
                "## Trust boundary",
                "",
                "Observed resources without a configured declared scope are not classified as drift.",
                "",
            ]
        )
        return "\n".join(lines)

    summary = report["summary"]
    lines.extend(
        [
            "## Summary",
            "",
            f"- Declared records: {summary['declared_records']}",
            f"- In sync: {summary['in_sync']}",
            f"- Drift: {summary['drift']}",
            f"- Unknown: {summary['unknown']}",
            f"- Loader errors: {summary['loader_errors']}",
            "",
            "## Results",
            "",
        ]
    )
    if report["results"]:
        for item in report["results"]:
            lines.append(f"- [{item['classification']}] {item['subject']} @ {item['declared_revision']}")
            for mismatch in item["field_mismatches"]:
                lines.append(f"  - {mismatch['field']}: declared={mismatch['declared']!r}, observed={mismatch['observed']!r}")
            if item["unknown_fields"]:
                lines.append(f"  - Uncomparable fields: {', '.join(item['unknown_fields'])}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Trust boundary", ""])
    lines.append("Git-declared and live-observed records remain separate evidence planes. A difference is reported without overwriting either plane.")
    lines.append("")
    return "\n".join(lines)
