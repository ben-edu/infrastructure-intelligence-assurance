import json
import subprocess
from datetime import datetime, timezone

from infra_assurance.kubernetes_inventory import RESOURCE_QUERIES, build_inventory_context, collect_inventory

NOW = datetime(2026, 8, 14, 16, 0, tzinfo=timezone.utc)


def _payload(kind):
    base = {"metadata": {"name": "sample"}}
    if kind not in ("Namespace", "Node"):
        base["metadata"]["namespace"] = "apps"
    if kind == "Namespace":
        base["status"] = {"phase": "Active"}
    elif kind == "Node":
        base["spec"] = {"unschedulable": False}
        base["status"] = {"conditions": [{"type": "Ready", "status": "True"}], "nodeInfo": {"kubeletVersion": "v1.33.0", "operatingSystem": "linux", "architecture": "amd64"}, "allocatable": {"cpu": "4", "memory": "8Gi", "pods": "110"}}
    elif kind == "Deployment":
        base["spec"] = {"replicas": 2, "template": {"spec": {"containers": [{"image": "example/api:v1"}]}}}
        base["status"] = {"updatedReplicas": 2, "readyReplicas": 2, "availableReplicas": 2}
    elif kind == "StatefulSet":
        base["spec"] = {"replicas": 1, "template": {"spec": {"containers": [{"image": "postgres:16"}]}}, "volumeClaimTemplates": [{"metadata": {"name": "data"}}]}
        base["status"] = {"currentReplicas": 1, "updatedReplicas": 1, "readyReplicas": 1}
    elif kind == "DaemonSet":
        base["spec"] = {"template": {"spec": {"containers": [{"image": "agent:v1"}]}}}
        base["status"] = {"desiredNumberScheduled": 3, "currentNumberScheduled": 3, "updatedNumberScheduled": 3, "numberReady": 3, "numberAvailable": 3}
    elif kind == "Service":
        base["spec"] = {"type": "ClusterIP", "clusterIP": "10.0.0.10", "selector": {"app": "api"}, "ports": [{"port": 80, "targetPort": 8080, "protocol": "TCP"}]}
        base["status"] = {}
    elif kind == "Ingress":
        base["spec"] = {"ingressClassName": "traefik", "rules": [{"host": "example.invalid", "http": {"paths": [{"path": "/", "backend": {"service": {"name": "api", "port": {"number": 80}}}}]}}], "tls": [{"secretName": "example-tls"}]}
        base["status"] = {"loadBalancer": {"ingress": [{"ip": "192.0.2.10"}]}}
    elif kind == "PersistentVolumeClaim":
        base["spec"] = {"storageClassName": "local-path", "accessModes": ["ReadWriteOnce"], "resources": {"requests": {"storage": "10Gi"}}, "volumeName": "pvc-1"}
        base["status"] = {"phase": "Bound", "capacity": {"storage": "10Gi"}}
    return {"apiVersion": "v1", "items": [base]}


def runner(command, **kwargs):
    resource = command[command.index("get") + 1]
    query = next(q for q in RESOURCE_QUERIES if q.kubectl_resource == resource)
    return subprocess.CompletedProcess(command, 0, json.dumps(_payload(query.kind)), "")


def test_collects_full_milestone_one_inventory():
    snapshot = collect_inventory(cluster_id="k3s-main", runner=runner, now=NOW)
    collection_kinds = {e["subject"]["kind"] for e in snapshot["evidence"] if e["subject"]["kind"].endswith("Collection")}
    assert collection_kinds == {f"{q.kind}Collection" for q in RESOURCE_QUERIES}
    resource_kinds = {e["subject"]["kind"] for e in snapshot["evidence"] if not e["subject"]["kind"].endswith("Collection")}
    assert resource_kinds == {q.kind for q in RESOURCE_QUERIES}
    assert all(e["plane"] == "observed" for e in snapshot["evidence"])


def test_failure_is_unknown_not_absent():
    def forbidden(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "", "Error from server (Forbidden): forbidden")
    snapshot = collect_inventory(cluster_id="k3s-main", runner=forbidden, now=NOW)
    assert len(snapshot["evidence"]) == len(RESOURCE_QUERIES)
    assert all(e["existence"] == "UNKNOWN" for e in snapshot["evidence"])
    assert all(e["observation_status"] == "FAILED_TO_OBSERVE" for e in snapshot["evidence"])


def test_context_is_read_only_and_preserves_failures():
    snapshot = collect_inventory(cluster_id="k3s-main", runner=runner, now=NOW)
    context = build_inventory_context(snapshot, now=NOW)
    assert context["task"]["mutation_allowed"] is False
    assert context["task"]["scope"] == {"cluster": "k3s-main", "namespace": None}
    assert not context["observation_failures"]
    assert len(context["facts"]) == len(snapshot["evidence"])


def test_inventory_scope_never_requests_secrets():
    assert all(q.kubectl_resource != "secrets" for q in RESOURCE_QUERIES)
    assert all("secret" not in q.kubectl_resource for q in RESOURCE_QUERIES)
