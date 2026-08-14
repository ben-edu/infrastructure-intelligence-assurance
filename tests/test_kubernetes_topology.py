import json
from pathlib import Path

import jsonschema

from infra_assurance.kubernetes_inventory import ResourceQuery, _normalize
from infra_assurance.kubernetes_topology import build_kubernetes_topology

NOW = "2026-08-14T16:40:00Z"


def _subject(kind, namespace, name, api_group=""):
    return {
        "system": "kubernetes",
        "cluster": "k3s-main",
        "api_group": api_group,
        "kind": kind,
        "namespace": namespace,
        "name": name,
    }


def _evidence(evidence_id, kind, namespace, name, data, api_group=""):
    return {
        "schema_version": "0.1",
        "evidence_id": evidence_id,
        "plane": "observed",
        "subject": _subject(kind, namespace, name, api_group),
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": NOW,
        "observed_at": NOW,
        "expires_at": "2026-08-14T16:45:00Z",
        "data": data,
        "provenance": {
            "source_type": "kubernetes_api",
            "source_id": "k3s-main",
            "collector": "test",
            "collector_version": "0.3.0",
            "operation": f"LIST {kind}",
        },
        "errors": [],
    }


def _collection(evidence_id, kind, count):
    return _evidence(
        evidence_id,
        f"{kind}Collection",
        None,
        "*",
        {"resource_kind": kind, "item_count": count, "scope": "cluster"},
    )


def _failed_collection(evidence_id, kind):
    envelope = _collection(evidence_id, kind, 0)
    envelope["existence"] = "UNKNOWN"
    envelope["observation_status"] = "FAILED_TO_OBSERVE"
    envelope["observed_at"] = None
    envelope["expires_at"] = None
    envelope["data"] = {}
    envelope["errors"] = [{"code": "TEST_FAILURE", "summary": "Collection failed."}]
    return envelope


def _base_snapshot():
    evidence = [
        _collection("ev-deploy-collection", "Deployment", 1),
        _collection("ev-stateful-collection", "StatefulSet", 0),
        _collection("ev-daemon-collection", "DaemonSet", 0),
        _collection("ev-svc-collection", "Service", 1),
        _collection("ev-pvc-collection", "PersistentVolumeClaim", 1),
        _evidence(
            "ev-deploy",
            "Deployment",
            "apps",
            "api",
            {
                "desired_replicas": 2,
                "ready_replicas": 2,
                "available_replicas": 2,
                "pod_labels": {"app": "api", "tier": "backend"},
                "selector": {"app": "api"},
                "persistent_volume_claims": ["api-data"],
            },
            "apps",
        ),
        _evidence(
            "ev-service",
            "Service",
            "apps",
            "api",
            {"selector": {"app": "api"}, "ports": [{"port": 80}]},
        ),
        _evidence(
            "ev-ingress",
            "Ingress",
            "apps",
            "api",
            {
                "backends": [
                    {
                        "host": "api.example.invalid",
                        "path": "/",
                        "service": "api",
                        "service_port": 80,
                    }
                ]
            },
            "networking.k8s.io",
        ),
        _evidence(
            "ev-pvc",
            "PersistentVolumeClaim",
            "apps",
            "api-data",
            {"phase": "Bound"},
        ),
    ]
    return {
        "snapshot_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": NOW,
        "evidence": evidence,
    }


def test_derives_direct_and_inferred_relationships():
    topology = build_kubernetes_topology(_base_snapshot())
    types = {relation["type"] for relation in topology["relations"]}
    assert types == {
        "INGRESS_REFERENCES_SERVICE",
        "SERVICE_SELECTOR_MATCHES_WORKLOAD",
        "WORKLOAD_REFERENCES_PVC",
    }

    selector_relation = next(
        relation
        for relation in topology["relations"]
        if relation["type"] == "SERVICE_SELECTOR_MATCHES_WORKLOAD"
    )
    assert selector_relation["basis"] == "SELECTOR_MATCH_INFERENCE"
    assert set(selector_relation["evidence_ids"]) == {"ev-service", "ev-deploy"}

    direct_relation = next(
        relation
        for relation in topology["relations"]
        if relation["type"] == "INGRESS_REFERENCES_SERVICE"
    )
    assert direct_relation["basis"] == "OBSERVED_REFERENCE"


def test_missing_ingress_service_requires_verification_when_collection_complete():
    snapshot = _base_snapshot()
    snapshot["evidence"] = [e for e in snapshot["evidence"] if e["evidence_id"] != "ev-service"]
    topology = build_kubernetes_topology(snapshot)
    issue = next(i for i in topology["issues"] if i["code"] == "INGRESS_SERVICE_NOT_OBSERVED")
    assert issue["severity"] == "REQUIRES_VERIFICATION"
    assert {"ev-ingress", "ev-svc-collection"}.issubset(issue["evidence_ids"])


def test_missing_ingress_service_is_unknown_when_service_collection_failed():
    snapshot = _base_snapshot()
    snapshot["evidence"] = [
        e
        for e in snapshot["evidence"]
        if e["evidence_id"] not in {"ev-service", "ev-svc-collection"}
    ]
    snapshot["evidence"].append(_failed_collection("ev-svc-failed", "Service"))
    topology = build_kubernetes_topology(snapshot)
    issue = next(i for i in topology["issues"] if i["code"] == "INGRESS_SERVICE_TARGET_UNKNOWN")
    assert issue["severity"] == "UNKNOWN_WITH_CURRENT_SCOPE"
    assert "ev-svc-failed" in issue["evidence_ids"]


