from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence import freshness

PREFLIGHT_VERSION = "0.1"
REQUEST_VERSION = "0.1"
REQUEST_TYPE = "hypothetical_kubernetes_application_deployment"
RELEVANT_COLLECTIONS = (
    "Namespace",
    "Node",
    "Deployment",
    "Service",
    "Ingress",
    "PersistentVolumeClaim",
)
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet"}


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _exact_keys(value: dict[str, Any], allowed: set[str], where: str) -> None:
    unexpected = set(value) - allowed
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise ValueError(f"Unsupported field(s) in {where}: {names}")


def validate_request(request: dict[str, Any]) -> None:
    _exact_keys(
        request,
        {
            "request_version",
            "type",
            "cluster_id",
            "namespace",
            "application",
            "deployment",
            "service",
            "ingress",
            "pvc",
        },
        "request",
    )
    required = {"request_version", "type", "cluster_id", "namespace", "application", "deployment"}
    missing = required - set(request)
    if missing:
        raise ValueError(f"Missing required request field(s): {', '.join(sorted(missing))}")
    if request["request_version"] != REQUEST_VERSION:
        raise ValueError(f"Unsupported request_version: {request['request_version']}")
    if request["type"] != REQUEST_TYPE:
        raise ValueError(f"Unsupported request type: {request['type']}")
    for field in ("cluster_id", "namespace", "application"):
        if not isinstance(request[field], str) or not request[field].strip():
            raise ValueError(f"{field} must be a non-empty string")

    deployment = request["deployment"]
    if not isinstance(deployment, dict):
        raise ValueError("deployment must be an object")
    _exact_keys(deployment, {"name", "replicas", "image"}, "deployment")
    if set(deployment) != {"name", "replicas", "image"}:
        raise ValueError("deployment requires name, replicas, and image")
    if not isinstance(deployment["name"], str) or not deployment["name"]:
        raise ValueError("deployment.name must be a non-empty string")
    if not isinstance(deployment["replicas"], int) or deployment["replicas"] < 1:
        raise ValueError("deployment.replicas must be an integer greater than zero")
    if not isinstance(deployment["image"], str) or not deployment["image"]:
        raise ValueError("deployment.image must be a non-empty string")

    service = request.get("service")
    if service is not None:
        if not isinstance(service, dict):
            raise ValueError("service must be an object")
        _exact_keys(service, {"name", "port", "target_port"}, "service")
        if set(service) != {"name", "port", "target_port"}:
            raise ValueError("service requires name, port, and target_port")
        if not isinstance(service["name"], str) or not service["name"]:
            raise ValueError("service.name must be a non-empty string")
        for field in ("port", "target_port"):
            if not isinstance(service[field], int) or not (1 <= service[field] <= 65535):
                raise ValueError(f"service.{field} must be an integer in 1..65535")

    ingress = request.get("ingress")
    if ingress is not None:
        if service is None:
            raise ValueError("ingress requires a service in the same request")
        if not isinstance(ingress, dict):
            raise ValueError("ingress must be an object")
        _exact_keys(ingress, {"name", "host", "path"}, "ingress")
        if set(ingress) != {"name", "host", "path"}:
            raise ValueError("ingress requires name, host, and path")
        for field in ("name", "host", "path"):
            if not isinstance(ingress[field], str) or not ingress[field]:
                raise ValueError(f"ingress.{field} must be a non-empty string")
        if not ingress["path"].startswith("/"):
            raise ValueError("ingress.path must start with '/'")

    pvc = request.get("pvc")
    if pvc is not None:
        if not isinstance(pvc, dict):
            raise ValueError("pvc must be an object")
        _exact_keys(pvc, {"name", "size", "storage_class"}, "pvc")
        if "name" not in pvc or "size" not in pvc:
            raise ValueError("pvc requires name and size")
        if not isinstance(pvc["name"], str) or not pvc["name"]:
            raise ValueError("pvc.name must be a non-empty string")
        if not isinstance(pvc["size"], str) or not pvc["size"]:
            raise ValueError("pvc.size must be a non-empty string")
        if "storage_class" in pvc and pvc["storage_class"] is not None:
            if not isinstance(pvc["storage_class"], str) or not pvc["storage_class"]:
                raise ValueError("pvc.storage_class must be null or a non-empty string")


