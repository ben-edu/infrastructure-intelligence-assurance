from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

RUNTIME_VERSION = "0.1"
DEFAULT_TTL_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_PROMETHEUS_NAMESPACE = "monitoring"
DEFAULT_PROMETHEUS_SERVICE = "kube-prom-stack-prometheus"
DEFAULT_PROMETHEUS_PORT = 9090
Runner = Callable[..., subprocess.CompletedProcess[str]]

TARGET_LABEL_ALLOWLIST = {
    "namespace",
    "service",
    "job",
    "endpoint",
    "pod",
    "container",
}
ALERT_LABEL_ALLOWLIST = {
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


def _label(subject: dict[str, Any]) -> str:
    namespace = f"{subject['namespace']}/" if subject.get("namespace") else ""
    return f"{subject['kind']}/{namespace}{subject['name']}"


def _sanitize_labels(value: Any, allowlist: set[str]) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in value.items():
        if key not in allowlist:
            continue
        if isinstance(item, (str, int, float, bool)):
            result[str(key)] = str(item)
    return result


def _stable_hash(*parts: Any) -> str:
    material = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _proxy_path(
    *,
    namespace: str,
    service: str,
    port: int,
    api_path: str,
) -> str:
    suffix = api_path.lstrip("/")
    return (
        f"/api/v1/namespaces/{namespace}/services/{service}:{port}/proxy/{suffix}"
    )


def _classify_proxy_failure(stderr: str) -> tuple[str, str]:
    lowered = stderr.lower()
    if "forbidden" in lowered:
        return (
            "PROMETHEUS_PROXY_FORBIDDEN",
            "Kubernetes API denied the read-only Prometheus service-proxy request.",
        )
    if "not found" in lowered:
        return (
            "PROMETHEUS_SERVICE_UNAVAILABLE",
            "The configured Prometheus Service proxy endpoint is unavailable.",
        )
    if "timeout" in lowered or "timed out" in lowered:
        return (
            "PROMETHEUS_PROXY_TIMEOUT",
            "The read-only Prometheus service-proxy request timed out.",
        )
    if "connection refused" in lowered or "unable to connect" in lowered:
        return (
            "PROMETHEUS_PROXY_UNREACHABLE",
            "The Prometheus service-proxy endpoint could not be reached.",
        )
    return (
        "PROMETHEUS_PROXY_READ_FAILED",
        "The read-only Prometheus service-proxy request failed.",
    )


def _proxy_get_json(
    raw_path: str,
    *,
    kubectl_context: str | None,
    runner: Runner,
    timeout_seconds: int,
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
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
            "code": "PROMETHEUS_PROXY_TIMEOUT",
            "summary": "kubectl exceeded the local Prometheus proxy timeout.",
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
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, {
            "code": "PROMETHEUS_RESPONSE_INVALID",
            "summary": "Prometheus returned a response that could not be normalized safely.",
        }

    if not isinstance(payload, dict) or payload.get("status") != "success":
        return None, {
            "code": "PROMETHEUS_API_ERROR",
            "summary": "Prometheus API did not return a successful response.",
        }
    data = payload.get("data")
    if not isinstance(data, dict):
        return None, {
            "code": "PROMETHEUS_RESPONSE_INVALID",
            "summary": "Prometheus API response did not contain the expected data object.",
        }
    return data, None


def _target_error_code(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    lowered = value.lower()
    if "timeout" in lowered or "deadline exceeded" in lowered:
        return "TARGET_TIMEOUT"
    if "connection refused" in lowered:
        return "TARGET_CONNECTION_REFUSED"
    if "tls" in lowered or "certificate" in lowered or "x509" in lowered:
        return "TARGET_TLS_ERROR"
    if "server returned http status" in lowered or "status code" in lowered:
        return "TARGET_HTTP_ERROR"
    return "TARGET_SCRAPE_ERROR"


def _target_health(value: Any) -> str:
    lowered = str(value or "").lower()
    if lowered == "up":
        return "UP"
    if lowered == "down":
        return "DOWN"
    return "UNKNOWN"


def _normalize_targets(
    data: dict[str, Any],
    *,
    now: datetime,
    ttl_seconds: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    active = data.get("activeTargets")
    if not isinstance(active, list):
        return [], [
            {
                "code": "PROMETHEUS_TARGETS_RESPONSE_INVALID",
                "statement": "Prometheus target data did not contain an activeTargets list.",
                "evidence_ids": [],
            }
        ]

    records: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for item in active:
        if not isinstance(item, dict):
            continue
        labels = _sanitize_labels(item.get("labels"), TARGET_LABEL_ALLOWLIST)
        target_id = "prom-target-" + _stable_hash(
            item.get("scrapeUrl"),
            labels,
            item.get("scrapePool"),
        )
        evidence_id = f"ev-prometheus-target-{uuid.uuid4()}"
        health = _target_health(item.get("health"))
        duration = item.get("lastScrapeDuration")
        if not isinstance(duration, (int, float)):
            duration = None
        last_scrape = item.get("lastScrape")
        if not isinstance(last_scrape, str) or not last_scrape:
            last_scrape = None
        error_code = _target_error_code(item.get("lastError"))
        records.append(
            {
                "target_id": target_id,
                "evidence_id": evidence_id,
                "observed_at": _rfc3339(now),
                "expires_at": _rfc3339(now + timedelta(seconds=ttl_seconds)),
                "health": health,
                "labels": labels,
                "last_scrape": last_scrape,
                "last_scrape_duration_seconds": duration,
                "error_code": error_code,
            }
        )
        if health == "UNKNOWN":
            unknowns.append(
                {
                    "code": "PROMETHEUS_TARGET_HEALTH_UNKNOWN",
                    "statement": f"Prometheus target {target_id} did not report a recognized up/down health state.",
                    "evidence_ids": [evidence_id],
                }
            )
    return records, unknowns


def _normalize_alerts(
    data: dict[str, Any],
    *,
    now: datetime,
    ttl_seconds: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items = data.get("alerts")
    if not isinstance(items, list):
        return [], [
            {
                "code": "PROMETHEUS_ALERTS_RESPONSE_INVALID",
                "statement": "Prometheus alert data did not contain an alerts list.",
                "evidence_ids": [],
            }
        ]

    records: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        labels = _sanitize_labels(item.get("labels"), ALERT_LABEL_ALLOWLIST)
        raw_state = str(item.get("state") or "").lower()
        if raw_state == "firing":
            state = "FIRING"
        elif raw_state == "pending":
            state = "PENDING"
        else:
            state = "UNKNOWN"
        active_at = item.get("activeAt")
        if not isinstance(active_at, str) or not active_at:
            active_at = None
        alert_id = "prom-alert-" + _stable_hash(labels, active_at, state)
        evidence_id = f"ev-prometheus-alert-{uuid.uuid4()}"
        records.append(
            {
                "alert_id": alert_id,
                "evidence_id": evidence_id,
                "observed_at": _rfc3339(now),
                "expires_at": _rfc3339(now + timedelta(seconds=ttl_seconds)),
                "state": state,
                "active_at": active_at,
                "labels": labels,
            }
        )
        if state == "UNKNOWN":
            unknowns.append(
                {
                    "code": "PROMETHEUS_ALERT_STATE_UNKNOWN",
                    "statement": f"Prometheus alert {alert_id} had an unrecognized runtime state.",
                    "evidence_ids": [evidence_id],
                }
            )
    return records, unknowns


def _service_to_workloads(topology: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for relation in topology.get("relations", []):
        if relation.get("type") != "SERVICE_SELECTOR_MATCHES_WORKLOAD":
            continue
        result.setdefault(relation["source"], []).append(relation)
    return result


def _workload_labels(snapshot: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for envelope in snapshot.get("evidence", []):
        subject = envelope.get("subject", {})
        if subject.get("kind") not in {"Deployment", "StatefulSet", "DaemonSet"}:
            continue
        if envelope.get("plane") != "observed":
            continue
        if envelope.get("existence") != "PRESENT":
            continue
        if envelope.get("observation_status") != "COMPLETE":
            continue
        result.append(_label(subject))
    return sorted(result)


def _service_label(labels: dict[str, str]) -> str | None:
    namespace = labels.get("namespace")
    service = labels.get("service")
    if namespace and service:
        return f"Service/{namespace}/{service}"
    return None


def _attribute_to_workloads(
    *,
    targets: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    topology: dict[str, Any],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
    list[dict[str, Any]],
]:
    service_to_workloads = _service_to_workloads(topology)
    targets_by_workload: dict[str, list[dict[str, Any]]] = {}
    alerts_by_workload: dict[str, list[dict[str, Any]]] = {}
    unknowns: list[dict[str, Any]] = []

    for target in targets:
        service_label = _service_label(target["labels"])
        if not service_label:
            continue
        relations = service_to_workloads.get(service_label, [])
        if not relations:
            unknowns.append(
                {
                    "code": "PROMETHEUS_TARGET_WORKLOAD_MAPPING_UNRESOLVED",
                    "statement": f"Target {target['target_id']} identifies {service_label}, but no current Service-to-workload selector inference is available.",
                    "evidence_ids": [target["evidence_id"]],
                }
            )
            continue
        for relation in relations:
            workload = relation["target"]
            targets_by_workload.setdefault(workload, []).append(
                {
                    "target_id": target["target_id"],
                    "health": target["health"],
                    "labels": target["labels"],
                    "last_scrape": target["last_scrape"],
                    "last_scrape_duration_seconds": target[
                        "last_scrape_duration_seconds"
                    ],
                    "error_code": target["error_code"],
                    "basis": [
                        "PROMETHEUS_RUNTIME_TARGET_SERVICE_LABEL",
                        "SERVICE_SELECTOR_MATCH_INFERENCE",
                    ],
                    "evidence_ids": list(
                        dict.fromkeys(
                            [target["evidence_id"]]
                            + relation.get("evidence_ids", [])
                        )
                    ),
                }
            )

    for alert in alerts:
        service_label = _service_label(alert["labels"])
        if not service_label:
            continue
        relations = service_to_workloads.get(service_label, [])
        if not relations:
            unknowns.append(
                {
                    "code": "PROMETHEUS_ALERT_WORKLOAD_MAPPING_UNRESOLVED",
                    "statement": f"Alert {alert['alert_id']} identifies {service_label}, but no current Service-to-workload selector inference is available.",
                    "evidence_ids": [alert["evidence_id"]],
                }
            )
            continue
        for relation in relations:
            workload = relation["target"]
            alerts_by_workload.setdefault(workload, []).append(
                {
                    "alert_id": alert["alert_id"],
                    "state": alert["state"],
                    "active_at": alert["active_at"],
                    "labels": alert["labels"],
                    "basis": [
                        "PROMETHEUS_ACTIVE_ALERT_SERVICE_LABEL",
                        "SERVICE_SELECTOR_MATCH_INFERENCE",
                    ],
                    "evidence_ids": list(
                        dict.fromkeys(
                            [alert["evidence_id"]]
                            + relation.get("evidence_ids", [])
                        )
                    ),
                }
            )

    return targets_by_workload, alerts_by_workload, unknowns


def _workload_runtime_state(
    targets: list[dict[str, Any]],
    alerts: list[dict[str, Any]],
    *,
    source_status: str,
) -> str:
    if source_status != "COMPLETE":
        return "UNKNOWN"
    if any(target.get("health") == "DOWN" for target in targets):
        return "PROMETHEUS_TARGET_DOWN"
    if any(target.get("health") == "UNKNOWN" for target in targets):
        return "UNKNOWN"
    if any(alert.get("state") in {"FIRING", "PENDING"} for alert in alerts):
        return "ACTIVE_ALERT"
    if targets:
        return "PROMETHEUS_TARGETS_UP"
    if alerts:
        return "ACTIVE_ALERT"
    return "NO_RUNTIME_SIGNAL_MATCH"


def build_prometheus_runtime_intelligence(
    snapshot: dict[str, Any],
    topology: dict[str, Any],
    *,
    kubectl_context: str | None = None,
    prometheus_namespace: str = DEFAULT_PROMETHEUS_NAMESPACE,
    prometheus_service: str = DEFAULT_PROMETHEUS_SERVICE,
    prometheus_port: int = DEFAULT_PROMETHEUS_PORT,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Read runtime Prometheus target/alert evidence without replacing Prometheus."""
    now = now or datetime.now(timezone.utc)
    cluster_id = snapshot["cluster_id"]
    if topology.get("cluster_id") != cluster_id:
        raise ValueError("Prometheus runtime inputs must target the same cluster")

    source_errors: list[dict[str, str]] = []
    unknowns: list[dict[str, Any]] = []

    targets_path = _proxy_path(
        namespace=prometheus_namespace,
        service=prometheus_service,
        port=prometheus_port,
        api_path="api/v1/targets?state=active",
    )
    alerts_path = _proxy_path(
        namespace=prometheus_namespace,
        service=prometheus_service,
        port=prometheus_port,
        api_path="api/v1/alerts",
    )

    targets_data, targets_error = _proxy_get_json(
        targets_path,
        kubectl_context=kubectl_context,
        runner=runner,
        timeout_seconds=timeout_seconds,
    )
    alerts_data, alerts_error = _proxy_get_json(
        alerts_path,
        kubectl_context=kubectl_context,
        runner=runner,
        timeout_seconds=timeout_seconds,
    )

    targets: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    if targets_error:
        source_errors.append({"scope": "targets", **targets_error})
    elif targets_data is not None:
        targets, target_unknowns = _normalize_targets(
            targets_data,
            now=now,
            ttl_seconds=ttl_seconds,
        )
        unknowns.extend(target_unknowns)

    if alerts_error:
        source_errors.append({"scope": "alerts", **alerts_error})
    elif alerts_data is not None:
        alerts, alert_unknowns = _normalize_alerts(
            alerts_data,
            now=now,
            ttl_seconds=ttl_seconds,
        )
        unknowns.extend(alert_unknowns)

    failed_scopes = {item["scope"] for item in source_errors}
    if failed_scopes == {"targets", "alerts"}:
        source_status = "FAILED_TO_OBSERVE"
    elif source_errors or unknowns:
        source_status = "PARTIAL"
    else:
        source_status = "COMPLETE"

    targets_by_workload, alerts_by_workload, mapping_unknowns = _attribute_to_workloads(
        targets=targets,
        alerts=alerts,
        topology=topology,
    )
    unknowns.extend(mapping_unknowns)

    # Mapping gaps do not make authoritative Prometheus observation itself partial.
    workload_labels = _workload_labels(snapshot)
    workload_runtime: list[dict[str, Any]] = []
    for workload_label in workload_labels:
        workload_targets = targets_by_workload.get(workload_label, [])
        workload_alerts = alerts_by_workload.get(workload_label, [])
        state = _workload_runtime_state(
            workload_targets,
            workload_alerts,
            source_status=source_status,
        )
        evidence_ids: list[str] = []
        for item in workload_targets + workload_alerts:
            evidence_ids.extend(item.get("evidence_ids", []))
        workload_runtime.append(
            {
                "subject": workload_label,
                "state": state,
                "targets": workload_targets,
                "active_alerts": workload_alerts,
                "evidence_ids": list(dict.fromkeys(evidence_ids)),
                "caveats": [
                    "PROMETHEUS_TARGETS_UP proves only that matched Prometheus scrape targets reported up at observation time; it does not prove application health.",
                    "Runtime target and alert attribution through a Service retains the existing selector-based Service-to-controller inference.",
                    "NO_RUNTIME_SIGNAL_MATCH means no attributable target or active alert was found in this runtime slice; it does not prove absence of monitoring or alerts outside the modeled path.",
                ],
            }
        )

    target_counts = Counter(item["health"] for item in targets)
    alert_counts = Counter(item["state"] for item in alerts)
    state_counts = Counter(item["state"] for item in workload_runtime)
    assigned_target_ids = {
        item["target_id"]
        for values in targets_by_workload.values()
        for item in values
    }
    assigned_alert_ids = {
        item["alert_id"]
        for values in alerts_by_workload.values()
        for item in values
    }

    return {
        "prometheus_runtime_version": RUNTIME_VERSION,
        "cluster_id": cluster_id,
        "generated_at": _rfc3339(now),
        "mutation_allowed": False,
        "source": {
            "type": "prometheus_http_api",
            "access": "kubernetes_service_proxy",
            "namespace": prometheus_namespace,
            "service": prometheus_service,
            "port": prometheus_port,
            "status": source_status,
        },
        "summary": {
            "targets_total": len(targets),
            "targets_up": target_counts["UP"],
            "targets_down": target_counts["DOWN"],
            "targets_unknown": target_counts["UNKNOWN"],
            "targets_attributed_to_workloads": len(assigned_target_ids),
            "targets_unattributed": len(targets) - len(assigned_target_ids),
            "active_alerts_total": len(alerts),
            "active_alerts_firing": alert_counts["FIRING"],
            "active_alerts_pending": alert_counts["PENDING"],
            "active_alerts_unknown": alert_counts["UNKNOWN"],
            "alerts_attributed_to_workloads": len(assigned_alert_ids),
            "alerts_unattributed": len(alerts) - len(assigned_alert_ids),
            "workloads_total": len(workload_runtime),
            "workloads_targets_up": state_counts["PROMETHEUS_TARGETS_UP"],
            "workloads_target_down": state_counts["PROMETHEUS_TARGET_DOWN"],
            "workloads_with_active_alert": state_counts["ACTIVE_ALERT"],
            "workloads_no_runtime_signal_match": state_counts["NO_RUNTIME_SIGNAL_MATCH"],
            "workloads_runtime_unknown": state_counts["UNKNOWN"],
        },
        "targets": targets,
        "active_alerts": alerts,
        "workload_runtime": workload_runtime,
        "unknowns": unknowns,
        "errors": source_errors,
    }


def attach_prometheus_runtime(
    inventory: dict[str, Any], runtime: dict[str, Any]
) -> dict[str, Any]:
    if inventory.get("cluster_id") != runtime.get("cluster_id"):
        raise ValueError("inventory and Prometheus runtime evidence must target the same cluster")

    result = copy.deepcopy(inventory)
    result["inventory_version"] = "0.3"
    runtime_index = {
        item["subject"]: item for item in runtime.get("workload_runtime", [])
    }
    source_status = runtime.get("source", {}).get("status", "FAILED_TO_OBSERVE")

    for entity in result.get("entities", []):
        workload_label = _label(entity["subject"])
        entity["runtime_observability"] = runtime_index.get(
            workload_label,
            {
                "subject": workload_label,
                "state": "UNKNOWN",
                "targets": [],
                "active_alerts": [],
                "evidence_ids": [],
                "caveats": [
                    "No Prometheus runtime record was produced for this workload."
                ],
            },
        )
        entity["evidence_ids"] = list(
            dict.fromkeys(
                entity.get("evidence_ids", [])
                + entity["runtime_observability"].get("evidence_ids", [])
            )
        )

    summary = runtime["summary"]
    result["summary"].update(
        {
            "prometheus_targets_total": summary["targets_total"],
            "prometheus_targets_up": summary["targets_up"],
            "prometheus_targets_down": summary["targets_down"],
            "prometheus_active_alerts": summary["active_alerts_total"],
            "workloads_prometheus_targets_up": summary["workloads_targets_up"],
            "workloads_prometheus_target_down": summary["workloads_target_down"],
            "workloads_with_active_prometheus_alert": summary[
                "workloads_with_active_alert"
            ],
            "workloads_no_runtime_signal_match": summary[
                "workloads_no_runtime_signal_match"
            ],
            "workloads_prometheus_runtime_unknown": summary[
                "workloads_runtime_unknown"
            ],
        }
    )
    result["prometheus_runtime_source_status"] = source_status
    return result


def render_prometheus_runtime_markdown(runtime: dict[str, Any]) -> str:
    summary = runtime["summary"]
    source = runtime["source"]
    lines = [
        "# Prometheus Runtime Intelligence",
        "",
        f"Cluster: `{runtime['cluster_id']}`",
        f"Generated: `{runtime['generated_at']}`",
        f"Source status: `{source['status']}`",
        "Mutation allowed: `false`",
        "",
        "## Target health",
        "",
        f"- Targets: {summary['targets_total']}",
        f"- Up: {summary['targets_up']}",
        f"- Down: {summary['targets_down']}",
        f"- Unknown: {summary['targets_unknown']}",
        f"- Attributed to workload entities: {summary['targets_attributed_to_workloads']}",
        f"- Unattributed: {summary['targets_unattributed']}",
        "",
        "## Active Prometheus alerts",
        "",
        f"- Active alerts: {summary['active_alerts_total']}",
        f"- Firing: {summary['active_alerts_firing']}",
        f"- Pending: {summary['active_alerts_pending']}",
        f"- Unknown: {summary['active_alerts_unknown']}",
        f"- Attributed to workload entities: {summary['alerts_attributed_to_workloads']}",
        f"- Unattributed: {summary['alerts_unattributed']}",
        "",
        "## Workload runtime signal state",
        "",
        f"- Prometheus targets up: {summary['workloads_targets_up']}",
        f"- Prometheus target down: {summary['workloads_target_down']}",
        f"- Active alert: {summary['workloads_with_active_alert']}",
        f"- No attributable runtime signal match: {summary['workloads_no_runtime_signal_match']}",
        f"- Unknown: {summary['workloads_runtime_unknown']}",
        "",
        "## Attention",
        "",
    ]

    attention = [
        item
        for item in runtime["workload_runtime"]
        if item["state"] in {"PROMETHEUS_TARGET_DOWN", "ACTIVE_ALERT", "UNKNOWN"}
    ]
    if attention:
        for item in attention:
            lines.append(f"- {item['subject']}: {item['state']}")
            for target in item["targets"]:
                if target["health"] != "UP":
                    labels = target.get("labels", {})
                    lines.append(
                        "  - target "
                        f"health={target['health']} "
                        f"namespace={labels.get('namespace')} "
                        f"service={labels.get('service')} "
                        f"error_code={target.get('error_code')}"
                    )
            for alert in item["active_alerts"]:
                labels = alert.get("labels", {})
                lines.append(
                    "  - alert "
                    f"state={alert['state']} "
                    f"alertname={labels.get('alertname')} "
                    f"severity={labels.get('severity')}"
                )
    else:
        lines.append("- No workload-attributed runtime attention in this observation.")

    lines.extend(["", "## Unknown or failed observation", ""])
    if runtime["errors"]:
        for error in runtime["errors"]:
            lines.append(f"- [{error['scope']}:{error['code']}] {error['summary']}")
    if runtime["unknowns"]:
        for item in runtime["unknowns"]:
            lines.append(f"- [{item['code']}] {item['statement']}")
    if not runtime["errors"] and not runtime["unknowns"]:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "Prometheus remains authoritative for target health and alert evaluation. This artifact stores a narrow current projection and does not persist raw scrape URLs, arbitrary target labels, alert annotations, metric series, credentials, or Secret values.",
            "A Prometheus target reporting UP proves scrape-target reachability at the observed time, not application correctness or user-visible health.",
            "Workload attribution through Service labels retains selector-based Service-to-controller inference and must not be treated as direct Pod ownership proof.",
            "",
        ]
    )
    return "\n".join(lines)


def render_inventory_runtime_markdown(
    inventory_markdown: str,
    runtime: dict[str, Any],
) -> str:
    summary = runtime["summary"]
    source_status = runtime["source"]["status"]
    extra = [
        "",
        "## Prometheus runtime signals",
        "",
        f"- Source status: `{source_status}`",
        f"- Targets up / down / unknown: {summary['targets_up']} / {summary['targets_down']} / {summary['targets_unknown']}",
        f"- Active alerts: {summary['active_alerts_total']}",
        f"- Workloads with target down: {summary['workloads_target_down']}",
        f"- Workloads with active alert: {summary['workloads_with_active_alert']}",
        f"- Workloads with runtime unknown: {summary['workloads_runtime_unknown']}",
        "",
        "Prometheus target health and active-alert state are authoritative runtime signals from Prometheus, but target-to-workload attribution can retain selector inference and does not by itself prove application health.",
        "",
    ]
    return inventory_markdown.rstrip() + "\n" + "\n".join(extra)