def test_selector_without_controller_match_is_unknown_not_broken():
    snapshot = _base_snapshot()
    service = next(e for e in snapshot["evidence"] if e["evidence_id"] == "ev-service")
    service["data"]["selector"] = {"app": "standalone"}
    topology = build_kubernetes_topology(snapshot)
    issue = next(i for i in topology["issues"] if i["code"] == "SERVICE_SELECTOR_NO_CONTROLLER_MATCH")
    assert issue["severity"] == "UNKNOWN_WITH_CURRENT_SCOPE"
    assert "EndpointSlices" in issue["required_live_verification"]


def test_selector_scope_failure_remains_unknown():
    snapshot = _base_snapshot()
    snapshot["evidence"] = [
        e for e in snapshot["evidence"] if e["evidence_id"] != "ev-stateful-collection"
    ]
    snapshot["evidence"].append(_failed_collection("ev-stateful-failed", "StatefulSet"))
    topology = build_kubernetes_topology(snapshot)
    issue = next(
        i for i in topology["issues"] if i["code"] == "SERVICE_SELECTOR_CONTROLLER_SCOPE_INCOMPLETE"
    )
    assert issue["severity"] == "UNKNOWN_WITH_CURRENT_SCOPE"
    assert "ev-stateful-failed" in issue["evidence_ids"]


def test_multiple_controller_matches_are_marked_ambiguous():
    snapshot = _base_snapshot()
    snapshot["evidence"].append(
        _evidence(
            "ev-stateful",
            "StatefulSet",
            "apps",
            "api-cache",
            {
                "desired_replicas": 1,
                "ready_replicas": 1,
                "pod_labels": {"app": "api", "component": "cache"},
                "selector": {"app": "api"},
                "persistent_volume_claims": [],
            },
            "apps",
        )
    )
    topology = build_kubernetes_topology(snapshot)
    issue = next(
        i for i in topology["issues"] if i["code"] == "SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES"
    )
    assert issue["severity"] == "AMBIGUOUS"
    matches = [r for r in topology["relations"] if r["type"] == "SERVICE_SELECTOR_MATCHES_WORKLOAD"]
    assert len(matches) == 2


def test_missing_pvc_reference_uses_complete_collection_evidence():
    snapshot = _base_snapshot()
    snapshot["evidence"] = [e for e in snapshot["evidence"] if e["evidence_id"] != "ev-pvc"]
    topology = build_kubernetes_topology(snapshot)
    issue = next(i for i in topology["issues"] if i["code"] == "WORKLOAD_PVC_NOT_OBSERVED")
    assert set(issue["evidence_ids"]) == {"ev-deploy", "ev-pvc-collection"}


def test_missing_pvc_is_unknown_when_pvc_collection_failed():
    snapshot = _base_snapshot()
    snapshot["evidence"] = [
        e
        for e in snapshot["evidence"]
        if e["evidence_id"] not in {"ev-pvc", "ev-pvc-collection"}
    ]
    snapshot["evidence"].append(_failed_collection("ev-pvc-failed", "PersistentVolumeClaim"))
    topology = build_kubernetes_topology(snapshot)
    issue = next(i for i in topology["issues"] if i["code"] == "WORKLOAD_PVC_TARGET_UNKNOWN")
    assert issue["severity"] == "UNKNOWN_WITH_CURRENT_SCOPE"
    assert "ev-pvc-failed" in issue["evidence_ids"]


def test_topology_validates_against_schema():
    topology = build_kubernetes_topology(_base_snapshot())
    schema_path = Path(__file__).parents[1] / "schemas" / "kubernetes-topology.schema.json"
    schema = json.loads(schema_path.read_text())
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    ).validate(topology)


def test_inventory_normalization_exposes_only_relationship_metadata():
    deployment_query = ResourceQuery("Deployment", "apps", "deployments.apps", True)
    deployment = {
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "api"}},
            "template": {
                "metadata": {"labels": {"app": "api", "tier": "backend"}},
                "spec": {
                    "containers": [{"image": "example/api:v1"}],
                    "volumes": [
                        {"name": "data", "persistentVolumeClaim": {"claimName": "api-data"}}
                    ],
                },
            },
        },
        "status": {"readyReplicas": 1, "availableReplicas": 1, "updatedReplicas": 1},
    }
    data = _normalize(deployment_query, deployment)
    assert data["pod_labels"] == {"app": "api", "tier": "backend"}
    assert data["selector"] == {"app": "api"}
    assert data["persistent_volume_claims"] == ["api-data"]


def test_ingress_default_backend_is_normalized():
    ingress_query = ResourceQuery(
        "Ingress", "networking.k8s.io", "ingresses.networking.k8s.io", True
    )
    ingress = {
        "spec": {
            "defaultBackend": {
                "service": {"name": "fallback", "port": {"number": 8080}}
            }
        },
        "status": {},
    }
    data = _normalize(ingress_query, ingress)
    assert data["backends"] == [
        {"host": None, "path": None, "service": "fallback", "service_port": 8080}
    ]