def _collection(snapshot: dict[str, Any], kind: str) -> dict[str, Any] | None:
    wanted = f"{kind}Collection"
    for envelope in snapshot.get("evidence", []):
        if envelope.get("subject", {}).get("kind") == wanted:
            return envelope
    return None


def _resources(snapshot: dict[str, Any]) -> dict[tuple[str, str | None, str], dict[str, Any]]:
    result: dict[tuple[str, str | None, str], dict[str, Any]] = {}
    for envelope in snapshot.get("evidence", []):
        if envelope.get("observation_status") != "COMPLETE":
            continue
        subject = envelope.get("subject", {})
        kind = subject.get("kind")
        name = subject.get("name")
        if not kind or not name or kind.endswith("Collection"):
            continue
        result[(kind, subject.get("namespace"), name)] = envelope
    return result


def _item(code: str, statement: str, evidence_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "statement": statement,
        "evidence_ids": list(dict.fromkeys(evidence_ids or [])),
    }


def _verification(code: str, check: str, reason: str, evidence_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "check": check,
        "reason": reason,
        "evidence_ids": list(dict.fromkeys(evidence_ids or [])),
    }


def _label(envelope: dict[str, Any]) -> str:
    subject = envelope["subject"]
    namespace = f"{subject['namespace']}/" if subject.get("namespace") else ""
    return f"{subject['kind']}/{namespace}{subject['name']}"


def _topology_issue_in_namespace(issue: dict[str, Any], namespace: str) -> bool:
    marker = f"/{namespace}/"
    subject = issue.get("subject", "")
    target = issue.get("target", "")
    return marker in subject or marker in target


def _requested_objects(request: dict[str, Any]) -> list[tuple[str, str, str]]:
    namespace = request["namespace"]
    result = [("Deployment", namespace, request["deployment"]["name"])]
    if request.get("service"):
        result.append(("Service", namespace, request["service"]["name"]))
    if request.get("ingress"):
        result.append(("Ingress", namespace, request["ingress"]["name"]))
    if request.get("pvc"):
        result.append(("PersistentVolumeClaim", namespace, request["pvc"]["name"]))
    return result


