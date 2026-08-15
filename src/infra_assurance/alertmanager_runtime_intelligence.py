from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

RUNTIME_VERSION = "0.1"
ATTENTION_VERSION = "0.1"
DEFAULT_TTL_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_ALERTMANAGER_NAMESPACE = "monitoring"
DEFAULT_ALERTMANAGER_SERVICE = "kube-prom-stack-alertmanager"
DEFAULT_ALERTMANAGER_PORT = 9093
Runner = Callable[..., subprocess.CompletedProcess[str]]

ALERT_LABEL_ALLOWLIST = {
    "alertname",
    "severity",
    "namespace",
    "service",
    "job",
    "pod",
    "container",
    "node",
}
PROMETHEUS_CORRELATION_KEYS = {
    "alertname",
    "severity",
    "namespace",
    "service",
    "job",
    "pod",
    "container",
}


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_hash(*parts: Any) -> str:
    material = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _sanitize_labels(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in value.items():
        if key not in ALERT_LABEL_ALLOWLIST:
            continue
        if isinstance(item, (str, int, float, bool)):
            result[str(key)] = str(item)
    return result


def _proxy_path(*, namespace: str, service: str, port: int, api_path: str) -> str:
    suffix = api_path.lstrip("/")
    return f"/api/v1/namespaces/{namespace}/services/{service}:{port}/proxy/{suffix}"


def _classify_proxy_failure(stderr: str) -> tuple[str, str]:
    lowered = stderr.lower()
    if "forbidden" in lowered:
        return (
            "ALERTMANAGER_PROXY_FORBIDDEN",
            "Kubernetes API denied the read-only Alertmanager service-proxy request.",
        )
    if "not found" in lowered:
        return (
            "ALERTMANAGER_SERVICE_UNAVAILABLE",
            "The configured Alertmanager Service proxy endpoint is unavailable.",
        )
    if "timeout" in lowered or "timed out" in lowered:
        return (
            "ALERTMANAGER_PROXY_TIMEOUT",
            "The read-only Alertmanager service-proxy request timed out.",
        )
    if "connection refused" in lowered or "unable to connect" in lowered:
        return (
            "ALERTMANAGER_PROXY_UNREACHABLE",
            "The Alertmanager service-proxy endpoint could not be reached.",
        )
    return (
        "ALERTMANAGER_PROXY_READ_FAILED",
        "The read-only Alertmanager service-proxy request failed.",
    )


def _proxy_get_json(
    raw_path: str,
    *,
    kubectl_context: str | None,
    runner: Runner,
    timeout_seconds: int,
) -> tuple[Any | None, dict[str, str] | None]:
    command = ["kubectl"]
    if kubectl_context:
        command += ["--context", kubectl_context]
    command += ["get", "--raw", raw_path]

    try:
        result = runner(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, {
            "code": "ALERTMANAGER_PROXY_TIMEOUT",
            "summary": "kubectl exceeded the local Alertmanager proxy timeout.",
        }
    except FileNotFoundError:
        return None, {
            "code": "KUBECTL_NOT_AVAILABLE",
            "summary": "kubectl is not available in the runtime observer.",
        }

    if result.returncode != 0:
        code, summary = _classify_proxy_failure(result.stderr)
        return None, {"code": code, "summary": summary}

    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError:
        return None, {
            "code": "ALERTMANAGER_RESPONSE_INVALID",
            "summary": "Alertmanager returned a response that could not be normalized safely.",
        }


def _normalize_alert_state(value: Any) -> str:
    raw = str(value or "").lower()
    if raw == "active":
        return "ACTIVE"
    if raw == "suppressed":
        return "SUPPRESSED"
    if raw == "unprocessed":
        return "UNPROCESSED"
    return "UNKNOWN"


def _handling_state(
    *,
    state: str,
    silenced_count: int,
    inhibited_count: int,
) -> str:
    if state == "UNPROCESSED":
        return "UNPROCESSED"
    if state == "UNKNOWN":
        return "UNKNOWN"
    if silenced_count and inhibited_count:
        return "SILENCED_AND_INHIBITED"
    if silenced_count:
        return "SILENCED"
    if inhibited_count:
        return "INHIBITED"
    if state == "SUPPRESSED":
        return "SUPPRESSED_OTHER"
    return "ACTIVE"


def _safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _normalize_alerts(
    payload: Any,
    *,
    now: datetime,
    ttl_seconds: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(payload, list):
        return [], [
            {
                "code": "ALERTMANAGER_ALERTS_RESPONSE_INVALID",
                "statement": "Alertmanager alert data was not a list.",
                "evidence_ids": [],
            }
        ]

    records: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue

        labels = _sanitize_labels(item.get("labels"))
        status = item.get("status") if isinstance(item.get("status"), dict) else {}
        state = _normalize_alert_state(status.get("state"))
        silenced_by = _safe_string_list(status.get("silencedBy"))
        inhibited_by = _safe_string_list(status.get("inhibitedBy"))
        muted_by = _safe_string_list(status.get("mutedBy"))
        handling_state = _handling_state(
            state=state,
            silenced_count=len(silenced_by),
            inhibited_count=len(inhibited_by),
        )

        raw_fingerprint = item.get("fingerprint")
        if not isinstance(raw_fingerprint, str) or not raw_fingerprint:
            raw_fingerprint = _stable_hash(labels, item.get("startsAt"), item.get("updatedAt"))
        alertmanager_alert_id = "am-alert-" + _stable_hash(raw_fingerprint)
        evidence_id = f"ev-alertmanager-alert-{uuid.uuid4()}"

        starts_at = item.get("startsAt") if isinstance(item.get("startsAt"), str) else None
        updated_at = item.get("updatedAt") if isinstance(item.get("updatedAt"), str) else None
        ends_at = item.get("endsAt") if isinstance(item.get("endsAt"), str) else None

        record = {
            "alertmanager_alert_id": alertmanager_alert_id,
            "evidence_id": evidence_id,
            "observed_at": _rfc3339(now),
            "expires_at": _rfc3339(now + timedelta(seconds=ttl_seconds)),
            "state": state,
            "handling_state": handling_state,
            "labels": labels,
            "starts_at": starts_at,
            "updated_at": updated_at,
            "ends_at": ends_at,
            "silence_refs": ["am-silence-" + _stable_hash(value) for value in silenced_by],
            "silenced_by_count": len(silenced_by),
            "inhibited_by_count": len(inhibited_by),
            "muted_by_count": len(muted_by),
        }
        records.append(record)

        if state == "UNKNOWN":
            unknowns.append(
                {
                    "code": "ALERTMANAGER_ALERT_STATE_UNKNOWN",
                    "statement": f"Alertmanager alert {alertmanager_alert_id} had an unrecognized processing state.",
                    "evidence_ids": [evidence_id],
                }
            )

    return records, unknowns


def _normalize_silences(
    payload: Any,
    *,
    now: datetime,
    ttl_seconds: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(payload, list):
        return [], [
            {
                "code": "ALERTMANAGER_SILENCES_RESPONSE_INVALID",
                "statement": "Alertmanager silence data was not a list.",
                "evidence_ids": [],
            }
        ]

    records: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id")
        if not isinstance(raw_id, str) or not raw_id:
            continue
        status = item.get("status") if isinstance(item.get("status"), dict) else {}
        raw_state = str(status.get("state") or "").lower()
        if raw_state == "active":
            state = "ACTIVE"
        elif raw_state == "pending":
            state = "PENDING"
        elif raw_state == "expired":
            state = "EXPIRED"
        else:
            state = "UNKNOWN"
        evidence_id = f"ev-alertmanager-silence-{uuid.uuid4()}"
        silence_ref = "am-silence-" + _stable_hash(raw_id)
        records.append(
            {
                "silence_ref": silence_ref,
                "evidence_id": evidence_id,
                "observed_at": _rfc3339(now),
                "expires_at": _rfc3339(now + timedelta(seconds=ttl_seconds)),
                "state": state,
                "starts_at": item.get("startsAt") if isinstance(item.get("startsAt"), str) else None,
                "ends_at": item.get("endsAt") if isinstance(item.get("endsAt"), str) else None,
                "updated_at": item.get("updatedAt") if isinstance(item.get("updatedAt"), str) else None,
            }
        )
        if state == "UNKNOWN":
            unknowns.append(
                {
                    "code": "ALERTMANAGER_SILENCE_STATE_UNKNOWN",
                    "statement": f"Alertmanager silence {silence_ref} had an unrecognized state.",
                    "evidence_ids": [evidence_id],
                }
            )
    return records, unknowns


def _correlation_projection(labels: dict[str, str]) -> tuple[tuple[str, str], ...] | None:
    projection = {
        key: labels[key]
        for key in sorted(PROMETHEUS_CORRELATION_KEYS)
        if key in labels and labels[key]
    }
    if not projection.get("alertname"):
        return None
    return tuple(sorted(projection.items()))


def _correlate_prometheus_alerts(
    alerts: list[dict[str, Any]],
    prometheus_runtime: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    index: dict[tuple[tuple[str, str], ...], list[dict[str, Any]]] = {}
    for item in prometheus_runtime.get("active_alerts", []):
        labels = item.get("labels") if isinstance(item.get("labels"), dict) else {}
        key = _correlation_projection(labels)
        if key is not None:
            index.setdefault(key, []).append(item)

    result: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for alert in alerts:
        item = dict(alert)
        key = _correlation_projection(alert["labels"])
        candidates = index.get(key, []) if key is not None else []
        if len(candidates) == 1:
            candidate = candidates[0]
            correlation = {
                "status": "MATCHED",
                "prometheus_alert_id": candidate["alert_id"],
                "evidence_ids": [candidate["evidence_id"]],
            }
        elif len(candidates) > 1:
            correlation = {
                "status": "AMBIGUOUS",
                "prometheus_alert_id": None,
                "evidence_ids": [candidate["evidence_id"] for candidate in candidates],
            }
            unknowns.append(
                {
                    "code": "ALERTMANAGER_PROMETHEUS_CORRELATION_AMBIGUOUS",
                    "statement": f"Alertmanager alert {alert['alertmanager_alert_id']} matched multiple normalized Prometheus alerts; no single correlation was selected.",
                    "evidence_ids": [alert["evidence_id"]] + correlation["evidence_ids"],
                }
            )
        else:
            correlation = {
                "status": "UNRESOLVED",
                "prometheus_alert_id": None,
                "evidence_ids": [],
            }
            unknowns.append(
                {
                    "code": "ALERTMANAGER_PROMETHEUS_CORRELATION_UNRESOLVED",
                    "statement": f"Alertmanager alert {alert['alertmanager_alert_id']} had no unique normalized Prometheus alert match.",
                    "evidence_ids": [alert["evidence_id"]],
                }
            )
        item["prometheus_correlation"] = correlation
        result.append(item)
    return result, unknowns


def _prometheus_workload_index(prometheus_runtime: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for workload in prometheus_runtime.get("workload_runtime", []):
        subject = workload.get("subject")
        if not isinstance(subject, str):
            continue
        for alert in workload.get("active_alerts", []):
            alert_id = alert.get("alert_id")
            if isinstance(alert_id, str):
                result.setdefault(alert_id, []).append(subject)
    return result


def _scope_for_alert(
    alert: dict[str, Any],
    workload_index: dict[str, list[str]],
    *,
    cluster_id: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    correlation = alert["prometheus_correlation"]
    prometheus_alert_id = correlation.get("prometheus_alert_id")
    workloads = workload_index.get(prometheus_alert_id, []) if prometheus_alert_id else []
    if len(workloads) == 1:
        return {
            "type": "WORKLOAD",
            "subject": workloads[0],
            "basis": [
                "ALERTMANAGER_PROMETHEUS_ALERT_CORRELATION",
                "SERVICE_SELECTOR_MATCH_INFERENCE",
            ],
        }, None

    labels = alert["labels"]
    if labels.get("node"):
        return {
            "type": "NODE",
            "subject": f"Node/{labels['node']}",
            "basis": ["ALERTMANAGER_NODE_LABEL"],
        }, None
    if labels.get("namespace") and labels.get("service"):
        return {
            "type": "SERVICE",
            "subject": f"Service/{labels['namespace']}/{labels['service']}",
            "basis": ["ALERTMANAGER_NAMESPACE_SERVICE_LABELS"],
        }, None
    if labels.get("namespace"):
        return {
            "type": "NAMESPACE",
            "subject": f"Namespace/{labels['namespace']}",
            "basis": ["ALERTMANAGER_NAMESPACE_LABEL"],
        }, None

    warning = None
    if len(workloads) > 1:
        warning = {
            "code": "ALERT_ATTENTION_WORKLOAD_SCOPE_AMBIGUOUS",
            "statement": f"Alertmanager alert {alert['alertmanager_alert_id']} correlates with a Prometheus alert associated with multiple workload candidates; platform scope was retained instead.",
            "evidence_ids": [alert["evidence_id"]] + correlation.get("evidence_ids", []),
        }
    return {
        "type": "PLATFORM",
        "subject": f"Platform/{cluster_id}",
        "basis": ["ALERTMANAGER_ALERT_WITHOUT_SUPPORTED_RESOURCE_SCOPE"],
    }, warning


def build_alertmanager_runtime_intelligence(
    prometheus_runtime: dict[str, Any],
    *,
    kubectl_context: str | None = None,
    alertmanager_namespace: str = DEFAULT_ALERTMANAGER_NAMESPACE,
    alertmanager_service: str = DEFAULT_ALERTMANAGER_SERVICE,
    alertmanager_port: int = DEFAULT_ALERTMANAGER_PORT,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Read narrow Alertmanager handling evidence and correlate it conservatively."""
    now = now or datetime.now(timezone.utc)
    cluster_id = prometheus_runtime["cluster_id"]

    alerts_path = _proxy_path(
        namespace=alertmanager_namespace,
        service=alertmanager_service,
        port=alertmanager_port,
        api_path="api/v2/alerts?active=true&silenced=true&inhibited=true&unprocessed=true",
    )
    silences_path = _proxy_path(
        namespace=alertmanager_namespace,
        service=alertmanager_service,
        port=alertmanager_port,
        api_path="api/v2/silences?active=true&expired=false&pending=true",
    )

    alerts_payload, alerts_error = _proxy_get_json(
        alerts_path,
        kubectl_context=kubectl_context,
        runner=runner,
        timeout_seconds=timeout_seconds,
    )
    silences_payload, silences_error = _proxy_get_json(
        silences_path,
        kubectl_context=kubectl_context,
        runner=runner,
        timeout_seconds=timeout_seconds,
    )

    errors: list[dict[str, Any]] = []
    source_unknowns: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    silences: list[dict[str, Any]] = []

    if alerts_error:
        errors.append({"scope": "alerts", **alerts_error})
    else:
        alerts, normalized_unknowns = _normalize_alerts(
            alerts_payload,
            now=now,
            ttl_seconds=ttl_seconds,
        )
        source_unknowns.extend(normalized_unknowns)

    if silences_error:
        errors.append({"scope": "silences", **silences_error})
    else:
        silences, normalized_unknowns = _normalize_silences(
            silences_payload,
            now=now,
            ttl_seconds=ttl_seconds,
        )
        source_unknowns.extend(normalized_unknowns)

    failed_scopes = {item["scope"] for item in errors}
    if failed_scopes == {"alerts", "silences"}:
        source_status = "FAILED_TO_OBSERVE"
    elif errors or source_unknowns:
        source_status = "PARTIAL"
    else:
        source_status = "COMPLETE"

    correlated_alerts, correlation_unknowns = _correlate_prometheus_alerts(
        alerts,
        prometheus_runtime,
    )
    unknowns = source_unknowns + correlation_unknowns

    alert_state_counts = Counter(item["state"] for item in correlated_alerts)
    handling_counts = Counter(item["handling_state"] for item in correlated_alerts)
    correlation_counts = Counter(
        item["prometheus_correlation"]["status"] for item in correlated_alerts
    )
    silence_counts = Counter(item["state"] for item in silences)

    return {
        "alertmanager_runtime_version": RUNTIME_VERSION,
        "cluster_id": cluster_id,
        "generated_at": _rfc3339(now),
        "mutation_allowed": False,
        "source": {
            "type": "alertmanager_http_api_v2",
            "access": "kubernetes_service_proxy",
            "namespace": alertmanager_namespace,
            "service": alertmanager_service,
            "port": alertmanager_port,
            "status": source_status,
        },
        "summary": {
            "alerts_total": len(correlated_alerts),
            "alerts_active": alert_state_counts["ACTIVE"],
            "alerts_suppressed": alert_state_counts["SUPPRESSED"],
            "alerts_unprocessed": alert_state_counts["UNPROCESSED"],
            "alerts_unknown": alert_state_counts["UNKNOWN"],
            "alerts_silenced": handling_counts["SILENCED"],
            "alerts_inhibited": handling_counts["INHIBITED"],
            "alerts_silenced_and_inhibited": handling_counts["SILENCED_AND_INHIBITED"],
            "alerts_suppressed_other": handling_counts["SUPPRESSED_OTHER"],
            "prometheus_correlations_matched": correlation_counts["MATCHED"],
            "prometheus_correlations_unresolved": correlation_counts["UNRESOLVED"],
            "prometheus_correlations_ambiguous": correlation_counts["AMBIGUOUS"],
            "silences_total": len(silences),
            "silences_active": silence_counts["ACTIVE"],
            "silences_pending": silence_counts["PENDING"],
            "silences_unknown": silence_counts["UNKNOWN"],
        },
        "alerts": correlated_alerts,
        "silences": silences,
        "unknowns": unknowns,
        "errors": errors,
    }


def build_alert_attention(
    prometheus_runtime: dict[str, Any],
    alertmanager_runtime: dict[str, Any],
) -> dict[str, Any]:
    if prometheus_runtime.get("cluster_id") != alertmanager_runtime.get("cluster_id"):
        raise ValueError("Prometheus and Alertmanager runtime evidence must target the same cluster")

    cluster_id = alertmanager_runtime["cluster_id"]
    workload_index = _prometheus_workload_index(prometheus_runtime)
    attention: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []

    for alert in alertmanager_runtime.get("alerts", []):
        scope, warning = _scope_for_alert(alert, workload_index, cluster_id=cluster_id)
        if warning:
            unknowns.append(warning)
        correlation = alert["prometheus_correlation"]
        evidence_ids = [alert["evidence_id"]] + correlation.get("evidence_ids", [])
        attention.append(
            {
                "attention_id": "alert-attention-" + _stable_hash(alert["alertmanager_alert_id"]),
                "alertmanager_alert_id": alert["alertmanager_alert_id"],
                "prometheus_alert_id": correlation.get("prometheus_alert_id"),
                "correlation_status": correlation["status"],
                "state": alert["state"],
                "handling_state": alert["handling_state"],
                "labels": alert["labels"],
                "scope": scope,
                "starts_at": alert["starts_at"],
                "updated_at": alert["updated_at"],
                "ends_at": alert["ends_at"],
                "silence_refs": alert["silence_refs"],
                "evidence_ids": list(dict.fromkeys(evidence_ids)),
            }
        )

    scope_counts = Counter(item["scope"]["type"] for item in attention)
    handling_counts = Counter(item["handling_state"] for item in attention)
    correlation_counts = Counter(item["correlation_status"] for item in attention)

    return {
        "alert_attention_version": ATTENTION_VERSION,
        "cluster_id": cluster_id,
        "generated_at": alertmanager_runtime["generated_at"],
        "mutation_allowed": False,
        "source_status": {
            "prometheus": prometheus_runtime.get("source", {}).get("status", "FAILED_TO_OBSERVE"),
            "alertmanager": alertmanager_runtime.get("source", {}).get("status", "FAILED_TO_OBSERVE"),
        },
        "summary": {
            "attention_total": len(attention),
            "active": handling_counts["ACTIVE"],
            "silenced": handling_counts["SILENCED"],
            "inhibited": handling_counts["INHIBITED"],
            "silenced_and_inhibited": handling_counts["SILENCED_AND_INHIBITED"],
            "suppressed_other": handling_counts["SUPPRESSED_OTHER"],
            "unprocessed": handling_counts["UNPROCESSED"],
            "unknown_handling": handling_counts["UNKNOWN"],
            "scope_workload": scope_counts["WORKLOAD"],
            "scope_node": scope_counts["NODE"],
            "scope_service": scope_counts["SERVICE"],
            "scope_namespace": scope_counts["NAMESPACE"],
            "scope_platform": scope_counts["PLATFORM"],
            "correlation_matched": correlation_counts["MATCHED"],
            "correlation_unresolved": correlation_counts["UNRESOLVED"],
            "correlation_ambiguous": correlation_counts["AMBIGUOUS"],
        },
        "attention": attention,
        "unknowns": unknowns,
        "caveats": [
            "Alertmanager handling state is authoritative for silencing/inhibition processing at observation time; it does not prove notification delivery to an external receiver.",
            "Receiver configuration, receiver names, free-form annotations, notification payloads, and credentials are intentionally excluded.",
            "Resource scope is label-based unless a unique existing Prometheus-to-workload inference path is available; unsupported ownership is not invented.",
        ],
    }


def render_alertmanager_runtime_markdown(runtime: dict[str, Any]) -> str:
    summary = runtime["summary"]
    lines = [
        "# Alertmanager Runtime Intelligence",
        "",
        f"Cluster: `{runtime['cluster_id']}`",
        f"Generated: `{runtime['generated_at']}`",
        f"Source status: `{runtime['source']['status']}`",
        "Mutation allowed: `false`",
        "",
        "## Alert handling",
        "",
        f"- Alerts: {summary['alerts_total']}",
        f"- Active: {summary['alerts_active']}",
        f"- Suppressed: {summary['alerts_suppressed']}",
        f"- Unprocessed: {summary['alerts_unprocessed']}",
        f"- Silenced: {summary['alerts_silenced']}",
        f"- Inhibited: {summary['alerts_inhibited']}",
        f"- Silenced and inhibited: {summary['alerts_silenced_and_inhibited']}",
        "",
        "## Prometheus correlation",
        "",
        f"- Matched: {summary['prometheus_correlations_matched']}",
        f"- Unresolved: {summary['prometheus_correlations_unresolved']}",
        f"- Ambiguous: {summary['prometheus_correlations_ambiguous']}",
        "",
        "## Silences",
        "",
        f"- Observed active/pending silences: {summary['silences_total']}",
        f"- Active: {summary['silences_active']}",
        f"- Pending: {summary['silences_pending']}",
    ]

    if runtime.get("errors"):
        lines += ["", "## Failed observation", ""]
        for item in runtime["errors"]:
            lines.append(f"- [{item['scope']}:{item['code']}] {item['summary']}")

    if runtime.get("unknowns"):
        lines += ["", "## Unknown / unresolved", ""]
        for item in runtime["unknowns"][:30]:
            lines.append(f"- [{item['code']}] {item['statement']}")

    lines += [
        "",
        "## Trust boundary",
        "",
        "Alertmanager remains authoritative for alert handling, silencing, and inhibition state. This artifact excludes receiver configuration, receiver names, free-form annotations, notification payloads, arbitrary labels, and credentials.",
        "Correlation to Prometheus is only accepted when the normalized allowlisted label projection has one unique match.",
    ]
    return "\n".join(lines) + "\n"


def render_alert_attention_markdown(attention: dict[str, Any]) -> str:
    summary = attention["summary"]
    lines = [
        "# Operational Alert Attention",
        "",
        f"Cluster: `{attention['cluster_id']}`",
        f"Generated: `{attention['generated_at']}`",
        f"Prometheus source: `{attention['source_status']['prometheus']}`",
        f"Alertmanager source: `{attention['source_status']['alertmanager']}`",
        "Mutation allowed: `false`",
        "",
        "## Summary",
        "",
        f"- Alert attention records: {summary['attention_total']}",
        f"- Active: {summary['active']}",
        f"- Silenced: {summary['silenced']}",
        f"- Inhibited: {summary['inhibited']}",
        f"- Correlated to Prometheus: {summary['correlation_matched']}",
        f"- Correlation unresolved: {summary['correlation_unresolved']}",
        f"- Correlation ambiguous: {summary['correlation_ambiguous']}",
        f"- Workload scoped: {summary['scope_workload']}",
        f"- Node scoped: {summary['scope_node']}",
        f"- Service scoped: {summary['scope_service']}",
        f"- Namespace scoped: {summary['scope_namespace']}",
        f"- Platform scoped: {summary['scope_platform']}",
        "",
        "## Current attention",
        "",
    ]

    for item in attention.get("attention", []):
        labels = item["labels"]
        name = labels.get("alertname", item["alertmanager_alert_id"])
        severity = labels.get("severity", "unknown")
        lines.append(
            f"- [{item['handling_state']}] {name} severity={severity} scope={item['scope']['subject']} correlation={item['correlation_status']}"
        )

    if attention.get("unknowns"):
        lines += ["", "## Scope / correlation unknowns", ""]
        for item in attention["unknowns"][:30]:
            lines.append(f"- [{item['code']}] {item['statement']}")

    lines += ["", "## Trust boundary", ""]
    lines.extend(attention["caveats"])
    return "\n".join(lines) + "\n"
