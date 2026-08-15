from __future__ import annotations

import argparse
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from .io_utils import atomic_write_json, atomic_write_text

ROUTING_OWNERSHIP_VERSION = "0.1"
COLLECTOR_VERSION = "0.1.0"
DEFAULT_TTL_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_POD_GETS = 500
DEFAULT_MAX_REPLICASET_GETS = 250
Runner = Callable[..., subprocess.CompletedProcess[str]]
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet"}

ENDPOINTSLICE_JSONPATH = (
    r'{range .items[*]}'
    r'{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}'
    r'{.metadata.labels.kubernetes\.io/service-name}{"\t"}'
    r'{range .endpoints[*]}'
    r'{.targetRef.apiVersion}{"|"}{.targetRef.kind}{"|"}'
    r'{.targetRef.namespace}{"|"}{.targetRef.name}{"|"}'
    r'{.conditions.ready}{"|"}{.conditions.serving}{"|"}'
    r'{.conditions.terminating}{";"}'
    r'{end}{"\n"}{end}'
)
OWNER_JSONPATH = (
    r'{range .metadata.ownerReferences[?(@.controller==true)]}'
    r'{.apiVersion}{"|"}{.kind}{"|"}{.name}{";"}{end}'
)


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _api_group(api_version: str | None) -> str:
    if not api_version:
        return ""
    return api_version.split("/", 1)[0] if "/" in api_version else ""


def _label(kind: str, namespace: str | None, name: str) -> str:
    return f"{kind}/{namespace}/{name}" if namespace else f"{kind}/{name}"


def _bool_or_none(value: str) -> bool | None:
    value = value.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def _parse_owner_projection(value: str) -> list[dict[str, str]] | None:
    owners: list[dict[str, str]] = []
    if not value.strip():
        return owners
    for raw in value.split(";"):
        if not raw:
            continue
        parts = raw.split("|")
        if len(parts) != 3 or not parts[1] or not parts[2]:
            return None
        owners.append(
            {
                "api_group": _api_group(parts[0]),
                "kind": parts[1],
                "name": parts[2],
            }
        )
    return owners


def _parse_endpointslice_projection(value: str) -> tuple[list[dict[str, Any]], int]:
    slices: list[dict[str, Any]] = []
    invalid = 0
    for raw_line in value.splitlines():
        if not raw_line.strip():
            continue
        parts = raw_line.split("\t", 3)
        if len(parts) < 3:
            invalid += 1
            continue
        namespace, name, service_name = parts[:3]
        endpoints_raw = parts[3] if len(parts) == 4 else ""
        if not namespace or not name:
            invalid += 1
            continue
        endpoints: list[dict[str, Any]] = []
        for raw_endpoint in endpoints_raw.split(";"):
            if raw_endpoint == "":
                continue
            fields = raw_endpoint.split("|")
            if len(fields) != 7:
                invalid += 1
                continue
            api_version, kind, target_namespace, target_name, ready, serving, terminating = fields
            target_ref = None
            if kind and target_name:
                target_ref = {
                    "api_group": _api_group(api_version),
                    "kind": kind,
                    "namespace": target_namespace or namespace,
                    "name": target_name,
                }
            endpoints.append(
                {
                    "target_ref": target_ref,
                    "conditions": {
                        "ready": _bool_or_none(ready),
                        "serving": _bool_or_none(serving),
                        "terminating": _bool_or_none(terminating),
                    },
                }
            )
        slices.append(
            {
                "evidence_id": f"ev-{uuid.uuid4()}",
                "namespace": namespace,
                "name": name,
                "service_name": service_name or None,
                "endpoints": endpoints,
            }
        )
    return slices, invalid


def _classify_failure(stderr: str) -> tuple[str, str]:
    lowered = stderr.lower()
    if "notfound" in lowered or "not found" in lowered:
        return "KUBERNETES_NOT_FOUND", "Referenced Kubernetes object was not found by exact-name GET."
    if "forbidden" in lowered:
        return "KUBERNETES_FORBIDDEN", "Kubernetes API denied the routing ownership read request."
    if "timeout" in lowered or "timed out" in lowered:
        return "KUBERNETES_TIMEOUT", "Kubernetes routing ownership read request timed out."
    if "connection refused" in lowered or "unable to connect" in lowered:
        return "KUBERNETES_UNREACHABLE", "Kubernetes API could not be reached."
    return "KUBECTL_READ_FAILED", "kubectl could not complete the routing ownership read request."