def build_deployment_preflight(
    snapshot: dict[str, Any],
    operational_context: dict[str, Any],
    topology: dict[str, Any],
    request: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    validate_request(request)
    now = now or datetime.now(timezone.utc)

    facts: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    inferences: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    required: list[dict[str, Any]] = []
    plan_steps: list[dict[str, Any]] = []
    post_change: list[dict[str, Any]] = []

    cluster_id = request["cluster_id"]
    namespace = request["namespace"]
    resources = _resources(snapshot)

    if snapshot.get("cluster_id") != cluster_id:
        unknowns.append(_item("SNAPSHOT_CLUSTER_MISMATCH", "The evidence snapshot belongs to a different cluster."))
    if topology.get("cluster_id") != cluster_id:
        unknowns.append(_item("TOPOLOGY_CLUSTER_MISMATCH", "The topology projection belongs to a different cluster."))
    context_scope = operational_context.get("task", {}).get("scope", {})
    if context_scope.get("cluster") != cluster_id:
        unknowns.append(_item("CONTEXT_CLUSTER_MISMATCH", "The operational context belongs to a different cluster."))
    if topology.get("generated_at") != snapshot.get("generated_at"):
        unknowns.append(
            _item(
                "TOPOLOGY_SNAPSHOT_MISMATCH",
                "The topology projection was not generated from the current evidence snapshot.",
            )
        )

    collection_health: dict[str, bool] = {}
    for kind in RELEVANT_COLLECTIONS:
        envelope = _collection(snapshot, kind)
        if envelope is None:
            collection_health[kind] = False
            unknowns.append(_item("COLLECTION_MISSING", f"No {kind} collection evidence is available."))
            required.append(
                _verification(
                    "REFRESH_COLLECTION",
                    f"Refresh the {kind} collection.",
                    f"Planning cannot safely use absence or current-state claims without a complete {kind} collection.",
                )
            )
            continue
        if envelope.get("observation_status") != "COMPLETE":
            collection_health[kind] = False
            error_codes = [error.get("code", "UNKNOWN") for error in envelope.get("errors", [])]
            unknowns.append(
                _item(
                    "COLLECTION_FAILED",
                    f"The latest {kind} collection did not complete successfully ({', '.join(error_codes)}).",
                    [envelope["evidence_id"]],
                )
            )
            required.append(
                _verification(
                    "REFRESH_COLLECTION",
                    f"Re-observe {kind} resources successfully.",
                    "The latest collection failed, so missing resources must not be interpreted as absent.",
                    [envelope["evidence_id"]],
                )
            )
            continue
        state = freshness(envelope, now)
        if state != "CURRENT":
            collection_health[kind] = False
            unknowns.append(
                _item(
                    "COLLECTION_STALE",
                    f"The {kind} collection is stale.",
                    [envelope["evidence_id"]],
                )
            )
            required.append(
                _verification(
                    "REFRESH_COLLECTION",
                    f"Refresh the {kind} collection before change approval.",
                    "Expired evidence may be useful as last-known state but cannot substantiate a current-state change plan.",
                    [envelope["evidence_id"]],
                )
            )
            continue
        collection_health[kind] = True

    namespace_env = resources.get(("Namespace", None, namespace))
    if collection_health.get("Namespace"):
        ns_collection = _collection(snapshot, "Namespace")
        ns_ids = [ns_collection["evidence_id"]] if ns_collection else []
        if namespace_env:
            facts.append(
                _item(
                    "NAMESPACE_PRESENT",
                    f"Namespace/{namespace} is present in the current observed inventory.",
                    [namespace_env["evidence_id"]],
                )
            )
            plan_steps.append(
                {
                    "order": 1,
                    "action": f"Reuse existing namespace {namespace}.",
                    "state": "OBSERVED_PRESENT",
                    "evidence_ids": [namespace_env["evidence_id"]],
                }
            )
        else:
            facts.append(
                _item(
                    "NAMESPACE_NOT_OBSERVED",
                    f"Namespace/{namespace} was not observed in the current complete Namespace collection.",
                    ns_ids,
                )
            )
            plan_steps.append(
                {
                    "order": 1,
                    "action": f"Include creation of namespace {namespace} in the reviewed change if this deployment is approved.",
                    "state": "WOULD_REQUIRE_CREATION",
                    "evidence_ids": ns_ids,
                }
            )

    kind_collection_names = {
        "Deployment": "Deployment",
        "Service": "Service",
        "Ingress": "Ingress",
        "PersistentVolumeClaim": "PersistentVolumeClaim",
    }
    for kind, ns, name in _requested_objects(request):
        if not collection_health.get(kind_collection_names[kind]):
            continue
        existing = resources.get((kind, ns, name))
        collection_env = _collection(snapshot, kind_collection_names[kind])
        evidence_ids = [collection_env["evidence_id"]] if collection_env else []
        if existing:
            conflicts.append(
                _item(
                    "RESOURCE_NAME_CONFLICT",
                    f"Requested {kind}/{ns}/{name} already exists in current observed state.",
                    [existing["evidence_id"]],
                )
            )
        else:
            facts.append(
                _item(
                    "RESOURCE_NAME_AVAILABLE",
                    f"No {kind}/{ns}/{name} was observed in the current complete {kind} collection.",
                    evidence_ids,
                )
            )

    if request.get("ingress") and collection_health.get("Ingress"):
        requested_host = request["ingress"]["host"]
        requested_path = request["ingress"]["path"]
        same_host_other_paths: list[dict[str, Any]] = []
        for (kind, _ns, _name), envelope in resources.items():
            if kind != "Ingress":
                continue
            for backend in envelope.get("data", {}).get("backends", []):
                if backend.get("host") != requested_host:
                    continue
                existing_path = backend.get("path") or "/"
                if existing_path == requested_path:
                    conflicts.append(
                        _item(
                            "INGRESS_ROUTE_CONFLICT",
                            f"Ingress host/path {requested_host}{requested_path} is already referenced by {_label(envelope)}.",
                            [envelope["evidence_id"]],
                        )
                    )
                else:
                    same_host_other_paths.append(envelope)
        if same_host_other_paths:
            ids = [item["evidence_id"] for item in same_host_other_paths]
            inferences.append(
                _item(
                    "INGRESS_HOST_SHARED",
                    f"Ingress host {requested_host} is already used on other paths; coexistence may be valid but routing ownership requires review.",
                    ids,
                )
            )
            required.append(
                _verification(
                    "VERIFY_INGRESS_HOST_ROUTING",
                    f"Review existing routes for host {requested_host} before approving the new path.",
                    "Sharing a host across paths can be valid, but the current evidence does not prove controller-specific routing policy.",
                    ids,
                )
            )

    if collection_health.get("Node"):
        nodes = [env for (kind, _ns, _name), env in resources.items() if kind == "Node"]
        not_ready = [env for env in nodes if env.get("data", {}).get("ready") is not True]
        unschedulable = [env for env in nodes if env.get("data", {}).get("unschedulable") is True]
        node_ids = [env["evidence_id"] for env in nodes]
        if nodes and not not_ready and not unschedulable:
            facts.append(
                _item(
                    "NODES_READY",
                    f"All {len(nodes)} observed Nodes are Ready and schedulable in the current snapshot.",
                    node_ids,
                )
            )
        else:
            affected = sorted({_label(env) for env in not_ready + unschedulable})
            inferences.append(
                _item(
                    "NODE_READINESS_ATTENTION",
                    f"Observed Node readiness/schedulability needs attention: {', '.join(affected) if affected else 'no Node records available'}.",
                    [env["evidence_id"] for env in not_ready + unschedulable],
                )
            )
            required.append(
                _verification(
                    "VERIFY_SCHEDULING_TARGETS",
                    "Confirm that sufficient schedulable Nodes are currently available.",
                    "Node readiness or schedulability is not uniformly healthy in the current snapshot.",
                    [env["evidence_id"] for env in not_ready + unschedulable],
                )
            )

    target_exception_facts = [
        fact
        for fact in operational_context.get("facts", [])
        if not fact.get("subject", "").endswith("Collection/*") and f"/{namespace}/" in fact.get("subject", "")
    ]
    for fact in target_exception_facts:
        inferences.append(
            _item(
                "EXISTING_NAMESPACE_EXCEPTION",
                f"Existing operational exception in target namespace: {fact['subject']}.",
                fact.get("evidence_ids", []),
            )
        )

    target_topology_issues = [
        issue for issue in topology.get("issues", []) if _topology_issue_in_namespace(issue, namespace)
    ]
    for issue in target_topology_issues:
        inferences.append(
            _item(
                "EXISTING_TOPOLOGY_UNCERTAINTY",
                f"Existing topology uncertainty in target namespace: {issue.get('statement', issue.get('code'))}",
                issue.get("evidence_ids", []),
            )
        )
        required.append(
            _verification(
                "RESOLVE_RELEVANT_TOPOLOGY_UNCERTAINTY",
                issue.get("required_live_verification", "Resolve the relevant topology uncertainty."),
                "A pre-existing relationship ambiguity intersects the requested deployment namespace.",
                issue.get("evidence_ids", []),
            )
        )

    required.append(
        _verification(
            "VERIFY_IMAGE_PULLABILITY",
            f"Verify that cluster nodes can pull image {request['deployment']['image']} with the intended registry authentication path.",
            "Image registry reachability and pull authentication are outside the current Kubernetes evidence slice.",
        )
    )
    required.append(
        _verification(
            "VERIFY_SCHEDULING_CAPACITY",
            "Verify current scheduling capacity for the requested replicas and resource requests before approval.",
            "Node allocatable values are observed, but aggregate workload requests, actual placement pressure, and scheduler feasibility are not modeled yet.",
        )
    )
    required.append(
        _verification(
            "VERIFY_NAMESPACE_POLICY",
            f"Verify ResourceQuota and LimitRange policy in namespace {namespace} before approval.",
            "ResourceQuota and LimitRange evidence are not collected in Milestone 1.",
        )
    )

    if request.get("service") or request.get("ingress"):
        required.append(
            _verification(
                "VERIFY_NETWORK_POLICY",
                f"Verify NetworkPolicy constraints relevant to namespace {namespace} and the requested traffic path.",
                "NetworkPolicy evidence is outside the current Milestone 1 scope.",
            )
        )
    if request.get("ingress"):
        required.append(
            _verification(
                "VERIFY_EXTERNAL_DNS",
                f"Verify DNS ownership and routing for host {request['ingress']['host']}.",
                "External DNS state is not part of the current Kubernetes evidence slice.",
            )
        )
    if request.get("pvc"):
        storage_class = request["pvc"].get("storage_class")
        requested = storage_class if storage_class else "the cluster default StorageClass"
        required.append(
            _verification(
                "VERIFY_STORAGE_PROVISIONING",
                f"Verify {requested} and provisioning support for requested PVC size {request['pvc']['size']}.",
                "StorageClass and provisioner capability are not collected in Milestone 1.",
            )
        )

    next_order = 2
    if request.get("pvc"):
        plan_steps.append(
            {
                "order": next_order,
                "action": f"Prepare PVC {request['pvc']['name']} ({request['pvc']['size']}) in namespace {namespace}.",
                "state": "PLAN_ONLY",
                "evidence_ids": [],
            }
        )
        next_order += 1
    plan_steps.append(
        {
            "order": next_order,
            "action": f"Prepare Deployment {request['deployment']['name']} with {request['deployment']['replicas']} replicas using image {request['deployment']['image']}.",
            "state": "PLAN_ONLY",
            "evidence_ids": [],
        }
    )
    next_order += 1
    if request.get("service"):
        plan_steps.append(
            {
                "order": next_order,
                "action": f"Prepare Service {request['service']['name']} on port {request['service']['port']} targeting port {request['service']['target_port']}.",
                "state": "PLAN_ONLY",
                "evidence_ids": [],
            }
        )
        next_order += 1
    if request.get("ingress"):
        plan_steps.append(
            {
                "order": next_order,
                "action": f"Prepare Ingress {request['ingress']['name']} for {request['ingress']['host']}{request['ingress']['path']}.",
                "state": "PLAN_ONLY",
                "evidence_ids": [],
            }
        )

    post_change.extend(
        [
            _item(
                "VERIFY_DEPLOYMENT_READINESS",
                f"After an approved future change, verify Deployment/{namespace}/{request['deployment']['name']} reaches desired and ready replicas.",
            ),
            _item(
                "VERIFY_NO_NEW_OPERATIONAL_EXCEPTIONS",
                "After an approved future change, refresh evidence and confirm no new operational exception was introduced.",
            ),
        ]
    )
    if request.get("service"):
        post_change.append(
            _item(
                "VERIFY_SERVICE_ENDPOINTS",
                f"After an approved future change, verify Service/{namespace}/{request['service']['name']} has the intended live endpoints.",
            )
        )
    if request.get("ingress"):
        post_change.append(
            _item(
                "VERIFY_INGRESS_ROUTE",
                f"After an approved future change, verify the route {request['ingress']['host']}{request['ingress']['path']} reaches the intended backend.",
            )
        )
    if request.get("pvc"):
        post_change.append(
            _item(
                "VERIFY_PVC_BOUND",
                f"After an approved future change, verify PersistentVolumeClaim/{namespace}/{request['pvc']['name']} is Bound before depending on storage.",
            )
        )

    if unknowns:
        readiness = "INSUFFICIENT_EVIDENCE"
    elif conflicts:
        readiness = "BLOCKED_BY_CURRENT_CONFLICT"
    else:
        readiness = "PLAN_WITH_LIVE_VERIFICATION"

    return {
        "preflight_version": PREFLIGHT_VERSION,
        "generated_at": _rfc3339(now),
        "cluster_id": cluster_id,
        "request": request,
        "mutation_allowed": False,
        "readiness": readiness,
        "facts": facts,
        "conflicts": conflicts,
        "inferences": inferences,
        "unknowns": unknowns,
        "required_live_verification": required,
        "candidate_plan": sorted(plan_steps, key=lambda item: item["order"]),
        "post_change_verification": post_change,
    }


def render_preflight_markdown(preflight: dict[str, Any]) -> str:
    request = preflight["request"]
    lines = [
        "# Kubernetes Deployment Planning Preflight",
        "",
        f"Cluster: `{preflight['cluster_id']}`",
        f"Namespace: `{request['namespace']}`",
        f"Application: `{request['application']}`",
        f"Generated: `{preflight['generated_at']}`",
        f"Readiness: `{preflight['readiness']}`",
        "Mutation allowed: `false`",
        "",
    ]

    sections = (
        ("Evidence-backed facts", "facts"),
        ("Observed conflicts", "conflicts"),
        ("Inferences and attention", "inferences"),
        ("Unknown evidence state", "unknowns"),
    )
    for title, key in sections:
        lines.extend([f"## {title}", ""])
        items = preflight[key]
        if items:
            for item in items:
                lines.append(f"- [{item['code']}] {item['statement']}")
        else:
            lines.append("- None.")
        lines.append("")

    lines.extend(["## Required live verification", ""])
    if preflight["required_live_verification"]:
        for item in preflight["required_live_verification"]:
            lines.append(f"- [{item['code']}] {item['check']}")
            lines.append(f"  Reason: {item['reason']}")
    else:
        lines.append("- None.")
    lines.append("")

    lines.extend(["## Candidate plan", ""])
    for step in preflight["candidate_plan"]:
        lines.append(f"{step['order']}. {step['action']} ({step['state']})")
    lines.append("")

    lines.extend(["## Post-change verification", ""])
    for item in preflight["post_change_verification"]:
        lines.append(f"- [{item['code']}] {item['statement']}")
    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "This is a read-only planning artifact derived from current evidence. It is not approval to mutate infrastructure, and it must not be used to convert unknown, stale, failed, or inferred state into fact.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a read-only Kubernetes deployment planning preflight from current evidence."
    )
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("/var/lib/infra-assurance/evidence/kubernetes.json"),
    )
    parser.add_argument(
        "--context",
        type=Path,
        default=Path("/var/lib/infra-assurance/evidence/context.json"),
    )
    parser.add_argument(
        "--topology",
        type=Path,
        default=Path("/var/lib/infra-assurance/evidence/topology.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/var/lib/infra-assurance/evidence/preflight.json"),
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("/var/lib/infra-assurance/evidence/preflight.md"),
    )
    args = parser.parse_args()

    request = json.loads(args.request.read_text(encoding="utf-8"))
    snapshot = json.loads(args.evidence.read_text(encoding="utf-8"))
    operational_context = json.loads(args.context.read_text(encoding="utf-8"))
    topology = json.loads(args.topology.read_text(encoding="utf-8"))
    preflight = build_deployment_preflight(snapshot, operational_context, topology, request)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.summary_out.write_text(render_preflight_markdown(preflight), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
