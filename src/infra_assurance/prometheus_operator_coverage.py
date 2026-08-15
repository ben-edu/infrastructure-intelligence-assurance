from __future__ import annotations

import copy
import json
import subprocess
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

COVERAGE_VERSION = "0.1"
DEFAULT_TTL_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 30
Runner = Callable[..., subprocess.CompletedProcess[str]]
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet"}


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _label(subject: dict[str, Any]) -> str:
    namespace = f"{subject['namespace']}/" if subject.get("namespace") else ""
    return f"{subject['kind']}/{namespace}{subject['name']}"


def _metadata_labels(item: dict[str, Any]) -> dict[str, str]:
    labels = item.get("metadata", {}).get("labels", {})
    if not isinstance(labels, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in labels.items()
        if isinstance(key, str) and isinstance(value, (str, int, float, bool))
    }


def _subject(
    cluster_id: str,
    *,
    api_group: str,
    kind: str,
    namespace: str | None,
    name: str,
) -> dict[str, Any]:
    return {
        "system": "kubernetes",
        "cluster": cluster_id,
        "api_group": api_group,
        "kind": kind,
        "namespace": namespace,
        "name": name,
    }


def _evidence_id(kind: str) -> str:
    return f"ev-observability-{kind.lower()}-{uuid.uuid4()}"


def _selector(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        return {"valid": False, "match_labels": {}, "match_expressions": []}

    match_labels = value.get("matchLabels", {})
    match_expressions = value.get("matchExpressions", [])
    valid = isinstance(match_labels, dict) and isinstance(match_expressions, list)
    normalized_expressions: list[dict[str, Any]] = []

    if isinstance(match_expressions, list):
        for item in match_expressions:
            if not isinstance(item, dict):
                valid = False
                continue
            key = item.get("key")
            operator = item.get("operator")
            values = item.get("values", [])
            if not isinstance(key, str) or not key:
                valid = False
                continue
            if operator not in {"In", "NotIn", "Exists", "DoesNotExist"}:
                valid = False
                continue
            if not isinstance(values, list):
                valid = False
                continue
            normalized_expressions.append(
                {
                    "key": key,
                    "operator": operator,
                    "values": [str(entry) for entry in values],
                }
            )

    return {
        "valid": valid,
        "match_labels": {
            str(key): str(item)
            for key, item in match_labels.items()
            if isinstance(key, str) and isinstance(item, (str, int, float, bool))
        }
        if isinstance(match_labels, dict)
        else {},
        "match_expressions": normalized_expressions,
    }


def _namespace_target_selector(value: Any) -> dict[str, Any]:
    if value is None:
        return {"valid": True, "mode": "SAME_NAMESPACE", "match_names": []}
    if not isinstance(value, dict):
        return {"valid": False, "mode": "UNKNOWN", "match_names": []}
    if value.get("any") is True:
        return {"valid": True, "mode": "ANY", "match_names": []}
    names = value.get("matchNames", [])
    if names is None:
        names = []
    if not isinstance(names, list):
        return {"valid": False, "mode": "UNKNOWN", "match_names": []}
    if names:
        return {
            "valid": True,
            "mode": "MATCH_NAMES",
            "match_names": [str(name) for name in names if isinstance(name, str) and name],
        }
    return {"valid": True, "mode": "SAME_NAMESPACE", "match_names": []}


def _selector_matches(selector: dict[str, Any], labels: dict[str, str]) -> bool | None:
    if selector.get("valid") is False:
        return None

    for key, expected in selector.get("match_labels", {}).items():
        if labels.get(key) != expected:
            return False

    for requirement in selector.get("match_expressions", []):
        key = requirement["key"]
        operator = requirement["operator"]
        values = set(requirement.get("values", []))
        present = key in labels
        actual = labels.get(key)

        if operator == "In" and (not present or actual not in values):
            return False
        if operator == "NotIn" and present and actual in values:
            return False
        if operator == "Exists" and not present:
            return False
        if operator == "DoesNotExist" and present:
            return False
    return True


def _resource_selector_matches(
    selector: dict[str, Any] | None, labels: dict[str, str]
) -> bool | None:
    # Prometheus Operator resource selector semantics: null selects none; empty selects all.
    if selector is None:
        return False
    return _selector_matches(selector, labels)


def _target_namespace_allows(
    selector: dict[str, Any], *, owner_namespace: str, candidate_namespace: str
) -> bool | None:
    if selector.get("valid") is False:
        return None
    mode = selector.get("mode")
    if mode == "ANY":
        return True
    if mode == "MATCH_NAMES":
        return candidate_namespace in selector.get("match_names", [])
    if mode == "SAME_NAMESPACE":
        return candidate_namespace == owner_namespace
    return None


def _classify_failure(stderr: str) -> tuple[str, str]:
    lowered = stderr.lower()
    if "forbidden" in lowered:
        return "KUBERNETES_FORBIDDEN", "Kubernetes API denied the observability configuration read."
    if (
        "the server doesn't have a resource type" in lowered
        or "could not find the requested resource" in lowered
        or "no matches for kind" in lowered
    ):
        return (
            "PROMETHEUS_OPERATOR_RESOURCE_UNAVAILABLE",
            "Prometheus Operator API resource is unavailable in this cluster.",
        )
    if "timeout" in lowered or "timed out" in lowered:
        return "KUBERNETES_TIMEOUT", "Kubernetes observability configuration read timed out."
    if "connection refused" in lowered or "unable to connect" in lowered:
        return "KUBERNETES_UNREACHABLE", "Kubernetes API could not be reached."
    return "KUBECTL_READ_FAILED", "kubectl could not complete the observability configuration read."


def _run_list(
    resource: str,
    *,
    all_namespaces: bool,
    kubectl_context: str | None,
    runner: Runner,
    timeout_seconds: int,
) -> tuple[list[dict[str, Any]] | None, dict[str, str] | None]:
    command = ["kubectl"]
    if kubectl_context:
        command += ["--context", kubectl_context]
    command += ["get", resource]
    if all_namespaces:
        command.append("--all-namespaces")
    command += ["--output", "json"]

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
            "code": "KUBECTL_TIMEOUT",
            "summary": "kubectl exceeded the local observability read timeout.",
        }
    except FileNotFoundError:
        return None, {
            "code": "KUBECTL_NOT_AVAILABLE",
            "summary": "kubectl is not available in the collector runtime.",
        }

    if result.returncode != 0:
        code, summary = _classify_failure(result.stderr)
        return None, {"code": code, "summary": summary}

    try:
        items = json.loads(result.stdout)["items"]
        if not isinstance(items, list):
            raise ValueError
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None, {
            "code": "KUBECTL_OUTPUT_INVALID",
            "summary": "Kubernetes observability configuration output could not be normalized safely.",
        }
    return items, None


