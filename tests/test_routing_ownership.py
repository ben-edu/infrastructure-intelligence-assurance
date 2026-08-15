from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from infra_assurance.routing_ownership import build_routing_ownership

NOW = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def _collection(kind: str, evidence_id: str, status: str = "COMPLETE") -> dict:
    return {
        "evidence_id": evidence_id,
        "observation_status": status,
        "subject": {"kind": f"{kind}Collection", "namespace": None, "name": "*"},
    }


def _resource(kind: str, namespace: str, name: str, evidence_id: str) -> dict:
    return {
        "evidence_id": evidence_id,
        "observation_status": "COMPLETE",
        "subject": {"kind": kind, "namespace": namespace, "name": name},
    }


def _snapshot(*resources: dict) -> dict:
    return {
        "cluster_id": "k3s-main",
        "evidence": [
            _collection("Service", "service-collection"),
            _collection("Deployment", "deployment-collection"),
            _collection("StatefulSet", "statefulset-collection"),
            _collection("DaemonSet", "daemonset-collection"),
            *resources,
        ],
    }


def _runner(endpoint_output: str, pod_owners: dict[tuple[str, str], str], rs_owners: dict[tuple[str, str], str]):
    calls: list[list[str]] = []

    def run(command, **kwargs):
        calls.append(command)
        resource = command[command.index("get") + 1]
        if resource == "endpointslices.discovery.k8s.io":
            return subprocess.CompletedProcess(command, 0, endpoint_output, "")
        namespace = command[command.index("--namespace") + 1]
        name = command[command.index("get") + 2]
        if resource == "pod":
            value = pod_owners.get((namespace, name))
        elif resource == "replicaset.apps":
            value = rs_owners.get((namespace, name))
        else:
            raise AssertionError(command)
        if value == "NOT_FOUND":
            return subprocess.CompletedProcess(command, 1, "", "Error from server (NotFound): not found")
        if value == "FORBIDDEN":
            return subprocess.CompletedProcess(command, 1, "", "Error from server (Forbidden): forbidden")
        return subprocess.CompletedProcess(command, 0, value or "", "")

    return run, calls


def test_deployment_routing_uses_targetref_pod_and_replicaset_owner_chain():
    endpoints = "apps\tweb-abc\tweb\tv1|Pod|apps|web-pod|true||;\n"
    runner, calls = _runner(
        endpoints,
        {("apps", "web-pod"): "apps/v1|ReplicaSet|web-rs;"},
        {("apps", "web-rs"): "apps/v1|Deployment|web;"},
    )
    result = build_routing_ownership(
        _snapshot(
            _resource("Service", "apps", "web", "service-web"),
            _resource("Deployment", "apps", "web", "deployment-web"),
        ),
        runner=runner,
        now=NOW,
    )

    path = result["service_routes"][0]["paths"][0]
    assert result["source_status"]["overall"] == "COMPLETE"
    assert path["resolution"] == "RESOLVED_WORKLOAD"
    assert path["workload"] == "Deployment/apps/web"
    assert path["basis"] == [
        "ENDPOINTSLICE_SERVICE_NAME_LABEL",
        "ENDPOINT_TARGET_REF",
        "POD_CONTROLLER_OWNER_REFERENCE",
        "REPLICASET_CONTROLLER_OWNER_REFERENCE",
        "CURRENT_WORKLOAD_OBSERVATION",
    ]
    assert result["service_routes"][0]["state"] == "RESOLVED_WORKLOAD_ROUTING"
    assert any("pod" in call and "web-pod" in call for call in calls)
    assert any("replicaset.apps" in call and "web-rs" in call for call in calls)
    assert not any("--all-namespaces" in call and "pod" in call for call in calls)
    assert not any("--all-namespaces" in call and "replicaset.apps" in call for call in calls)


def test_statefulset_and_daemonset_owner_references_resolve_without_name_inference():
    endpoints = (
        "apps\tdb-a\tdb\tv1|Pod|apps|db-0|true||;\n"
        "monitoring\tagent-a\tagent\tv1|Pod|monitoring|agent-xyz|true||;\n"
    )
    runner, _ = _runner(
        endpoints,
        {
            ("apps", "db-0"): "apps/v1|StatefulSet|db;",
            ("monitoring", "agent-xyz"): "apps/v1|DaemonSet|agent;",
        },
        {},
    )
    result = build_routing_ownership(
        _snapshot(
            _resource("Service", "apps", "db", "service-db"),
            _resource("StatefulSet", "apps", "db", "statefulset-db"),
            _resource("Service", "monitoring", "agent", "service-agent"),
            _resource("DaemonSet", "monitoring", "agent", "daemonset-agent"),
        ),
        runner=runner,
        now=NOW,
    )
    resolved = {item["service"]: item["resolved_workloads"] for item in result["service_routes"]}
    assert resolved["Service/apps/db"][0]["subject"] == "StatefulSet/apps/db"
    assert resolved["Service/monitoring/agent"][0]["subject"] == "DaemonSet/monitoring/agent"
    assert result["summary"]["replicaset_gets_requested"] == 0