def _kubectl_prefix(kubectl_context: str | None) -> list[str]:
    command = ["kubectl"]
    if kubectl_context:
        command += ["--context", kubectl_context]
    return command


def _collect_endpointslices(
    *,
    runner: Runner,
    kubectl_context: str | None,
    now: datetime,
    ttl_seconds: int,
    timeout_seconds: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    evidence_id = f"ev-{uuid.uuid4()}"
    command = _kubectl_prefix(kubectl_context) + [
        "get",
        "endpointslices.discovery.k8s.io",
        "--all-namespaces",
        "--output",
        f"jsonpath={ENDPOINTSLICE_JSONPATH}",
    ]
    try:
        result = runner(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
    except subprocess.TimeoutExpired:
        return (
            {"status": "FAILED_TO_OBSERVE", "mode": "LIST_PROJECTED", "observed_at": None, "expires_at": None, "item_count": None, "evidence_id": evidence_id},
            [],
            [{"source": "endpoint_slices", "code": "KUBECTL_TIMEOUT", "summary": "kubectl exceeded the local EndpointSlice timeout."}],
        )
    except FileNotFoundError:
        return (
            {"status": "FAILED_TO_OBSERVE", "mode": "LIST_PROJECTED", "observed_at": None, "expires_at": None, "item_count": None, "evidence_id": evidence_id},
            [],
            [{"source": "endpoint_slices", "code": "KUBECTL_NOT_AVAILABLE", "summary": "kubectl is not available in the collector runtime."}],
        )
    if result.returncode != 0:
        code, summary = _classify_failure(result.stderr)
        return (
            {"status": "FAILED_TO_OBSERVE", "mode": "LIST_PROJECTED", "observed_at": None, "expires_at": None, "item_count": None, "evidence_id": evidence_id},
            [],
            [{"source": "endpoint_slices", "code": code, "summary": summary}],
        )

    slices, invalid = _parse_endpointslice_projection(result.stdout)
    status = "PARTIAL" if invalid else "COMPLETE"
    source_status = {
        "status": status,
        "mode": "LIST_PROJECTED",
        "observed_at": _rfc3339(now),
        "expires_at": _rfc3339(now + timedelta(seconds=ttl_seconds)),
        "item_count": len(slices),
        "evidence_id": evidence_id,
    }
    errors = []
    if invalid:
        errors.append(
            {
                "source": "endpoint_slices",
                "code": "ENDPOINTSLICE_PROJECTION_PARTIAL",
                "summary": f"{invalid} projected EndpointSlice or endpoint records could not be parsed safely.",
            }
        )
    return source_status, slices, errors


def _get_owner_projection(
    *,
    resource: str,
    namespace: str,
    name: str,
    runner: Runner,
    kubectl_context: str | None,
    timeout_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    evidence_id = f"ev-{uuid.uuid4()}"
    command = _kubectl_prefix(kubectl_context) + [
        "get",
        resource,
        name,
        "--namespace",
        namespace,
        "--output",
        f"jsonpath={OWNER_JSONPATH}",
    ]
    try:
        result = runner(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
    except subprocess.TimeoutExpired:
        return {"state": "UNKNOWN", "evidence_id": evidence_id, "controller_owners": []}, {"code": "KUBECTL_TIMEOUT", "summary": "Exact-name Kubernetes metadata GET timed out."}
    except FileNotFoundError:
        return {"state": "UNKNOWN", "evidence_id": evidence_id, "controller_owners": []}, {"code": "KUBECTL_NOT_AVAILABLE", "summary": "kubectl is not available in the collector runtime."}

    if result.returncode != 0:
        code, summary = _classify_failure(result.stderr)
        if code == "KUBERNETES_NOT_FOUND":
            return {"state": "ABSENT", "evidence_id": evidence_id, "controller_owners": []}, None
        return {"state": "UNKNOWN", "evidence_id": evidence_id, "controller_owners": []}, {"code": code, "summary": summary}

    owners = _parse_owner_projection(result.stdout)
    if owners is None:
        return {"state": "UNKNOWN", "evidence_id": evidence_id, "controller_owners": []}, {"code": "OWNER_PROJECTION_INVALID", "summary": "Controller ownerReference projection could not be parsed safely."}
    return {"state": "PRESENT", "evidence_id": evidence_id, "controller_owners": owners}, None


def _status_for_selective_get(*, requested: int, present: int, absent: int, unknown: int, skipped: int, now: datetime, ttl_seconds: int) -> dict[str, Any]:
    if unknown or skipped:
        status = "FAILED_TO_OBSERVE" if requested > 0 and unknown + skipped == requested else "PARTIAL"
    else:
        status = "COMPLETE"
    return {
        "status": status,
        "mode": "SELECTIVE_GET_PROJECTED",
        "observed_at": _rfc3339(now),
        "expires_at": _rfc3339(now + timedelta(seconds=ttl_seconds)),
        "requested": requested,
        "present": present,
        "absent": absent,
        "unknown": unknown,
        "skipped_by_bound": skipped,
    }


def _snapshot_indexes(snapshot: dict[str, Any]) -> tuple[dict[tuple[str, str | None, str], dict[str, Any]], dict[str, dict[str, Any]]]:
    resources: dict[tuple[str, str | None, str], dict[str, Any]] = {}
    collections: dict[str, dict[str, Any]] = {}
    for envelope in snapshot.get("evidence", []):
        subject = envelope.get("subject", {})
        kind = subject.get("kind")
        if not isinstance(kind, str):
            continue
        if kind.endswith("Collection"):
            collections[kind.removesuffix("Collection")] = envelope
            continue
        if envelope.get("observation_status") != "COMPLETE":
            continue
        resources[(kind, subject.get("namespace"), subject.get("name"))] = envelope
    return resources, collections


def _collection_complete(collections: dict[str, dict[str, Any]], kind: str) -> bool:
    envelope = collections.get(kind)
    return bool(envelope and envelope.get("observation_status") == "COMPLETE")


def _resolve_workload(
    *,
    namespace: str,
    owner: dict[str, str],
    pod_record: dict[str, Any],
    replica_sets: dict[tuple[str, str], dict[str, Any]],
    skipped_replica_sets: set[tuple[str, str]],
    resources: dict[tuple[str, str | None, str], dict[str, Any]],
    collections: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    basis = ["POD_CONTROLLER_OWNER_REFERENCE"]
    evidence_ids = [pod_record["evidence_id"]]
    immediate_owner = {
        "api_group": owner.get("api_group", ""),
        "kind": owner["kind"],
        "namespace": namespace,
        "name": owner["name"],
    }
    owner_kind = owner["kind"]
    owner_name = owner["name"]

    if owner_kind == "ReplicaSet":
        key = (namespace, owner_name)
        if key in skipped_replica_sets:
            return {"resolution": "REPLICASET_GET_BOUND_EXCEEDED", "immediate_owner": immediate_owner, "workload": None, "basis": basis, "evidence_ids": evidence_ids}
        replica_set = replica_sets.get(key)
        if replica_set is None or replica_set["state"] == "UNKNOWN":
            if replica_set is not None:
                evidence_ids.append(replica_set["evidence_id"])
            return {"resolution": "REPLICASET_OBSERVATION_UNKNOWN", "immediate_owner": immediate_owner, "workload": None, "basis": basis, "evidence_ids": evidence_ids}
        if replica_set["state"] == "ABSENT":
            evidence_ids.append(replica_set["evidence_id"])
            return {"resolution": "REPLICASET_NOT_FOUND", "immediate_owner": immediate_owner, "workload": None, "basis": basis, "evidence_ids": evidence_ids}
        evidence_ids.append(replica_set["evidence_id"])
        rs_owners = replica_set.get("controller_owners", [])
        if len(rs_owners) != 1:
            return {
                "resolution": "REPLICASET_CONTROLLER_OWNER_AMBIGUOUS" if len(rs_owners) > 1 else "REPLICASET_CONTROLLER_OWNER_UNKNOWN",
                "immediate_owner": immediate_owner,
                "workload": None,
                "basis": basis + ["REPLICASET_EXACT_GET"],
                "evidence_ids": evidence_ids,
            }
        rs_owner = rs_owners[0]
        if rs_owner["kind"] != "Deployment":
            return {"resolution": "UNSUPPORTED_REPLICASET_CONTROLLER_KIND", "immediate_owner": immediate_owner, "workload": None, "basis": basis + ["REPLICASET_CONTROLLER_OWNER_REFERENCE"], "evidence_ids": evidence_ids}
        owner_kind = "Deployment"
        owner_name = rs_owner["name"]
        basis.append("REPLICASET_CONTROLLER_OWNER_REFERENCE")
    elif owner_kind not in WORKLOAD_KINDS:
        return {"resolution": "UNSUPPORTED_POD_CONTROLLER_KIND", "immediate_owner": immediate_owner, "workload": None, "basis": basis, "evidence_ids": evidence_ids}

    workload_subject = _label(owner_kind, namespace, owner_name)
    workload = resources.get((owner_kind, namespace, owner_name))
    if workload is not None:
        evidence_ids.append(workload["evidence_id"])
        return {
            "resolution": "RESOLVED_WORKLOAD",
            "immediate_owner": immediate_owner,
            "workload": workload_subject,
            "basis": basis + ["CURRENT_WORKLOAD_OBSERVATION"],
            "evidence_ids": list(dict.fromkeys(evidence_ids)),
        }
    return {
        "resolution": "WORKLOAD_NOT_OBSERVED" if _collection_complete(collections, owner_kind) else "WORKLOAD_OBSERVATION_UNKNOWN",
        "immediate_owner": immediate_owner,
        "workload": workload_subject,
        "basis": basis,
        "evidence_ids": list(dict.fromkeys(evidence_ids)),
    }


def _overall_status(values: list[str]) -> str:
    if all(value == "COMPLETE" for value in values):
        return "COMPLETE"
    if values and all(value == "FAILED_TO_OBSERVE" for value in values):
        return "FAILED_TO_OBSERVE"
    return "PARTIAL"


def build_routing_ownership(
    snapshot: dict[str, Any],
    *,
    runner: Runner = subprocess.run,
    kubectl_context: str | None = None,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    max_pod_gets: int = DEFAULT_MAX_POD_GETS,
    max_replicaset_gets: int = DEFAULT_MAX_REPLICASET_GETS,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if max_pod_gets < 1 or max_replicaset_gets < 1:
        raise ValueError("selective GET bounds must be positive")

    endpoint_status, endpoint_slices, errors = _collect_endpointslices(
        runner=runner,
        kubectl_context=kubectl_context,
        now=now,
        ttl_seconds=ttl_seconds,
        timeout_seconds=timeout_seconds,
    )
    resources, collections = _snapshot_indexes(snapshot)

    pod_targets = sorted(
        {
            (endpoint["target_ref"]["namespace"], endpoint["target_ref"]["name"])
            for endpoint_slice in endpoint_slices
            for endpoint in endpoint_slice["endpoints"]
            if endpoint.get("target_ref") and endpoint["target_ref"]["kind"] == "Pod"
        }
    )
    selected_pods = pod_targets[:max_pod_gets]
    skipped_pods = set(pod_targets[max_pod_gets:])
    pod_records: dict[tuple[str, str], dict[str, Any]] = {}
    for namespace, name in selected_pods:
        record, error = _get_owner_projection(
            resource="pod",
            namespace=namespace,
            name=name,
            runner=runner,
            kubectl_context=kubectl_context,
            timeout_seconds=timeout_seconds,
        )
        pod_records[(namespace, name)] = record
        if error:
            errors.append({"source": "pods", "subject": _label("Pod", namespace, name), **error})

    rs_targets = sorted(
        {
            (namespace, owner["name"])
            for (namespace, _name), pod in pod_records.items()
            if pod["state"] == "PRESENT"
            for owner in pod.get("controller_owners", [])
            if owner["kind"] == "ReplicaSet"
        }
    )
    selected_rs = rs_targets[:max_replicaset_gets]
    skipped_rs = set(rs_targets[max_replicaset_gets:])
    rs_records: dict[tuple[str, str], dict[str, Any]] = {}
    for namespace, name in selected_rs:
        record, error = _get_owner_projection(
            resource="replicaset.apps",
            namespace=namespace,
            name=name,
            runner=runner,
            kubectl_context=kubectl_context,
            timeout_seconds=timeout_seconds,
        )
        rs_records[(namespace, name)] = record
        if error:
            errors.append({"source": "replica_sets", "subject": _label("ReplicaSet", namespace, name), **error})

    def _counts(records: dict[tuple[str, str], dict[str, Any]]) -> tuple[int, int, int]:
        return (
            sum(record["state"] == "PRESENT" for record in records.values()),
            sum(record["state"] == "ABSENT" for record in records.values()),
            sum(record["state"] == "UNKNOWN" for record in records.values()),
        )

    pod_present, pod_absent, pod_unknown = _counts(pod_records)
    rs_present, rs_absent, rs_unknown = _counts(rs_records)
    pod_status = _status_for_selective_get(
        requested=len(pod_targets), present=pod_present, absent=pod_absent,
        unknown=pod_unknown, skipped=len(skipped_pods), now=now, ttl_seconds=ttl_seconds,
    )
    rs_status = _status_for_selective_get(
        requested=len(rs_targets), present=rs_present, absent=rs_absent,
        unknown=rs_unknown, skipped=len(skipped_rs), now=now, ttl_seconds=ttl_seconds,
    )

    service_routes: dict[tuple[str, str], dict[str, Any]] = {}
    unknowns: list[dict[str, Any]] = []
    for endpoint_slice in endpoint_slices:
        namespace = endpoint_slice["namespace"]
        slice_name = endpoint_slice["name"]
        service_name = endpoint_slice.get("service_name")
        if not service_name:
            unknowns.append(
                {
                    "code": "ENDPOINTSLICE_SERVICE_LABEL_MISSING",
                    "subject": _label("EndpointSlice", namespace, slice_name),
                    "statement": "EndpointSlice has no kubernetes.io/service-name label, so Service association is unknown.",
                    "evidence_ids": [endpoint_slice["evidence_id"]],
                }
            )
            continue
        key = (namespace, service_name)
        service_subject = _label("Service", namespace, service_name)
        route = service_routes.setdefault(
            key,
            {
                "service": service_subject,
                "service_observation": "UNKNOWN",
                "endpoint_slices": [],
                "paths": [],
                "resolved_workloads": [],
                "scope_completeness": "COMPLETE" if endpoint_status["status"] == "COMPLETE" else "PARTIAL",
            },
        )
        route["endpoint_slices"].append(_label("EndpointSlice", namespace, slice_name))
        service = resources.get(("Service", namespace, service_name))
        service_evidence_id = None
        if service is not None:
            route["service_observation"] = "PRESENT"
            service_evidence_id = service["evidence_id"]
        elif _collection_complete(collections, "Service"):
            route["service_observation"] = "ABSENT_FROM_COMPLETE_OBSERVATION"
        else:
            route["service_observation"] = "UNKNOWN"
            route["scope_completeness"] = "PARTIAL"

        for endpoint in endpoint_slice["endpoints"]:
            target = endpoint.get("target_ref")
            evidence_ids = [endpoint_slice["evidence_id"]]
            if service_evidence_id:
                evidence_ids.append(service_evidence_id)
            path: dict[str, Any] = {
                "endpoint_slice": _label("EndpointSlice", namespace, slice_name),
                "target": target,
                "conditions": endpoint["conditions"],
                "resolution": "UNKNOWN",
                "immediate_owner": None,
                "workload": None,
                "basis": ["ENDPOINTSLICE_SERVICE_NAME_LABEL"],
                "evidence_ids": evidence_ids,
            }
            if target is None:
                path["resolution"] = "TARGET_REF_MISSING"
                route["paths"].append(path)
                continue
            path["basis"].append("ENDPOINT_TARGET_REF")
            if target["kind"] != "Pod":
                path["resolution"] = "NON_POD_TARGET"
                route["paths"].append(path)
                continue

            pod_key = (target["namespace"], target["name"])
            if pod_key in skipped_pods:
                path["resolution"] = "POD_GET_BOUND_EXCEEDED"
                route["scope_completeness"] = "PARTIAL"
                route["paths"].append(path)
                continue
            pod = pod_records.get(pod_key)
            if pod is None or pod["state"] == "UNKNOWN":
                if pod is not None:
                    path["evidence_ids"].append(pod["evidence_id"])
                path["resolution"] = "POD_OBSERVATION_UNKNOWN"
                route["scope_completeness"] = "PARTIAL"
                route["paths"].append(path)
                continue
            path["evidence_ids"].append(pod["evidence_id"])
            if pod["state"] == "ABSENT":
                path["resolution"] = "POD_NOT_FOUND"
                route["paths"].append(path)
                continue
            owners = pod.get("controller_owners", [])
            if len(owners) != 1:
                path["resolution"] = "POD_CONTROLLER_OWNER_AMBIGUOUS" if len(owners) > 1 else "POD_CONTROLLER_OWNER_UNKNOWN"
                route["paths"].append(path)
                continue
            resolved = _resolve_workload(
                namespace=target["namespace"], owner=owners[0], pod_record=pod,
                replica_sets=rs_records, skipped_replica_sets=skipped_rs,
                resources=resources, collections=collections,
            )
            path.update(resolved)
            path["basis"] = ["ENDPOINTSLICE_SERVICE_NAME_LABEL", "ENDPOINT_TARGET_REF"] + resolved["basis"]
            path["evidence_ids"] = list(dict.fromkeys(evidence_ids + resolved["evidence_ids"]))
            if path["resolution"] in {"REPLICASET_GET_BOUND_EXCEEDED", "REPLICASET_OBSERVATION_UNKNOWN", "WORKLOAD_OBSERVATION_UNKNOWN"}:
                route["scope_completeness"] = "PARTIAL"
            route["paths"].append(path)

    routes: list[dict[str, Any]] = []
    for route in service_routes.values():
        groups: dict[str, dict[str, Any]] = {}
        for path in route["paths"]:
            if path["resolution"] != "RESOLVED_WORKLOAD" or not path.get("workload"):
                continue
            group = groups.setdefault(
                path["workload"],
                {"subject": path["workload"], "pod_targets": 0, "basis": [], "evidence_ids": []},
            )
            group["pod_targets"] += 1
            group["basis"].extend(path["basis"])
            group["evidence_ids"].extend(path["evidence_ids"])
        for group in groups.values():
            group["basis"] = list(dict.fromkeys(group["basis"]))
            group["evidence_ids"] = list(dict.fromkeys(group["evidence_ids"]))
        route["resolved_workloads"] = sorted(groups.values(), key=lambda item: item["subject"])

        resolutions = [path["resolution"] for path in route["paths"]]
        resolved_count = sum(value == "RESOLVED_WORKLOAD" for value in resolutions)
        non_pod_count = sum(value == "NON_POD_TARGET" for value in resolutions)
        if route["service_observation"] == "ABSENT_FROM_COMPLETE_OBSERVATION":
            route["state"] = "SERVICE_NOT_OBSERVED"
        elif route["service_observation"] == "UNKNOWN":
            route["state"] = "UNKNOWN"
        elif not resolutions:
            route["state"] = "NO_ENDPOINTS_OBSERVED"
        elif resolved_count == len(resolutions):
            route["state"] = "RESOLVED_WORKLOAD_ROUTING"
        elif resolved_count:
            route["state"] = "PARTIAL_ROUTING"
        elif non_pod_count == len(resolutions):
            route["state"] = "NON_POD_ROUTING"
        else:
            route["state"] = "UNKNOWN"
        routes.append(route)

    all_paths = [path for route in routes for path in route["paths"]]
    summary = {
        "endpoint_slices": len(endpoint_slices),
        "pod_gets_requested": len(pod_targets),
        "pod_gets_executed": len(selected_pods),
        "replicaset_gets_requested": len(rs_targets),
        "replicaset_gets_executed": len(selected_rs),
        "services_with_endpoint_slices": len(routes),
        "endpoint_paths": len(all_paths),
        "pod_targets": sum((path.get("target") or {}).get("kind") == "Pod" for path in all_paths),
        "non_pod_targets": sum(path["resolution"] == "NON_POD_TARGET" for path in all_paths),
        "target_refs_missing": sum(path["resolution"] == "TARGET_REF_MISSING" for path in all_paths),
        "resolved_workload_paths": sum(path["resolution"] == "RESOLVED_WORKLOAD" for path in all_paths),
        "services_with_resolved_workloads": sum(bool(route["resolved_workloads"]) for route in routes),
        "services_non_pod_only": sum(route["state"] == "NON_POD_ROUTING" for route in routes),
        "services_unknown_or_partial": sum(route["state"] in {"UNKNOWN", "PARTIAL_ROUTING", "SERVICE_NOT_OBSERVED"} or route["scope_completeness"] == "PARTIAL" for route in routes),
    }

    overall = _overall_status([endpoint_status["status"], pod_status["status"], rs_status["status"]])
    if any(route["scope_completeness"] == "PARTIAL" for route in routes) and overall == "COMPLETE":
        overall = "PARTIAL"
    return {
        "routing_ownership_version": ROUTING_OWNERSHIP_VERSION,
        "cluster_id": snapshot["cluster_id"],
        "generated_at": _rfc3339(now),
        "mutation_allowed": False,
        "source_status": {
            "overall": overall,
            "endpoint_slices": endpoint_status,
            "pods": pod_status,
            "replica_sets": rs_status,
        },
        "bounds": {"max_pod_gets": max_pod_gets, "max_replicaset_gets": max_replicaset_gets},
        "summary": summary,
        "service_routes": sorted(routes, key=lambda route: route["service"]),
        "unknowns": unknowns,
        "errors": errors,
    }


def render_routing_ownership_markdown(value: dict[str, Any]) -> str:
    s = value["summary"]
    lines = [
        "# Kubernetes Endpoint Routing and Ownership",
        "",
        f"Cluster: `{value['cluster_id']}`",
        f"Generated: `{value['generated_at']}`",
        "Mutation allowed: `false`",
        f"Source status: `{value['source_status']['overall']}`",
        "",
        "## Summary",
        "",
        f"- EndpointSlices: {s['endpoint_slices']}",
        f"- Pod exact GETs: {s['pod_gets_executed']} / requested {s['pod_gets_requested']}",
        f"- ReplicaSet exact GETs: {s['replicaset_gets_executed']} / requested {s['replicaset_gets_requested']}",
        f"- Services with EndpointSlices: {s['services_with_endpoint_slices']}",
        f"- Endpoint paths: {s['endpoint_paths']}",
        f"- Pod targets: {s['pod_targets']}",
        f"- Non-Pod targets: {s['non_pod_targets']}",
        f"- Resolved workload paths: {s['resolved_workload_paths']}",
        f"- Services with resolved workloads: {s['services_with_resolved_workloads']}",
        "",
        "## Service routing",
        "",
    ]
    for route in value["service_routes"]:
        workloads = ", ".join(item["subject"] for item in route["resolved_workloads"]) or "none"
        lines.append(f"- [{route['state']}] {route['service']} paths={len(route['paths'])} resolved_workloads={workloads}")
        for path in [p for p in route["paths"] if p["resolution"] != "RESOLVED_WORKLOAD"][:10]:
            target = path.get("target")
            target_label = _label(target["kind"], target.get("namespace"), target["name"]) if target else "targetRef-missing"
            lines.append(f"  - {path['resolution']}: {target_label}")
    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "EndpointSlice association uses the observed kubernetes.io/service-name label. Endpoint backends use targetRef. Pod controller ownership uses exact-name Pod GETs projected to controller ownerReferences only. Deployment resolution follows an exact ReplicaSet GET and its controller ownerReference; Pod names are never parsed to infer controllers.",
            "",
            "Pod and ReplicaSet permissions are GET-only and are not enumerable by this observer. Persisted evidence excludes Pod specs, container/env configuration, labels, annotations, Pod/endpoint IP addresses, logs, Secret values, service-account tokens, and owner UIDs.",
            "",
            "This artifact is acceptance-gated and does not yet replace selector-based Service-to-workload inference in inventory or incident candidates.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build bounded Kubernetes EndpointSlice/Pod routing ownership evidence.")
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path)
    parser.add_argument("--context", dest="kubectl_context")
    parser.add_argument("--max-pod-gets", type=int, default=DEFAULT_MAX_POD_GETS)
    parser.add_argument("--max-replicaset-gets", type=int, default=DEFAULT_MAX_REPLICASET_GETS)
    args = parser.parse_args()
    import json
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    result = build_routing_ownership(
        snapshot,
        kubectl_context=args.kubectl_context,
        max_pod_gets=args.max_pod_gets,
        max_replicaset_gets=args.max_replicaset_gets,
    )
    atomic_write_json(args.out, result)
    if args.summary_out:
        atomic_write_text(args.summary_out, render_routing_ownership_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
