from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence import freshness

DRIFT_VERSION = "0.2"


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
        if (
            envelope.get("existence") == "PRESENT"
            and envelope.get("observation_status") == "COMPLETE"
        ):
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


def _source_status(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "FAILED_TO_OBSERVE",
            "errors": [
                {
                    "code": "DECLARED_SOURCE_STATUS_INVALID",
                    "summary": "Declared source status could not be read safely.",
                }
            ],
        }
    return value if isinstance(value, dict) else None


def load_declared_records(
    directory: Path,
    *,
    source_status_path: Path | None = None,
) -> dict[str, Any]:
    """Load normalized Git-declared envelopes and preserve source observation status."""
    status = _source_status(source_status_path)
    if status and status.get("status") == "FAILED_TO_OBSERVE":
        return {
            "status": "DECLARED_STATE_OBSERVATION_FAILED",
            "records": [],
            "errors": status.get("errors", []),
            "source_status": status,
        }

    if not directory.exists():
        return {
            "status": "DECLARED_STATE_UNAVAILABLE",
            "records": [],
            "errors": [],
            "source_status": status,
        }

    files = sorted(path for path in directory.rglob("*.json") if path.is_file())
    if not files:
        if status and status.get("status") in {"COMPLETE", "PARTIAL"}:
            return {
                "status": "AVAILABLE_PARTIAL" if status.get("status") == "PARTIAL" else "AVAILABLE",
                "records": [],
                "errors": status.get("errors", []),
                "source_status": status,
            }
        return {
            "status": "DECLARED_STATE_UNAVAILABLE",
            "records": [],
            "errors": [],
            "source_status": status,
        }

    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for path in files:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append(
                {
                    "file": str(path),
                    "error": "invalid JSON in normalized declared evidence",
                }
            )
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

    if status and status.get("status") == "PARTIAL":
        errors.extend(
            {
                "file": status.get("source_id", "declared-source"),
                "error": item.get("summary", "declared source normalization was partial"),
            }
            for item in status.get("errors", [])
        )
        load_status = "AVAILABLE_PARTIAL"
    elif records or (status and status.get("status") == "COMPLETE"):
        load_status = "AVAILABLE" if not errors else "AVAILABLE_PARTIAL"
    elif errors:
        load_status = "DECLARED_STATE_ERRORS"
    else:
        load_status = "DECLARED_STATE_UNAVAILABLE"

    return {
        "status": load_status,
        "records": records,
        "errors": errors,
        "source_status": status,
    }


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
    if record.get("observation_status") == "FAILED_TO_OBSERVE":
        return "FAILED"
    if record.get("observation_status") != "COMPLETE":
        return "PARTIAL"
    try:
        return "CURRENT_COMPLETE" if freshness(record, now) == "CURRENT" else "STALE"
    except ValueError:
        return "MISSING_EXPIRY"


def _matches_declared(declared: Any, observed: Any) -> bool:
    if isinstance(declared, dict):
        return isinstance(observed, dict) and all(
            key in observed and _matches_declared(value, observed[key])
            for key, value in declared.items()
        )
    if isinstance(declared, list):
        return (
            isinstance(observed, list)
            and len(declared) == len(observed)
            and all(_matches_declared(left, right) for left, right in zip(declared, observed))
        )
    return declared == observed