def test_non_pod_endpoint_target_stays_non_pod_and_does_not_fetch_pod():
    endpoints = "monitoring\tkubelet-a\tkubelet\tv1|Node||k3s-worker-01|true||;\n"
    runner, calls = _runner(endpoints, {}, {})
    result = build_routing_ownership(
        _snapshot(_resource("Service", "monitoring", "kubelet", "service-kubelet")),
        runner=runner,
        now=NOW,
    )
    route = result["service_routes"][0]
    assert route["state"] == "NON_POD_ROUTING"
    assert route["paths"][0]["resolution"] == "NON_POD_TARGET"
    assert route["paths"][0]["target"]["kind"] == "Node"
    assert result["summary"]["pod_gets_requested"] == 0
    assert len(calls) == 1


def test_exact_not_found_is_absence_but_forbidden_is_unknown():
    endpoints = (
        "apps\tmissing-a\tmissing\tv1|Pod|apps|missing-pod|true||;\n"
        "apps\tblocked-a\tblocked\tv1|Pod|apps|blocked-pod|true||;\n"
    )
    runner, _ = _runner(
        endpoints,
        {
            ("apps", "missing-pod"): "NOT_FOUND",
            ("apps", "blocked-pod"): "FORBIDDEN",
        },
        {},
    )
    result = build_routing_ownership(
        _snapshot(
            _resource("Service", "apps", "missing", "service-missing"),
            _resource("Service", "apps", "blocked", "service-blocked"),
        ),
        runner=runner,
        now=NOW,
    )
    resolutions = {
        route["service"]: route["paths"][0]["resolution"]
        for route in result["service_routes"]
    }
    assert resolutions["Service/apps/missing"] == "POD_NOT_FOUND"
    assert resolutions["Service/apps/blocked"] == "POD_OBSERVATION_UNKNOWN"
    assert result["source_status"]["pods"]["absent"] == 1
    assert result["source_status"]["pods"]["unknown"] == 1
    assert result["source_status"]["overall"] == "PARTIAL"


def test_get_bound_is_explicit_partial_evidence():
    endpoints = (
        "apps\ta\tsvc\tv1|Pod|apps|pod-a|true||;v1|Pod|apps|pod-b|true||;\n"
    )
    runner, calls = _runner(
        endpoints,
        {("apps", "pod-a"): "apps/v1|StatefulSet|a;"},
        {},
    )
    result = build_routing_ownership(
        _snapshot(
            _resource("Service", "apps", "svc", "service-svc"),
            _resource("StatefulSet", "apps", "a", "statefulset-a"),
        ),
        runner=runner,
        now=NOW,
        max_pod_gets=1,
    )
    assert result["source_status"]["overall"] == "PARTIAL"
    assert result["source_status"]["pods"]["skipped_by_bound"] == 1
    assert any(path["resolution"] == "POD_GET_BOUND_EXCEEDED" for path in result["service_routes"][0]["paths"])
    pod_calls = [call for call in calls if call[call.index("get") + 1] == "pod"]
    assert len(pod_calls) == 1


def test_projected_artifact_excludes_addresses_uid_labels_annotations_specs_and_secret_material():
    endpoints = "apps\tweb-a\tweb\tv1|Pod|apps|web-pod|true||;\n"
    runner, _ = _runner(
        endpoints,
        {("apps", "web-pod"): "apps/v1|ReplicaSet|web-rs;"},
        {("apps", "web-rs"): "apps/v1|Deployment|web;"},
    )
    result = build_routing_ownership(
        _snapshot(
            _resource("Service", "apps", "web", "service-web"),
            _resource("Deployment", "apps", "web", "deployment-web"),
        ),
        runner=runner,
        now=NOW,
    )
    raw = json.dumps(result)
    for forbidden in (
        "addresses",
        "podIP",
        "containerStatuses",
        "envFrom",
        "secretKeyRef",
        "annotations",
        '"labels"',
        '"uid"',
        "serviceAccountToken",
        "password",
        "private_key",
    ):
        assert forbidden not in raw


def test_schema_validates_routing_ownership_artifact():
    endpoints = "apps\tweb-a\tweb\tv1|Pod|apps|web-pod|true||;\n"
    runner, _ = _runner(
        endpoints,
        {("apps", "web-pod"): "apps/v1|ReplicaSet|web-rs;"},
        {("apps", "web-rs"): "apps/v1|Deployment|web;"},
    )
    result = build_routing_ownership(
        _snapshot(
            _resource("Service", "apps", "web", "service-web"),
            _resource("Deployment", "apps", "web", "deployment-web"),
        ),
        runner=runner,
        now=NOW,
    )
    schema = json.loads((ROOT / "schemas" / "kubernetes-routing-ownership.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(result)
