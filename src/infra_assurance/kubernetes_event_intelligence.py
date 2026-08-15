from __future__ import annotations

import hashlib
import json
import re
import subprocess
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

EVENT_RUNTIME_VERSION = "0.1"
EVENT_CORRELATION_VERSION = "0.1"
DEFAULT_WINDOW_SECONDS = 3600
DEFAULT_MAX_EVENTS = 500
DEFAULT_TTL_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 20
Runner = Callable[..., subprocess.CompletedProcess[str]]

_SAFE_REASON = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _stable_hash(*parts: Any) -> str:
    raw = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _safe_reason(value: Any) -> str:
    if not isinstance(value, str) or not value:
        return "UNKNOWN"
    if _SAFE_REASON.fullmatch(value):
        return value
    return "REDACTED_REASON"


def _event_type(value: Any) -> str:
    normalized = str(value or "").upper()
    if normalized == "WARNING":
        return "WARNING"
    if normalized == "NORMAL":
        return "NORMAL"
    return "UNKNOWN"


def _subject(regarding: dict[str, Any]) -> str:
    namespace = regarding.get("namespace")
    if namespace:
        return f"{regarding['kind']}/{namespace}/{regarding['name']}"
    return f"{regarding['kind']}/{regarding['name']}"


def _classify_failure(stderr: str) -> tuple[str, str]:
    lowered = stderr.lower()
    if "forbidden" in lowered:
        return (
            "KUBERNETES_EVENTS_FORBIDDEN",
            "Kubernetes API denied the read-only Event list request.",
        )
    if "timeout" in lowered or "timed out" in lowered:
        return (
            "KUBERNETES_EVENTS_TIMEOUT",
            "The read-only Kubernetes Event list request timed out.",
        )
    if "connection refused" in lowered or "unable to connect" in lowered:
        return (
            "KUBERNETES_EVENTS_UNREACHABLE",
            "The Kubernetes API could not be reached for Event observation.",
        )
    return (
        "KUBERNETES_EVENTS_READ_FAILED",
        "The read-only Kubernetes Event list request failed.",
    )


def _event_last_seen(item: dict[str, Any]) -> datetime | None:
    series = item.get("series") if isinstance(item.get("series"), dict) else {}
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    for candidate in (
        series.get("lastObservedTime"),
        item.get("eventTime"),
        item.get("lastTimestamp"),
        metadata.get("creationTimestamp"),
        item.get("firstTimestamp"),
    ):
        parsed = _parse_time(candidate)
        if parsed is not None:
            return parsed
    return None


def _event_first_seen(item: dict[str, Any], last_seen: datetime) -> datetime:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    for candidate in (
        item.get("firstTimestamp"),
        metadata.get("creationTimestamp"),
        item.get("eventTime"),
    ):
        parsed = _parse_time(candidate)
        if parsed is not None:
            return parsed
    return last_seen


def _event_count(item: dict[str, Any]) -> int:
    series = item.get("series") if isinstance(item.get("series"), dict) else {}
    value = series.get("count", item.get("count", 1))
    if isinstance(value, int) and value >= 1:
        return value
    return 1