def _compare_fields(
    kind: str,
    declared: dict[str, Any],
    observed: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
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
        if not _matches_declared(declared_value, observed_value):
            mismatches.append(
                {"field": key, "declared": declared_value, "observed": observed_value}
            )
    return mismatches, unknown_fields


def _empty_report(
    observed_snapshot: dict[str, Any],
    *,
    now: datetime,
    status: str,
    code: str,
    statement: str,
    loader_errors: list[dict[str, Any]],
    required: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "drift_version": DRIFT_VERSION,
        "cluster_id": observed_snapshot["cluster_id"],
        "generated_at": _rfc3339(now),
        "status": status,
        "summary": {
            "declared_records": 0,
            "in_sync": 0,
            "drift": 0,
            "unknown": 0,
            "loader_errors": len(loader_errors),
        },
        "results": [],
        "unknowns": [{"code": code, "statement": statement, "evidence_ids": []}],
        "loader_errors": loader_errors,
        "required_live_verification": required or [],
    }


def build_drift_report(
    observed_snapshot: dict[str, Any],
    declared_load: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    load_status = declared_load.get("status")
    records = declared_load.get("records", [])
    loader_errors = declared_load.get("errors", [])

    if load_status == "DECLARED_STATE_UNAVAILABLE":
        return _empty_report(
            observed_snapshot,
            now=now,
            status="DECLARED_STATE_UNAVAILABLE",
            code="DECLARED_STATE_UNAVAILABLE",
            statement="No normalized Git-declared evidence is configured; no declared-vs-observed drift claim can be made.",
            loader_errors=loader_errors,
        )

    if load_status == "DECLARED_STATE_OBSERVATION_FAILED":
        return _empty_report(
            observed_snapshot,
            now=now,
            status="DECLARED_STATE_OBSERVATION_FAILED",
            code="DECLARED_STATE_OBSERVATION_FAILED",
            statement="The latest Git declared-state observation failed; prior declared evidence is not promoted to current.",
            loader_errors=loader_errors,
            required=[
                {
                    "code": "REFRESH_DECLARED_GIT_SOURCE",
                    "check": "Refresh the configured Git declared-state source successfully.",
                    "reason": "The latest declared-state source observation failed.",
                }
            ],
        )

    if load_status == "DECLARED_STATE_ERRORS" and not records:
        return _empty_report(
            observed_snapshot,
            now=now,
            status="DECLARED_STATE_ERRORS",
            code="DECLARED_STATE_ERRORS",
            statement="Normalized declared evidence could not be loaded safely.",
            loader_errors=loader_errors,
        )

    collections = _collections(observed_snapshot)
    observed = _observed_resources(observed_snapshot)
    results: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    required: list[dict[str, str]] = []
    counts = {"IN_SYNC": 0, "DRIFT": 0, "UNKNOWN": 0}

    if load_status == "AVAILABLE_PARTIAL":
        unknowns.append(
            {
                "code": "DECLARED_STATE_PARTIAL",
                "statement": "The Git declared-state source was only partially normalized; valid records are evaluated but declared coverage is incomplete.",
                "evidence_ids": [],
            }
        )
        required.append(
            {
                "code": "RESOLVE_DECLARED_SOURCE_PARTIALITY",
                "check": "Resolve declared-source normalization errors before treating Git coverage as complete.",
                "reason": "The latest Git source normalization was partial.",
            }
        )

    for declared in records:
        subject = declared["subject"]
        label = _label(subject)

        if subject.get("cluster") != observed_snapshot.get("cluster_id"):
            counts["UNKNOWN"] += 1
            unknowns.append(
                {
                    "code": "DECLARED_CLUSTER_MISMATCH",
                    "statement": f"Declared evidence for {label} targets cluster {subject.get('cluster')}; it cannot be compared with {observed_snapshot.get('cluster_id')}.",
                    "evidence_ids": [declared["evidence_id"]],
                }
            )
            continue

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
                field_mismatches = [
                    {"field": "existence", "declared": "ABSENT", "observed": "PRESENT"}
                ]
                unknown_fields = []
        elif observed_record is None:
            classification = "DRIFT"
            field_mismatches = [
                {"field": "existence", "declared": "PRESENT", "observed": "ABSENT"}
            ]
            unknown_fields = []
        else:
            field_mismatches, unknown_fields = _compare_fields(
                kind, declared.get("data", {}), observed_record.get("data", {})
            )
            classification = (
                "DRIFT" if field_mismatches else "UNKNOWN" if unknown_fields else "IN_SYNC"
            )

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

    status = "EVALUATED_PARTIAL" if load_status == "AVAILABLE_PARTIAL" else "EVALUATED"
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

    if report["status"] in {
        "DECLARED_STATE_UNAVAILABLE",
        "DECLARED_STATE_OBSERVATION_FAILED",
        "DECLARED_STATE_ERRORS",
    }:
        statement = report["unknowns"][0]["statement"] if report["unknowns"] else "Declared state is unavailable."
        lines.extend(
            [
                "## Status",
                "",
                f"- {statement}",
                "",
                "## Trust boundary",
                "",
                "Prior or absent declared evidence is not converted into a current drift claim.",
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
            lines.append(
                f"- [{item['classification']}] {item['subject']} @ {item['declared_revision']}"
            )
            for mismatch in item["field_mismatches"]:
                lines.append(
                    f"  - {mismatch['field']}: declared={mismatch['declared']!r}, observed={mismatch['observed']!r}"
                )
            if item["unknown_fields"]:
                lines.append(f"  - Uncomparable fields: {', '.join(item['unknown_fields'])}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Unknown or partial declared evidence", ""])
    if report["unknowns"]:
        for item in report["unknowns"]:
            lines.append(f"- [{item['code']}] {item['statement']}")
    else:
        lines.append("- None.")

    lines.extend(["", "## Trust boundary", ""])
    lines.append(
        "Git-declared and live-observed records remain separate evidence planes. A difference is reported without overwriting either plane."
    )
    lines.append("")
    return "\n".join(lines)
