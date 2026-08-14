from __future__ import annotations

import argparse
import json
import os
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from .evidence import freshness

COLLECTOR_VERSION = "0.3.0"
DEFAULT_TTL_SECONDS = 300
DEFAULT_TIMEOUT_SECONDS = 30
Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class ResourceQuery:
    kind: str
    api_group: str
    kubectl_resource: str
    namespaced: bool


RESOURCE_QUERIES = (
    ResourceQuery("Namespace", "", "namespaces", False),
    ResourceQuery("Node", "", "nodes", False),
    ResourceQuery("Deployment", "apps", "deployments.apps", True),
    ResourceQuery("StatefulSet", "apps", "statefulsets.apps", True),
    ResourceQuery("DaemonSet", "apps", "daemonsets.apps", True),
    ResourceQuery("Service", "", "services", True),
    ResourceQuery("Ingress", "networking.k8s.io", "ingresses.networking.k8s.io", True),
    ResourceQuery("PersistentVolumeClaim", "", "persistentvolumeclaims", True),
)


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _subject(
    cluster_id: str,
    kind: str,
    api_group: str,
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


def _provenance(cluster_id: str, operation: str) -> dict[str, str]:
    return {
        "source_type": "kubernetes_api",
        "source_id": cluster_id,
        "collector": "kubernetes-inventory-observer",
        "collector_version": COLLECTOR_VERSION,
        "operation": operation,
    }


def _envelope(
    *,
    cluster_id: str,
    query: ResourceQuery,
    namespace: str | None,
    name: str,
    attempted_at: datetime,
    data: dict[str, Any],
    ttl_seconds: int,
) -> dict[str, Any]:
    expires_at = attempted_at + timedelta(seconds=ttl_seconds)
    return {
        "schema_version": "0.1",
        "evidence_id": f"ev-{uuid.uuid4()}",
        "plane": "observed",
        "subject": _subject(cluster_id, query.kind, query.api_group, namespace, name),
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": _rfc3339(attempted_at),
        "observed_at": _rfc3339(attempted_at),
        "expires_at": _rfc3339(expires_at),
        "data": data,
        "provenance": _provenance(cluster_id, f"LIST {query.kubectl_resource}"),
        "errors": [],
    }


def _collection_envelope(
    *,
    cluster_id: str,
    query: ResourceQuery,
    attempted_at: datetime,
    ttl_seconds: int,
    item_count: int,
) -> dict[str, Any]:
    return _envelope(
        cluster_id=cluster_id,
        query=ResourceQuery(
            f"{query.kind}Collection", query.api_group, query.kubectl_resource, False
        ),
        namespace=None,
        name="*",
        attempted_at=attempted_at,
        ttl_seconds=ttl_seconds,
        data={"resource_kind": query.kind, "item_count": item_count, "scope": "cluster"},
    )


def _failure_envelope(
    *,
    cluster_id: str,
    query: ResourceQuery,
    attempted_at: datetime,
    code: str,
    summary: str,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "evidence_id": f"ev-{uuid.uuid4()}",
        "plane": "observed",
        "subject": _subject(
            cluster_id, f"{query.kind}Collection", query.api_group, None, "*"
        ),
        "existence": "UNKNOWN",
        "observation_status": "FAILED_TO_OBSERVE",
        "attempted_at": _rfc3339(attempted_at),
        "observed_at": None,
        "expires_at": None,
        "data": {},
        "provenance": _provenance(cluster_id, f"LIST {query.kubectl_resource}"),
        "errors": [{"code": code, "summary": summary}],
    }


def _classify_failure(stderr: str) -> tuple[str, str]:
    lowered = stderr.lower()
    if "forbidden" in lowered:
        return "KUBERNETES_FORBIDDEN", "Kubernetes API denied the inventory read request."
    if "timeout" in lowered or "timed out" in lowered:
        return "KUBERNETES_TIMEOUT", "Kubernetes inventory read request timed out."
    if "connection refused" in lowered or "unable to connect" in lowered:
        return "KUBERNETES_UNREACHABLE", "Kubernetes API could not be reached."
    return "KUBECTL_READ_FAILED", "kubectl could not complete the inventory read request."


def _images(spec: dict[str, Any]) -> list[str]:
    return [
        container.get("image")
        for container in spec.get("template", {}).get("spec", {}).get("containers", [])
        if container.get("image")
    ]


def _pod_labels(spec: dict[str, Any]) -> dict[str, str]:
    labels = spec.get("template", {}).get("metadata", {}).get("labels", {})
    if not isinstance(labels, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in labels.items()
        if isinstance(key, str) and isinstance(value, (str, int, float, bool))
    }


def _workload_selector(spec: dict[str, Any]) -> dict[str, str]:
    labels = spec.get("selector", {}).get("matchLabels", {})
    if not isinstance(labels, dict):
        return {}
    return {
        str(key): str(value)
        for key, value in labels.items()
        if isinstance(key, str) and isinstance(value, (str, int, float, bool))
    }


def _persistent_volume_claims(spec: dict[str, Any]) -> list[str]:
    claims: list[str] = []
    for volume in spec.get("template", {}).get("spec", {}).get("volumes", []):
        claim_name = volume.get("persistentVolumeClaim", {}).get("claimName")
        if isinstance(claim_name, str) and claim_name and claim_name not in claims:
            claims.append(claim_name)
    return claims


def _ready_condition(item: dict[str, Any]) -> bool | None:
    for condition in item.get("status", {}).get("conditions", []):
        if condition.get("type") == "Ready":
            return condition.get("status") == "True"
    return None


def _normalize(query: ResourceQuery, item: dict[str, Any]) -> dict[str, Any]:
    spec, status = item.get("spec", {}), item.get("status", {})

    if query.kind == "Namespace":
        return {"phase": status.get("phase")}

    if query.kind == "Node":
        return {
            "ready": _ready_condition(item),
            "unschedulable": bool(spec.get("unschedulable", False)),
            "kubelet_version": status.get("nodeInfo", {}).get("kubeletVersion"),
            "operating_system": status.get("nodeInfo", {}).get("operatingSystem"),
            "architecture": status.get("nodeInfo", {}).get("architecture"),
            "allocatable": {
                key: status.get("allocatable", {}).get(key)
                for key in ("cpu", "memory", "pods")
                if key in status.get("allocatable", {})
            },
            "taints": [
                {key: taint[key] for key in ("key", "value", "effect") if key in taint}
                for taint in spec.get("taints", [])
            ],
        }

    if query.kind == "Deployment":
        return {
            "desired_replicas": spec.get("replicas", 1),
            "updated_replicas": status.get("updatedReplicas", 0),
            "ready_replicas": status.get("readyReplicas", 0),
            "available_replicas": status.get("availableReplicas", 0),
            "images": _images(spec),
            "selector": _workload_selector(spec),
            "pod_labels": _pod_labels(spec),
            "persistent_volume_claims": _persistent_volume_claims(spec),
        }

    if query.kind == "StatefulSet":
        return {
            "desired_replicas": spec.get("replicas", 1),
            "current_replicas": status.get("currentReplicas", 0),
            "updated_replicas": status.get("updatedReplicas", 0),
            "ready_replicas": status.get("readyReplicas", 0),
            "images": _images(spec),
            "selector": _workload_selector(spec),
            "pod_labels": _pod_labels(spec),
            "persistent_volume_claims": _persistent_volume_claims(spec),
            "volume_claim_templates": [
                template.get("metadata", {}).get("name")
                for template in spec.get("volumeClaimTemplates", [])
                if template.get("metadata", {}).get("name")
            ],
        }

    if query.kind == "DaemonSet":
        return {
            "desired_scheduled": status.get("desiredNumberScheduled", 0),
            "current_scheduled": status.get("currentNumberScheduled", 0),
            "updated_scheduled": status.get("updatedNumberScheduled", 0),
            "ready_scheduled": status.get("numberReady", 0),
            "available_scheduled": status.get("numberAvailable", 0),
            "images": _images(spec),
            "selector": _workload_selector(spec),
            "pod_labels": _pod_labels(spec),
            "persistent_volume_claims": _persistent_volume_claims(spec),
        }

    if query.kind == "Service":
        return {
            "type": spec.get("type", "ClusterIP"),
            "cluster_ip": spec.get("clusterIP"),
            "selector": spec.get("selector", {}),
            "ports": [
                {
                    key: port[key]
                    for key in ("name", "protocol", "port", "targetPort", "nodePort")
                    if key in port
                }
                for port in spec.get("ports", [])
            ],
            "load_balancer_ingress": [
                {key: value[key] for key in ("ip", "hostname") if key in value}
                for value in status.get("loadBalancer", {}).get("ingress", [])
            ],
        }

    if query.kind == "Ingress":
        backends: list[dict[str, Any]] = []

        default_service = spec.get("defaultBackend", {}).get("service", {})
        if default_service.get("name"):
            default_port = default_service.get("port", {})
            backends.append(
                {
                    "host": None,
                    "path": None,
                    "service": default_service.get("name"),
                    "service_port": default_port.get("name", default_port.get("number")),
                }
            )

        for rule in spec.get("rules", []):
            host = rule.get("host")
            for path in rule.get("http", {}).get("paths", []):
                service = path.get("backend", {}).get("service", {})
                port = service.get("port", {})
                if service.get("name"):
                    backends.append(
                        {
                            "host": host,
                            "path": path.get("path"),
                            "service": service.get("name"),
                            "service_port": port.get("name", port.get("number")),
                        }
                    )

        return {
            "ingress_class_name": spec.get("ingressClassName"),
            "backends": backends,
            "tls_secret_names": [
                entry.get("secretName")
                for entry in spec.get("tls", [])
                if entry.get("secretName")
            ],
            "load_balancer_ingress": [
                {key: value[key] for key in ("ip", "hostname") if key in value}
                for value in status.get("loadBalancer", {}).get("ingress", [])
            ],
        }

    if query.kind == "PersistentVolumeClaim":
        return {
            "phase": status.get("phase"),
            "storage_class": spec.get("storageClassName"),
            "access_modes": spec.get("accessModes", []),
            "requested_storage": spec.get("resources", {}).get("requests", {}).get("storage"),
            "capacity": status.get("capacity", {}).get("storage"),
            "volume_name": spec.get("volumeName"),
        }

    raise ValueError(f"Unsupported resource kind: {query.kind}")


def _run_query(
    *,
    cluster_id: str,
    kubectl_context: str | None,
    query: ResourceQuery,
    runner: Runner,
    now: datetime,
    ttl_seconds: int,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    command = ["kubectl"]
    if kubectl_context:
        command += ["--context", kubectl_context]
    command += ["get", query.kubectl_resource]
    if query.namespaced:
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
        return [
            _failure_envelope(
                cluster_id=cluster_id,
                query=query,
                attempted_at=now,
                code="KUBECTL_TIMEOUT",
                summary="kubectl exceeded the local inventory timeout.",
            )
        ]
    except FileNotFoundError:
        return [
            _failure_envelope(
                cluster_id=cluster_id,
                query=query,
                attempted_at=now,
                code="KUBECTL_NOT_AVAILABLE",
                summary="kubectl is not available in the collector runtime.",
            )
        ]

    if result.returncode != 0:
        code, summary = _classify_failure(result.stderr)
        return [
            _failure_envelope(
                cluster_id=cluster_id,
                query=query,
                attempted_at=now,
                code=code,
                summary=summary,
            )
        ]

    try:
        items = json.loads(result.stdout)["items"]
        if not isinstance(items, list):
            raise ValueError
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return [
            _failure_envelope(
                cluster_id=cluster_id,
                query=query,
                attempted_at=now,
                code="KUBECTL_OUTPUT_INVALID",
                summary="Kubernetes inventory output could not be normalized safely.",
            )
        ]

    evidence = [
        _collection_envelope(
            cluster_id=cluster_id,
            query=query,
            attempted_at=now,
            ttl_seconds=ttl_seconds,
            item_count=len(items),
        )
    ]

    for item in items:
        metadata = item.get("metadata", {})
        name = metadata.get("name")
        if name:
            evidence.append(
                _envelope(
                    cluster_id=cluster_id,
                    query=query,
                    namespace=metadata.get("namespace") if query.namespaced else None,
                    name=name,
                    attempted_at=now,
                    ttl_seconds=ttl_seconds,
                    data=_normalize(query, item),
                )
            )
    return evidence


def collect_inventory(
    *,
    cluster_id: str,
    kubectl_context: str | None = None,
    runner: Runner = subprocess.run,
    now: datetime | None = None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    observed_at = now or datetime.now(timezone.utc)
    evidence: list[dict[str, Any]] = []
    for query in RESOURCE_QUERIES:
        evidence.extend(
            _run_query(
                cluster_id=cluster_id,
                kubectl_context=kubectl_context,
                query=query,
                runner=runner,
                now=observed_at,
                ttl_seconds=ttl_seconds,
                timeout_seconds=timeout_seconds,
            )
        )
    return {
        "snapshot_version": "0.1",
        "cluster_id": cluster_id,
        "generated_at": _rfc3339(observed_at),
        "evidence": evidence,
    }


def build_inventory_context(
    snapshot: dict[str, Any], *, now: datetime | None = None
) -> dict[str, Any]:
    """Legacy full projection kept for compatibility with earlier tests and examples."""
    now = now or datetime.now(timezone.utc)
    facts, unknowns, failures, required = [], [], [], []
    for envelope in snapshot["evidence"]:
        subject = envelope["subject"]
        namespace = f"{subject['namespace']}/" if subject["namespace"] else ""
        label = f"{subject['kind']}/{namespace}{subject['name']}"
        if envelope["observation_status"] == "FAILED_TO_OBSERVE":
            unknowns.append({"subject": label, "reason": "Latest collection attempt failed."})
            failures.append(
                {
                    "subject": label,
                    "evidence_id": envelope["evidence_id"],
                    "error_codes": [error["code"] for error in envelope["errors"]],
                }
            )
            required.append(
                {
                    "question": f"Can {label} be observed successfully now?",
                    "reason": "The latest collection attempt failed.",
                }
            )
            continue
        state_freshness = freshness(envelope, now)
        facts.append(
            {
                "subject": label,
                "plane": envelope["plane"],
                "value": envelope["data"],
                "freshness": state_freshness,
                "evidence_ids": [envelope["evidence_id"]],
            }
        )
        if state_freshness == "STALE" and subject["kind"].endswith("Collection"):
            required.append(
                {
                    "question": f"What is the current state of {label}?",
                    "reason": "Inventory collection evidence has expired.",
                }
            )
    return {
        "context_version": "0.1",
        "task": {
            "type": "kubernetes_operational_inventory",
            "scope": {"cluster": snapshot["cluster_id"], "namespace": None},
            "mutation_allowed": False,
        },
        "generated_at": _rfc3339(now),
        "facts": facts,
        "unknowns": unknowns,
        "observation_failures": failures,
        "inferences": [],
        "required_live_verification": required,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect the Milestone 1 Kubernetes read-only inventory."
    )
    parser.add_argument("--cluster-id", default=os.environ.get("IIA_CLUSTER_ID"))
    parser.add_argument(
        "--context", dest="kubectl_context", default=os.environ.get("IIA_KUBECTL_CONTEXT")
    )
    parser.add_argument("--evidence-out", type=Path, required=True)
    parser.add_argument("--context-out", type=Path, required=True)
    args = parser.parse_args()

    if not args.cluster_id:
        parser.error("--cluster-id or IIA_CLUSTER_ID is required")

    snapshot = collect_inventory(
        cluster_id=args.cluster_id,
        kubectl_context=args.kubectl_context,
    )
    context = build_inventory_context(snapshot)

    args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
    args.context_out.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_out.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.context_out.write_text(
        json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