def _normalize_event(
    item: dict[str, Any],
    *,
    now: datetime,
    ttl_seconds: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    involved = item.get("involvedObject")
    if not isinstance(involved, dict):
        involved = item.get("regarding")
    if not isinstance(involved, dict):
        return None, {
            "code": "KUBERNETES_EVENT_OBJECT_UNKNOWN",
            "statement": "A Kubernetes Event had no usable involved-object identity.",
            "evidence_ids": [],
        }

    kind = involved.get("kind")
    name = involved.get("name")
    if not isinstance(kind, str) or not kind or not isinstance(name, str) or not name:
        return None, {
            "code": "KUBERNETES_EVENT_OBJECT_UNKNOWN",
            "statement": "A Kubernetes Event had an incomplete involved-object identity.",
            "evidence_ids": [],
        }

    namespace = involved.get("namespace")
    if not isinstance(namespace, str) or not namespace:
        namespace = None
    api_version = involved.get("apiVersion")
    if not isinstance(api_version, str) or not api_version:
        api_version = None

    last_seen = _event_last_seen(item)
    if last_seen is None:
        return None, {
            "code": "KUBERNETES_EVENT_TIME_UNKNOWN",
            "statement": f"Kubernetes Event for {kind}/{name} had no usable occurrence timestamp and was not promoted into the recent-event window.",
            "evidence_ids": [],
        }
    first_seen = _event_first_seen(item, last_seen)

    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    raw_identity = metadata.get("uid") or metadata.get("name")
    regarding = {
        "api_version": api_version,
        "kind": kind,
        "namespace": namespace,
        "name": name,
    }
    reason = _safe_reason(item.get("reason"))
    event_id = "k8s-event-" + _stable_hash(raw_identity, regarding, reason)
    evidence_id = f"ev-kubernetes-event-{uuid.uuid4()}"

    return (
        {
            "event_id": event_id,
            "evidence_id": evidence_id,
            "observed_at": _rfc3339(now),
            "expires_at": _rfc3339(now + timedelta(seconds=ttl_seconds)),
            "type": _event_type(item.get("type")),
            "reason": reason,
            "regarding": regarding,
            "subject": _subject(regarding),
            "first_seen": _rfc3339(first_seen),
            "last_seen": _rfc3339(last_seen),
            "count": _event_count(item),
        },
        None,
    )


def build_kubernetes_event_runtime(
    *,
    cluster_id: str,
    kubectl_context: str | None = None,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
    window_seconds: int = DEFAULT_WINDOW_SECONDS,
    max_events: int = DEFAULT_MAX_EVENTS,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Observe a bounded recent Kubernetes Event window without persisting free-form messages."""
    if window_seconds < 60:
        raise ValueError("window_seconds must be at least 60")
    if max_events < 1:
        raise ValueError("max_events must be at least 1")

    now = now or datetime.now(timezone.utc)
    command = ["kubectl"]
    if kubectl_context:
        command += ["--context", kubectl_context]
    command += ["get", "events", "--all-namespaces", "-o", "json"]

    try:
        result = runner(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _failed_runtime(
            cluster_id,
            now,
            window_seconds,
            max_events,
            "KUBERNETES_EVENTS_TIMEOUT",
            "kubectl exceeded the local Kubernetes Event observation timeout.",
        )
    except FileNotFoundError:
        return _failed_runtime(
            cluster_id,
            now,
            window_seconds,
            max_events,
            "KUBECTL_NOT_AVAILABLE",
            "kubectl is not available in the runtime observer.",
        )

    if result.returncode != 0:
        code, summary = _classify_failure(result.stderr)
        return _failed_runtime(cluster_id, now, window_seconds, max_events, code, summary)

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return _failed_runtime(
            cluster_id,
            now,
            window_seconds,
            max_events,
            "KUBERNETES_EVENTS_RESPONSE_INVALID",
            "Kubernetes Event observation returned invalid JSON.",
        )

    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return _failed_runtime(
            cluster_id,
            now,
            window_seconds,
            max_events,
            "KUBERNETES_EVENTS_RESPONSE_INVALID",
            "Kubernetes Event observation did not contain an items list.",
        )

    cutoff = now - timedelta(seconds=window_seconds)
    normalized: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        event, unknown = _normalize_event(item, now=now, ttl_seconds=ttl_seconds)
        if unknown:
            unknowns.append(unknown)
            continue
        assert event is not None
        last_seen = _parse_time(event["last_seen"])
        if last_seen is not None and last_seen >= cutoff:
            normalized.append(event)

    normalized.sort(key=lambda item: item["last_seen"], reverse=True)
    truncated = len(normalized) > max_events
    if truncated:
        normalized = normalized[:max_events]
        unknowns.append(
            {
                "code": "KUBERNETES_EVENT_WINDOW_TRUNCATED",
                "statement": f"Recent Kubernetes Event evidence exceeded the configured {max_events}-record bound; no-match correlation is not complete for this observation.",
                "evidence_ids": [],
            }
        )

    type_counts = Counter(item["type"] for item in normalized)
    source_status = "PARTIAL" if truncated or unknowns else "COMPLETE"
    return {
        "kubernetes_event_runtime_version": EVENT_RUNTIME_VERSION,
        "cluster_id": cluster_id,
        "generated_at": _rfc3339(now),
        "mutation_allowed": False,
        "source": {
            "type": "kubernetes_core_v1_events",
            "access": "kubectl_read",
            "status": source_status,
            "window_seconds": window_seconds,
            "max_events": max_events,
        },
        "summary": {
            "events_seen_from_api": len(items),
            "events_recent": len(normalized),
            "events_warning": type_counts["WARNING"],
            "events_normal": type_counts["NORMAL"],
            "events_unknown_type": type_counts["UNKNOWN"],
            "window_truncated": truncated,
        },
        "events": normalized,
        "unknowns": unknowns,
        "errors": [],
    }


def _failed_runtime(
    cluster_id: str,
    now: datetime,
    window_seconds: int,
    max_events: int,
    code: str,
    summary: str,
) -> dict[str, Any]:
    return {
        "kubernetes_event_runtime_version": EVENT_RUNTIME_VERSION,
        "cluster_id": cluster_id,
        "generated_at": _rfc3339(now),
        "mutation_allowed": False,
        "source": {
            "type": "kubernetes_core_v1_events",
            "access": "kubectl_read",
            "status": "FAILED_TO_OBSERVE",
            "window_seconds": window_seconds,
            "max_events": max_events,
        },
        "summary": {
            "events_seen_from_api": 0,
            "events_recent": 0,
            "events_warning": 0,
            "events_normal": 0,
            "events_unknown_type": 0,
            "window_truncated": False,
        },
        "events": [],
        "unknowns": [
            {
                "code": "KUBERNETES_EVENT_OBSERVATION_FAILED",
                "statement": "Recent Kubernetes Event evidence is unknown because the current read failed.",
                "evidence_ids": [],
            }
        ],
        "errors": [{"scope": "events", "code": code, "summary": summary}],
    }


def _namespace_from_subject(subject: str) -> str | None:
    parts = subject.split("/")
    if len(parts) == 3:
        return parts[1]
    if len(parts) == 2 and parts[0] == "Namespace":
        return parts[1]
    return None


def _correlation_basis(attention: dict[str, Any], event: dict[str, Any]) -> list[str] | None:
    scope = attention.get("scope", {})
    scope_type = scope.get("type")
    scope_subject = scope.get("subject")
    event_subject = event.get("subject")

    if scope_type in {"WORKLOAD", "NODE", "SERVICE"} and scope_subject == event_subject:
        return ["DIRECT_OBJECT_IDENTITY", "RECENT_KUBERNETES_WARNING_EVENT"]

    if scope_type == "NAMESPACE":
        namespace = _namespace_from_subject(str(scope_subject or ""))
        regarding_namespace = event.get("regarding", {}).get("namespace")
        if namespace and regarding_namespace == namespace:
            return ["NAMESPACE_SCOPE_MEMBERSHIP", "RECENT_KUBERNETES_WARNING_EVENT"]

    return None


def build_event_correlation(
    event_runtime: dict[str, Any],
    alert_attention: dict[str, Any],
) -> dict[str, Any]:
    """Relate recent Warning Events to current alert attention without claiming root cause."""
    if event_runtime.get("cluster_id") != alert_attention.get("cluster_id"):
        raise ValueError("Kubernetes Event and alert-attention evidence must target the same cluster")

    source_status = event_runtime.get("source", {}).get("status", "FAILED_TO_OBSERVE")
    correlations: list[dict[str, Any]] = []
    matched_event_ids: set[str] = set()

    warnings = [item for item in event_runtime.get("events", []) if item.get("type") == "WARNING"]

    for attention in alert_attention.get("attention", []):
        related: list[dict[str, Any]] = []
        for event in warnings:
            basis = _correlation_basis(attention, event)
            if not basis:
                continue
            matched_event_ids.add(event["event_id"])
            related.append(
                {
                    "event_id": event["event_id"],
                    "subject": event["subject"],
                    "reason": event["reason"],
                    "last_seen": event["last_seen"],
                    "count": event["count"],
                    "basis": basis,
                    "evidence_ids": [event["evidence_id"]],
                }
            )

        related.sort(key=lambda item: item["last_seen"], reverse=True)
        if related:
            status = "MATCHED"
        elif source_status == "COMPLETE":
            status = "NO_DIRECT_EVENT_MATCH"
        else:
            status = "UNKNOWN"
        correlations.append(
            {
                "attention_id": attention["attention_id"],
                "attention_scope": attention["scope"],
                "handling_state": attention["handling_state"],
                "correlation_status": status,
                "related_warning_events": related[:20],
                "evidence_ids": list(
                    dict.fromkeys(
                        attention.get("evidence_ids", [])
                        + [eid for item in related for eid in item["evidence_ids"]]
                    )
                ),
            }
        )

    status_counts = Counter(item["correlation_status"] for item in correlations)
    return {
        "event_correlation_version": EVENT_CORRELATION_VERSION,
        "cluster_id": event_runtime["cluster_id"],
        "generated_at": event_runtime["generated_at"],
        "mutation_allowed": False,
        "source_status": {
            "kubernetes_events": source_status,
            "alert_attention": "COMPLETE"
            if alert_attention.get("source_status", {}).get("prometheus") == "COMPLETE"
            and alert_attention.get("source_status", {}).get("alertmanager") == "COMPLETE"
            else "PARTIAL",
        },
        "summary": {
            "attention_records": len(correlations),
            "attention_with_related_warning_events": status_counts["MATCHED"],
            "attention_without_direct_warning_match": status_counts["NO_DIRECT_EVENT_MATCH"],
            "attention_event_correlation_unknown": status_counts["UNKNOWN"],
            "warning_events_recent": len(warnings),
            "warning_events_related_to_attention": len(matched_event_ids),
            "warning_events_without_attention_match": len(warnings) - len(matched_event_ids),
        },
        "correlations": correlations,
        "caveats": [
            "Kubernetes Event messages are intentionally not persisted; correlation uses structured Event metadata only.",
            "A related recent Event is supporting operational context and is not a root-cause conclusion.",
            "Namespace-scope correlation means the Event involved an object in that namespace; it does not prove the alert and Event share one cause.",
            "Platform-scoped alerts are not automatically correlated to all cluster Events because that would create overly broad causal-looking associations.",
            "Pod Events are not promoted to workload ownership without a separate evidence-backed owner-reference path.",
        ],
    }


def render_kubernetes_event_markdown(runtime: dict[str, Any]) -> str:
    summary = runtime["summary"]
    lines = [
        "# Kubernetes Event Runtime Evidence",
        "",
        f"Cluster: `{runtime['cluster_id']}`",
        f"Generated: `{runtime['generated_at']}`",
        f"Source status: `{runtime['source']['status']}`",
        f"Window: `{runtime['source']['window_seconds']}` seconds",
        "Mutation allowed: `false`",
        "",
        "## Summary",
        "",
        f"- Events returned by API: {summary['events_seen_from_api']}",
        f"- Recent bounded events: {summary['events_recent']}",
        f"- Warning: {summary['events_warning']}",
        f"- Normal: {summary['events_normal']}",
        f"- Unknown type: {summary['events_unknown_type']}",
        f"- Window truncated: {str(summary['window_truncated']).lower()}",
        "",
        "## Recent warnings",
        "",
    ]
    warnings = [item for item in runtime["events"] if item["type"] == "WARNING"]
    if warnings:
        for item in warnings[:50]:
            lines.append(
                f"- {item['reason']} subject={item['subject']} last_seen={item['last_seen']} count={item['count']}"
            )
    else:
        lines.append("- none")
    lines += [
        "",
        "## Trust boundary",
        "",
        "Raw Kubernetes Event messages and source host fields are not persisted. Event metadata is recent supporting evidence, not a root-cause conclusion.",
    ]
    return "\n".join(lines) + "\n"


def render_event_correlation_markdown(correlation: dict[str, Any]) -> str:
    summary = correlation["summary"]
    lines = [
        "# Kubernetes Event / Alert Attention Correlation",
        "",
        f"Cluster: `{correlation['cluster_id']}`",
        f"Generated: `{correlation['generated_at']}`",
        f"Kubernetes Event source: `{correlation['source_status']['kubernetes_events']}`",
        "Mutation allowed: `false`",
        "",
        "## Summary",
        "",
        f"- Alert attention records: {summary['attention_records']}",
        f"- Attention with related Warning Events: {summary['attention_with_related_warning_events']}",
        f"- Attention without direct Warning match: {summary['attention_without_direct_warning_match']}",
        f"- Correlation unknown: {summary['attention_event_correlation_unknown']}",
        f"- Recent Warning Events: {summary['warning_events_recent']}",
        f"- Warning Events related to attention: {summary['warning_events_related_to_attention']}",
        f"- Warning Events without attention match: {summary['warning_events_without_attention_match']}",
        "",
        "## Related current attention",
        "",
    ]
    matched = [item for item in correlation["correlations"] if item["correlation_status"] == "MATCHED"]
    if matched:
        for item in matched:
            lines.append(
                f"- {item['attention_scope']['subject']} handling={item['handling_state']} related_warnings={len(item['related_warning_events'])}"
            )
            for event in item["related_warning_events"][:10]:
                lines.append(
                    f"  - {event['reason']} subject={event['subject']} last_seen={event['last_seen']} count={event['count']} basis={'+'.join(event['basis'])}"
                )
    else:
        lines.append("- none")
    lines += [
        "",
        "## Trust boundary",
        "",
        "Correlation means only that a recent structured Kubernetes Warning Event falls within the same supported object or namespace scope. It is not a root-cause claim.",
    ]
    return "\n".join(lines) + "\n"
