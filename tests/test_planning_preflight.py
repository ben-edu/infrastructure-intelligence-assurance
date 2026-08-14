import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

from infra_assurance.planning_preflight import (
    build_deployment_preflight,
    render_preflight_markdown,
    validate_request,
)

NOW = datetime(2026, 8, 14, 16, 55, tzinfo=timezone.utc)
NOW_TEXT = "2026-08-14T16:55:00Z"
EXPIRES = "2026-08-14T17:00:00Z"


def _subject(kind, namespace, name, api_group=""):
    return {
        "system": "kubernetes",
        "cluster": "k3s-main",
        "api_group": api_group,
        "kind": kind,
        "namespace": namespace,
        "name": name,
    }


def _evidence(evidence_id, kind, namespace, name, data, api_group="", expires_at=EXPIRES):
    return {
        "schema_version": "0.1",
        "evidence_id": evidence_id,
        "plane": "observed",
        "subject": _subject(kind, namespace, name, api_group),
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": NOW_TEXT,
        "observed_at": NOW_TEXT,
        "expires_at": expires_at,
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


def _collection(evidence_id, kind, count=1, expires_at=EXPIRES):
    return _evidence(
        evidence_id,
        f"{kind}Collection",
        None,
        "*",
        {"resource_kind": kind, "item_count": count, "scope": "cluster"},
        expires_at=expires_at,
    )


def _request():
    return {
        "request_version": "0.1",
        "type": "hypothetical_kubernetes_application_deployment",
        "cluster_id": "k3s-main",
        "namespace": "validation",
        "application": "assurance-demo",
        "deployment": {
            "name": "assurance-demo",
            "replicas": 2,
            "image": "registry.example.invalid/assurance-demo:1.0",
        },
        "service": {"name": "assurance-demo", "port": 80, "target_port": 8080},
        "ingress": {
            "name": "assurance-demo",
            "host": "assurance-demo.example.invalid",
            "path": "/",
        },
        "pvc": {"name": "assurance-demo-data", "size": "1Gi", "storage_class": None},
    }


def _snapshot():
    evidence = [
        _collection("ev-ns-c", "Namespace", 2),
        _collection("ev-node-c", "Node", 2),
        _collection("ev-deploy-c", "Deployment", 1),
        _collection("ev-service-c", "Service", 1),
        _collection("ev-ingress-c", "Ingress", 1),
        _collection("ev-pvc-c", "PersistentVolumeClaim", 1),
        _evidence("ev-ns", "Namespace", None, "validation", {"phase": "Active"}),
        _evidence(
            "ev-node-1",
            "Node",
            None,
            "node-1",
            {"ready": True, "unschedulable": False, "allocatable": {"cpu": "4"}},
        ),
        _evidence(
            "ev-node-2",
            "Node",
            None,
            "node-2",
            {"ready": True, "unschedulable": False, "allocatable": {"cpu": "4"}},
        ),
        _evidence(
            "ev-existing-deploy",
            "Deployment",
            "validation",
            "nginx-validation",
            {"desired_replicas": 1, "ready_replicas": 1, "pod_labels": {"app": "nginx"}},
            "apps",
        ),
        _evidence(
            "ev-existing-service",
            "Service",
            "validation",
            "nginx-validation",
            {"selector": {"app": "nginx"}, "ports": [{"port": 80}]},
        ),
        _evidence(
            "ev-existing-ingress",
            "Ingress",
            "validation",
            "nginx-validation",
            {
                "backends": [
                    {
                        "host": "validation.example.invalid",
                        "path": "/",
                        "service": "nginx-validation",
                        "service_port": 80,
                    }
                ]
            },
            "networking.k8s.io",
        ),
        _evidence(
            "ev-existing-pvc",
            "PersistentVolumeClaim",
            "validation",
            "nginx-data",
            {"phase": "Bound"},
        ),
    ]
    return {
        "snapshot_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": NOW_TEXT,
        "evidence": evidence,
    }


def _context():
    return {
        "context_version": "0.1",
        "task": {
            "type": "kubernetes_operational_inventory",
            "scope": {"cluster": "k3s-main", "namespace": None},
            "mutation_allowed": False,
        },
        "generated_at": NOW_TEXT,
        "facts": [],
        "unknowns": [],
        "observation_failures": [],
        "inferences": [],
        "required_live_verification": [],
    }


def _topology(issues=None):
    return {
        "topology_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": NOW_TEXT,
        "summary": {
            "relations_total": 0,
            "ingress_service_references": 0,
            "service_workload_selector_matches": 0,
            "workload_pvc_references": 0,
            "issues_total": len(issues or []),
            "issues_requiring_verification": len(issues or []),
        },
        "relations": [],
        "issues": issues or [],
    }


def _codes(items):
    return {item["code"] for item in items}


def test_clean_request_produces_plan_with_selective_live_verification():
    preflight = build_deployment_preflight(_snapshot(), _context(), _topology(), _request(), now=NOW)

    assert preflight["mutation_allowed"] is False
    assert preflight["readiness"] == "PLAN_WITH_LIVE_VERIFICATION"
    assert not preflight["conflicts"]
    assert not preflight["unknowns"]
    assert "NAMESPACE_PRESENT" in _codes(preflight["facts"])
    assert "NODES_READY" in _codes(preflight["facts"])
    assert _codes(preflight["required_live_verification"]) >= {
        "VERIFY_IMAGE_PULLABILITY",
        "VERIFY_SCHEDULING_CAPACITY",
        "VERIFY_NAMESPACE_POLICY",
        "VERIFY_NETWORK_POLICY",
        "VERIFY_EXTERNAL_DNS",
        "VERIFY_STORAGE_PROVISIONING",
    }
    assert [step["order"] for step in preflight["candidate_plan"]] == [1, 2, 3, 4, 5]


def test_existing_requested_resource_blocks_plan():
    snapshot = _snapshot()
    snapshot["evidence"].append(
        _evidence(
            "ev-conflict",
            "Deployment",
            "validation",
            "assurance-demo",
            {"desired_replicas": 1, "ready_replicas": 1},
            "apps",
        )
    )

    preflight = build_deployment_preflight(snapshot, _context(), _topology(), _request(), now=NOW)
    assert preflight["readiness"] == "BLOCKED_BY_CURRENT_CONFLICT"
    assert "RESOURCE_NAME_CONFLICT" in _codes(preflight["conflicts"])


def test_exact_ingress_route_collision_blocks_plan():
    snapshot = _snapshot()
    ingress = next(e for e in snapshot["evidence"] if e["evidence_id"] == "ev-existing-ingress")
    ingress["data"]["backends"][0]["host"] = "assurance-demo.example.invalid"

    preflight = build_deployment_preflight(snapshot, _context(), _topology(), _request(), now=NOW)
    assert preflight["readiness"] == "BLOCKED_BY_CURRENT_CONFLICT"
    assert "INGRESS_ROUTE_CONFLICT" in _codes(preflight["conflicts"])


def test_shared_ingress_host_on_other_path_requires_review_not_block():
    snapshot = _snapshot()
    ingress = next(e for e in snapshot["evidence"] if e["evidence_id"] == "ev-existing-ingress")
    ingress["data"]["backends"][0]["host"] = "assurance-demo.example.invalid"
    ingress["data"]["backends"][0]["path"] = "/existing"

    preflight = build_deployment_preflight(snapshot, _context(), _topology(), _request(), now=NOW)
    assert preflight["readiness"] == "PLAN_WITH_LIVE_VERIFICATION"
    assert "INGRESS_HOST_SHARED" in _codes(preflight["inferences"])
    assert "VERIFY_INGRESS_HOST_ROUTING" in _codes(preflight["required_live_verification"])


def test_stale_collection_prevents_absence_claims():
    snapshot = _snapshot()
    deployment_collection = next(e for e in snapshot["evidence"] if e["evidence_id"] == "ev-deploy-c")
    deployment_collection["expires_at"] = "2026-08-14T16:54:59Z"

    preflight = build_deployment_preflight(snapshot, _context(), _topology(), _request(), now=NOW)
    assert preflight["readiness"] == "INSUFFICIENT_EVIDENCE"
    assert "COLLECTION_STALE" in _codes(preflight["unknowns"])
    available_statements = [
        item["statement"] for item in preflight["facts"] if item["code"] == "RESOURCE_NAME_AVAILABLE"
    ]
    assert not any("Deployment/validation/assurance-demo" in statement for statement in available_statements)


def test_failed_collection_prevents_absence_claims():
    snapshot = _snapshot()
    service_collection = next(e for e in snapshot["evidence"] if e["evidence_id"] == "ev-service-c")
    service_collection.update(
        {
            "existence": "UNKNOWN",
            "observation_status": "FAILED_TO_OBSERVE",
            "observed_at": None,
            "expires_at": None,
            "data": {},
            "errors": [{"code": "KUBERNETES_FORBIDDEN", "summary": "denied"}],
        }
    )

    preflight = build_deployment_preflight(snapshot, _context(), _topology(), _request(), now=NOW)
    assert preflight["readiness"] == "INSUFFICIENT_EVIDENCE"
    assert "COLLECTION_FAILED" in _codes(preflight["unknowns"])
    available_statements = [
        item["statement"] for item in preflight["facts"] if item["code"] == "RESOURCE_NAME_AVAILABLE"
    ]
    assert not any("Service/validation/assurance-demo" in statement for statement in available_statements)


def test_missing_namespace_is_planned_as_creation_not_false_conflict():
    snapshot = _snapshot()
    snapshot["evidence"] = [e for e in snapshot["evidence"] if e["evidence_id"] != "ev-ns"]

    preflight = build_deployment_preflight(snapshot, _context(), _topology(), _request(), now=NOW)
    assert preflight["readiness"] == "PLAN_WITH_LIVE_VERIFICATION"
    assert "NAMESPACE_NOT_OBSERVED" in _codes(preflight["facts"])
    assert preflight["candidate_plan"][0]["state"] == "WOULD_REQUIRE_CREATION"


def test_existing_topology_uncertainty_is_carried_into_preflight():
    issue = {
        "code": "SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES",
        "severity": "AMBIGUOUS",
        "subject": "Service/validation/shared",
        "statement": "Service/validation/shared selector matched two controllers.",
        "evidence_ids": ["ev-a", "ev-b"],
        "required_live_verification": "Inspect EndpointSlices and Pod ownership.",
    }
    preflight = build_deployment_preflight(_snapshot(), _context(), _topology([issue]), _request(), now=NOW)

    assert "EXISTING_TOPOLOGY_UNCERTAINTY" in _codes(preflight["inferences"])
    assert "RESOLVE_RELEVANT_TOPOLOGY_UNCERTAINTY" in _codes(preflight["required_live_verification"])


def test_request_rejects_unmodeled_secret_or_env_fields():
    request = _request()
    request["deployment"]["env"] = {"PASSWORD": "do-not-accept"}
    with pytest.raises(ValueError, match="Unsupported field"):
        validate_request(request)


def test_request_and_preflight_validate_against_schemas():
    request = _request()
    preflight = build_deployment_preflight(_snapshot(), _context(), _topology(), request, now=NOW)
    root = Path(__file__).parents[1]
    request_schema = json.loads((root / "schemas" / "hypothetical-deployment-request.schema.json").read_text())
    preflight_schema = json.loads((root / "schemas" / "deployment-preflight.schema.json").read_text())

    jsonschema.Draft202012Validator(request_schema).validate(request)
    jsonschema.Draft202012Validator(
        preflight_schema, format_checker=jsonschema.FormatChecker()
    ).validate(preflight)


def test_markdown_keeps_read_only_trust_boundary_visible():
    preflight = build_deployment_preflight(_snapshot(), _context(), _topology(), _request(), now=NOW)
    markdown = render_preflight_markdown(preflight)

    assert "Mutation allowed: `false`" in markdown
    assert "Required live verification" in markdown
    assert "not approval to mutate infrastructure" in markdown