def _observation_record(
    *,
    cluster_id: str,
    api_group: str,
    kind: str,
    item: dict[str, Any],
    now: datetime,
    ttl_seconds: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    metadata = item.get("metadata", {})
    namespace = metadata.get("namespace")
    name = metadata.get("name")
    return {
        "schema_version": "0.1",
        "evidence_id": _evidence_id(kind),
        "plane": "observed",
        "subject": _subject(
            cluster_id,
            api_group=api_group,
            kind=kind,
            namespace=namespace,
            name=name,
        ),
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": _rfc3339(now),
        "observed_at": _rfc3339(now),
        "expires_at": _rfc3339(now + timedelta(seconds=ttl_seconds)),
        "data": data,
        "provenance": {
            "source_type": "kubernetes_api",
            "source_id": cluster_id,
            "collector": "prometheus-operator-coverage-observer",
            "collector_version": COVERAGE_VERSION,
            "operation": f"LIST {kind}",
        },
        "errors": [],
    }


def _normalize_namespace_metadata(
    cluster_id: str, item: dict[str, Any], now: datetime, ttl_seconds: int
) -> dict[str, Any]:
    return _observation_record(
        cluster_id=cluster_id,
        api_group="",
        kind="Namespace",
        item=item,
        now=now,
        ttl_seconds=ttl_seconds,
        data={"labels": _metadata_labels(item)},
    )


def _normalize_service_metadata(
    cluster_id: str, item: dict[str, Any], now: datetime, ttl_seconds: int
) -> dict[str, Any]:
    return _observation_record(
        cluster_id=cluster_id,
        api_group="",
        kind="Service",
        item=item,
        now=now,
        ttl_seconds=ttl_seconds,
        data={"labels": _metadata_labels(item)},
    )


def _normalize_prometheus(
    cluster_id: str, item: dict[str, Any], now: datetime, ttl_seconds: int
) -> dict[str, Any]:
    spec = item.get("spec", {})
    return _observation_record(
        cluster_id=cluster_id,
        api_group="monitoring.coreos.com",
        kind="Prometheus",
        item=item,
        now=now,
        ttl_seconds=ttl_seconds,
        data={
            "labels": _metadata_labels(item),
            "paused": bool(spec.get("paused", False)),
            "service_monitor_selector": (
                _selector(spec.get("serviceMonitorSelector"))
                if "serviceMonitorSelector" in spec
                else None
            ),
            "service_monitor_namespace_selector": (
                _selector(spec.get("serviceMonitorNamespaceSelector"))
                if "serviceMonitorNamespaceSelector" in spec
                else None
            ),
            "pod_monitor_selector": (
                _selector(spec.get("podMonitorSelector"))
                if "podMonitorSelector" in spec
                else None
            ),
            "pod_monitor_namespace_selector": (
                _selector(spec.get("podMonitorNamespaceSelector"))
                if "podMonitorNamespaceSelector" in spec
                else None
            ),
        },
    )


def _endpoint_projection(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    result = []
    for endpoint in items:
        if not isinstance(endpoint, dict):
            continue
        projected = {
            field: endpoint[field]
            for field in ("port", "path", "scheme", "interval")
            if field in endpoint and isinstance(endpoint[field], (str, int, float, bool))
        }
        if projected:
            result.append(projected)
    return result


def _normalize_service_monitor(
    cluster_id: str, item: dict[str, Any], now: datetime, ttl_seconds: int
) -> dict[str, Any]:
    spec = item.get("spec", {})
    return _observation_record(
        cluster_id=cluster_id,
        api_group="monitoring.coreos.com",
        kind="ServiceMonitor",
        item=item,
        now=now,
        ttl_seconds=ttl_seconds,
        data={
            "labels": _metadata_labels(item),
            "selector": _selector(spec.get("selector"))
            or {"valid": True, "match_labels": {}, "match_expressions": []},
            "namespace_selector": _namespace_target_selector(spec.get("namespaceSelector")),
            "endpoints": _endpoint_projection(spec.get("endpoints", [])),
        },
    )


def _normalize_pod_monitor(
    cluster_id: str, item: dict[str, Any], now: datetime, ttl_seconds: int
) -> dict[str, Any]:
    spec = item.get("spec", {})
    return _observation_record(
        cluster_id=cluster_id,
        api_group="monitoring.coreos.com",
        kind="PodMonitor",
        item=item,
        now=now,
        ttl_seconds=ttl_seconds,
        data={
            "labels": _metadata_labels(item),
            "selector": _selector(spec.get("selector"))
            or {"valid": True, "match_labels": {}, "match_expressions": []},
            "namespace_selector": _namespace_target_selector(spec.get("namespaceSelector")),
            "pod_metrics_endpoints": _endpoint_projection(spec.get("podMetricsEndpoints", [])),
        },
    )


def _workload_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for envelope in snapshot.get("evidence", []):
        subject = envelope.get("subject", {})
        if subject.get("kind") not in WORKLOAD_KINDS:
            continue
        if envelope.get("plane") != "observed" or envelope.get("existence") != "PRESENT":
            continue
        if envelope.get("observation_status") != "COMPLETE":
            continue
        result[_label(subject)] = envelope
    return result


def _service_to_workloads(topology: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for relation in topology.get("relations", []):
        if relation.get("type") != "SERVICE_SELECTOR_MATCHES_WORKLOAD":
            continue
        result.setdefault(relation["source"], []).append(relation)
    return result


def _monitor_selection(
    prometheus_records: list[dict[str, Any]],
    monitor_records: list[dict[str, Any]],
    *,
    monitor_type: str,
    namespace_records: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {}
    unknowns: list[dict[str, Any]] = []

    selector_field = (
        "service_monitor_selector" if monitor_type == "ServiceMonitor" else "pod_monitor_selector"
    )
    namespace_selector_field = (
        "service_monitor_namespace_selector"
        if monitor_type == "ServiceMonitor"
        else "pod_monitor_namespace_selector"
    )

    for prometheus in prometheus_records:
        prometheus_label = _label(prometheus["subject"])
        prometheus_ns = prometheus["subject"].get("namespace") or ""
        resource_selector = prometheus["data"].get(selector_field)
        namespace_selector = prometheus["data"].get(namespace_selector_field)

        for monitor in monitor_records:
            monitor_label = _label(monitor["subject"])
            monitor_ns = monitor["subject"].get("namespace") or ""
            selection_evidence_ids = [prometheus["evidence_id"], monitor["evidence_id"]]

            if namespace_selector is None:
                namespace_allowed: bool | None = monitor_ns == prometheus_ns
            elif namespace_selector.get("valid") is False:
                namespace_allowed = None
            elif (
                not namespace_selector.get("match_labels")
                and not namespace_selector.get("match_expressions")
            ):
                namespace_allowed = True
            else:
                namespace_record = namespace_records.get(monitor_ns)
                if namespace_record is None:
                    namespace_allowed = None
                else:
                    namespace_allowed = _selector_matches(
                        namespace_selector,
                        namespace_record["data"].get("labels", {}),
                    )
                    selection_evidence_ids.append(namespace_record["evidence_id"])

            if namespace_allowed is None:
                unknowns.append(
                    {
                        "code": "PROMETHEUS_MONITOR_NAMESPACE_SELECTION_UNKNOWN",
                        "statement": (
                            f"Cannot evaluate whether {prometheus_label} selects namespace "
                            f"{monitor_ns} for {monitor_type} discovery."
                        ),
                        "evidence_ids": selection_evidence_ids,
                    }
                )
                continue
            if not namespace_allowed:
                continue

            selector_match = _resource_selector_matches(
                resource_selector,
                monitor["data"].get("labels", {}),
            )
            if selector_match is None:
                unknowns.append(
                    {
                        "code": "PROMETHEUS_MONITOR_SELECTOR_UNKNOWN",
                        "statement": (
                            f"Cannot evaluate {prometheus_label} selector against {monitor_label} "
                            "because the selector could not be normalized safely."
                        ),
                        "evidence_ids": selection_evidence_ids,
                    }
                )
                continue
            if not selector_match:
                continue

            selected.setdefault(monitor_label, []).append(
                {
                    "prometheus": prometheus,
                    "selection_evidence_ids": list(dict.fromkeys(selection_evidence_ids)),
                }
            )

    return selected, unknowns


def build_prometheus_operator_coverage(
    snapshot: dict[str, Any],
    topology: dict[str, Any],
    *,
    kubectl_context: str | None = None,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Derive Prometheus Operator configuration coverage without claiming live scrape health."""
    now = now or datetime.now(timezone.utc)
    cluster_id = snapshot["cluster_id"]
    if topology.get("cluster_id") != cluster_id:
        raise ValueError("observability coverage inputs must target the same cluster")

    query_specs = {
        "namespaces": ("namespaces", False),
        "services": ("services", True),
        "prometheuses": ("prometheuses.monitoring.coreos.com", True),
        "servicemonitors": ("servicemonitors.monitoring.coreos.com", True),
        "podmonitors": ("podmonitors.monitoring.coreos.com", True),
    }
    results: dict[str, list[dict[str, Any]] | None] = {}
    errors: list[dict[str, Any]] = []
    for key, (resource, all_namespaces) in query_specs.items():
        items, error = _run_list(
            resource,
            all_namespaces=all_namespaces,
            kubectl_context=kubectl_context,
            runner=runner,
            timeout_seconds=timeout_seconds,
        )
        results[key] = items
        if error:
            errors.append({"scope": key, **error})

    namespace_observations = [
        _normalize_namespace_metadata(cluster_id, item, now, ttl_seconds)
        for item in (results["namespaces"] or [])
        if item.get("metadata", {}).get("name")
    ]
    service_observations = [
        _normalize_service_metadata(cluster_id, item, now, ttl_seconds)
        for item in (results["services"] or [])
        if item.get("metadata", {}).get("name")
    ]
    prometheus_records = [
        _normalize_prometheus(cluster_id, item, now, ttl_seconds)
        for item in (results["prometheuses"] or [])
        if item.get("metadata", {}).get("name")
    ]
    service_monitor_records = [
        _normalize_service_monitor(cluster_id, item, now, ttl_seconds)
        for item in (results["servicemonitors"] or [])
        if item.get("metadata", {}).get("name")
    ]
    pod_monitor_records = [
        _normalize_pod_monitor(cluster_id, item, now, ttl_seconds)
        for item in (results["podmonitors"] or [])
        if item.get("metadata", {}).get("name")
    ]

    namespace_records = {
        item["subject"]["name"]: item for item in namespace_observations
    }
    service_records = {_label(item["subject"]): item for item in service_observations}

    selected_service_monitors, selection_unknowns_sm = _monitor_selection(
        prometheus_records,
        service_monitor_records,
        monitor_type="ServiceMonitor",
        namespace_records=namespace_records,
    )
    selected_pod_monitors, selection_unknowns_pm = _monitor_selection(
        prometheus_records,
        pod_monitor_records,
        monitor_type="PodMonitor",
        namespace_records=namespace_records,
    )

    workload_index = _workload_index(snapshot)
    service_to_workloads = _service_to_workloads(topology)
    service_paths_by_workload: dict[str, list[dict[str, Any]]] = {}
    pod_paths_by_workload: dict[str, list[dict[str, Any]]] = {}
    target_unknowns: list[dict[str, Any]] = []

    for monitor in service_monitor_records:
        monitor_label = _label(monitor["subject"])
        selected_by = selected_service_monitors.get(monitor_label, [])
        if not selected_by:
            continue
        monitor_ns = monitor["subject"].get("namespace") or ""
        selector = monitor["data"]["selector"]
        namespace_selector = monitor["data"]["namespace_selector"]

        for service_label, service in service_records.items():
            namespace_allowed = _target_namespace_allows(
                namespace_selector,
                owner_namespace=monitor_ns,
                candidate_namespace=service["subject"].get("namespace") or "",
            )
            if namespace_allowed is None:
                target_unknowns.append(
                    {
                        "code": "SERVICEMONITOR_TARGET_NAMESPACE_UNKNOWN",
                        "statement": f"Cannot evaluate target namespace selection for {monitor_label}.",
                        "evidence_ids": [monitor["evidence_id"], service["evidence_id"]],
                    }
                )
                continue
            if not namespace_allowed:
                continue

            service_match = _selector_matches(selector, service["data"].get("labels", {}))
            if service_match is None:
                target_unknowns.append(
                    {
                        "code": "SERVICEMONITOR_SERVICE_SELECTOR_UNKNOWN",
                        "statement": f"Cannot evaluate {monitor_label} selector against {service_label} safely.",
                        "evidence_ids": [monitor["evidence_id"], service["evidence_id"]],
                    }
                )
                continue
            if not service_match:
                continue

            for relation in service_to_workloads.get(service_label, []):
                workload_label = relation["target"]
                for selection in selected_by:
                    prometheus = selection["prometheus"]
                    evidence_ids = (
                        selection["selection_evidence_ids"]
                        + [service["evidence_id"]]
                        + relation.get("evidence_ids", [])
                    )
                    service_paths_by_workload.setdefault(workload_label, []).append(
                        {
                            "prometheus": _label(prometheus["subject"]),
                            "monitor": monitor_label,
                            "service": service_label,
                            "basis": [
                                "PROMETHEUS_MONITOR_SELECTION_INFERENCE",
                                "SERVICEMONITOR_SERVICE_SELECTOR_INFERENCE",
                                "SERVICE_SELECTOR_MATCH_INFERENCE",
                            ],
                            "evidence_ids": list(dict.fromkeys(evidence_ids)),
                        }
                    )

    for monitor in pod_monitor_records:
        monitor_label = _label(monitor["subject"])
        selected_by = selected_pod_monitors.get(monitor_label, [])
        if not selected_by:
            continue
        monitor_ns = monitor["subject"].get("namespace") or ""
        selector = monitor["data"]["selector"]
        namespace_selector = monitor["data"]["namespace_selector"]

        for workload_label, workload in workload_index.items():
            namespace_allowed = _target_namespace_allows(
                namespace_selector,
                owner_namespace=monitor_ns,
                candidate_namespace=workload["subject"].get("namespace") or "",
            )
            if namespace_allowed is None:
                target_unknowns.append(
                    {
                        "code": "PODMONITOR_TARGET_NAMESPACE_UNKNOWN",
                        "statement": f"Cannot evaluate target namespace selection for {monitor_label}.",
                        "evidence_ids": [monitor["evidence_id"], workload["evidence_id"]],
                    }
                )
                continue
            if not namespace_allowed:
                continue

            workload_match = _selector_matches(
                selector,
                workload.get("data", {}).get("pod_labels", {}),
            )
            if workload_match is None:
                target_unknowns.append(
                    {
                        "code": "PODMONITOR_TEMPLATE_SELECTOR_UNKNOWN",
                        "statement": f"Cannot evaluate {monitor_label} against {workload_label} safely.",
                        "evidence_ids": [monitor["evidence_id"], workload["evidence_id"]],
                    }
                )
                continue
            if not workload_match:
                continue

            for selection in selected_by:
                prometheus = selection["prometheus"]
                evidence_ids = selection["selection_evidence_ids"] + [workload["evidence_id"]]
                pod_paths_by_workload.setdefault(workload_label, []).append(
                    {
                        "prometheus": _label(prometheus["subject"]),
                        "monitor": monitor_label,
                        "basis": [
                            "PROMETHEUS_MONITOR_SELECTION_INFERENCE",
                            "PODMONITOR_TEMPLATE_LABEL_INFERENCE",
                        ],
                        "evidence_ids": list(dict.fromkeys(evidence_ids)),
                    }
                )

    unknowns = selection_unknowns_sm + selection_unknowns_pm + target_unknowns
    for error in errors:
        unknowns.append(
            {
                "code": error["code"],
                "statement": (
                    f"Observability configuration scope {error['scope']} could not be observed: "
                    f"{error['summary']}"
                ),
                "evidence_ids": [],
            }
        )

    critical_error_scopes = {error["scope"] for error in errors}
    workload_coverage = []
    for workload_label, workload in sorted(workload_index.items()):
        service_paths = service_paths_by_workload.get(workload_label, [])
        pod_paths = pod_paths_by_workload.get(workload_label, [])
        if service_paths or pod_paths:
            status = "OPERATOR_MONITOR_MATCH"
        elif critical_error_scopes & {
            "prometheuses",
            "servicemonitors",
            "podmonitors",
            "services",
            "namespaces",
        }:
            status = "UNKNOWN"
        elif unknowns:
            status = "UNKNOWN"
        else:
            status = "NO_OPERATOR_MONITOR_MATCH"

        evidence_ids = [workload["evidence_id"]]
        for path in service_paths + pod_paths:
            evidence_ids.extend(path["evidence_ids"])
        workload_coverage.append(
            {
                "subject": workload_label,
                "status": status,
                "scope_completeness": "PARTIAL" if errors or unknowns else "COMPLETE",
                "service_monitor_paths": service_paths,
                "pod_monitor_paths": pod_paths,
                "evidence_ids": list(dict.fromkeys(evidence_ids)),
                "caveats": [
                    "Prometheus Operator configuration matches do not prove current scrape target health or metric ingestion.",
                    "ServiceMonitor workload attribution composes ServiceMonitor-to-Service selection with selector-based Service-to-controller inference.",
                    "PodMonitor workload attribution uses controller pod-template labels and does not prove current live Pod target membership.",
                    "No operator monitor match does not rule out other Prometheus, static scrape, OpenTelemetry, or external monitoring paths.",
                ],
            }
        )

    counts = Counter(item["status"] for item in workload_coverage)
    monitoring_scopes = {"prometheuses", "servicemonitors", "podmonitors"}
    failed_monitoring_scopes = monitoring_scopes & critical_error_scopes
    if failed_monitoring_scopes == monitoring_scopes:
        source_status = "FAILED_TO_OBSERVE"
    elif errors or unknowns:
        source_status = "PARTIAL"
    else:
        source_status = "COMPLETE"

    source_observations = (
        namespace_observations
        + service_observations
        + prometheus_records
        + service_monitor_records
        + pod_monitor_records
    )
    return {
        "observability_coverage_version": COVERAGE_VERSION,
        "cluster_id": cluster_id,
        "generated_at": _rfc3339(now),
        "mutation_allowed": False,
        "source_status": source_status,
        "summary": {
            "prometheus_instances": len(prometheus_records),
            "service_monitors": len(service_monitor_records),
            "pod_monitors": len(pod_monitor_records),
            "selected_service_monitors": len(selected_service_monitors),
            "selected_pod_monitors": len(selected_pod_monitors),
            "workloads_total": len(workload_coverage),
            "workloads_with_operator_monitor_match": counts["OPERATOR_MONITOR_MATCH"],
            "workloads_without_operator_monitor_match": counts["NO_OPERATOR_MONITOR_MATCH"],
            "workloads_observability_unknown": counts["UNKNOWN"],
        },
        "source_observations": source_observations,
        "workload_coverage": workload_coverage,
        "unknowns": unknowns,
        "errors": errors,
    }


def attach_observability_coverage(
    inventory: dict[str, Any], coverage: dict[str, Any]
) -> dict[str, Any]:
    if inventory.get("cluster_id") != coverage.get("cluster_id"):
        raise ValueError("inventory and observability coverage must target the same cluster")

    result = copy.deepcopy(inventory)
    result["inventory_version"] = "0.2"
    coverage_index = {
        item["subject"]: item for item in coverage.get("workload_coverage", [])
    }

    for entity in result.get("entities", []):
        workload_label = _label(entity["subject"])
        entity["observability"] = coverage_index.get(
            workload_label,
            {
                "subject": workload_label,
                "status": "UNKNOWN",
                "scope_completeness": "PARTIAL",
                "service_monitor_paths": [],
                "pod_monitor_paths": [],
                "evidence_ids": [],
                "caveats": [
                    "No observability coverage record was produced for this workload."
                ],
            },
        )
        entity["evidence_ids"] = list(
            dict.fromkeys(
                entity.get("evidence_ids", [])
                + entity["observability"].get("evidence_ids", [])
            )
        )

    result["summary"].update(
        {
            "prometheus_instances": coverage["summary"]["prometheus_instances"],
            "service_monitors": coverage["summary"]["service_monitors"],
            "pod_monitors": coverage["summary"]["pod_monitors"],
            "workloads_with_operator_monitor_match": coverage["summary"][
                "workloads_with_operator_monitor_match"
            ],
            "workloads_without_operator_monitor_match": coverage["summary"][
                "workloads_without_operator_monitor_match"
            ],
            "workloads_observability_unknown": coverage["summary"][
                "workloads_observability_unknown"
            ],
        }
    )
    result["observability_source_status"] = coverage["source_status"]
    return result


def render_observability_coverage_markdown(coverage: dict[str, Any]) -> str:
    summary = coverage["summary"]
    lines = [
        "# Prometheus Operator Coverage",
        "",
        f"Cluster: `{coverage['cluster_id']}`",
        f"Generated: `{coverage['generated_at']}`",
        f"Source status: `{coverage['source_status']}`",
        "Mutation allowed: `false`",
        "",
        "## Configuration coverage",
        "",
        f"- Prometheus instances: {summary['prometheus_instances']}",
        f"- ServiceMonitors: {summary['service_monitors']}",
        f"- PodMonitors: {summary['pod_monitors']}",
        f"- Selected ServiceMonitors: {summary['selected_service_monitors']}",
        f"- Selected PodMonitors: {summary['selected_pod_monitors']}",
        f"- Workloads with operator monitor match: {summary['workloads_with_operator_monitor_match']}",
        f"- Workloads without operator monitor match: {summary['workloads_without_operator_monitor_match']}",
        f"- Workloads with unknown observability coverage: {summary['workloads_observability_unknown']}",
        "",
        "## Unknown or failed observation",
        "",
    ]
    if coverage["unknowns"]:
        for item in coverage["unknowns"]:
            lines.append(f"- [{item['code']}] {item['statement']}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "This artifact describes Prometheus Operator configuration coverage only. It does not prove that any target is currently up, scraped successfully, or producing expected metrics.",
            "ServiceMonitor-to-workload coverage includes selector-based inference through Services; PodMonitor coverage uses controller pod-template labels rather than live Pod membership.",
            "",
        ]
    )
    return "\n".join(lines)


def render_inventory_observability_markdown(
    inventory_markdown: str, coverage: dict[str, Any]
) -> str:
    summary = coverage["summary"]
    extra = [
        "",
        "## Prometheus Operator coverage",
        "",
        f"- Source status: `{coverage['source_status']}`",
        f"- Prometheus instances: {summary['prometheus_instances']}",
        f"- ServiceMonitors / PodMonitors: {summary['service_monitors']} / {summary['pod_monitors']}",
        f"- Workloads with operator monitor match: {summary['workloads_with_operator_monitor_match']}",
        f"- Workloads without operator monitor match: {summary['workloads_without_operator_monitor_match']}",
        f"- Workloads with unknown coverage: {summary['workloads_observability_unknown']}",
        "",
        "Configuration match is not scrape-health proof; live Prometheus target and metric verification remains outside this Milestone 3 projection.",
        "",
    ]
    return inventory_markdown.rstrip() + "\n" + "\n".join(extra)
