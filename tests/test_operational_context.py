import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from infra_assurance.operational_context import (
    build_operational_context,
    render_operational_context_markdown,
)

NOW = datetime(2026, 8, 14, 16, 0, tzinfo=timezone.utc)


def _envelope(kind, name, data, *, namespace=None, status="COMPLETE", evidence_id=None):
    observed = NOW.isoformat().replace("+00:00", "Z") if status == "COMPLETE" else None
    expires = (NOW + timedelta(minutes=5)).isoformat().replace("+00:00", "Z") if status == "COMPLETE" else None
    errors = [] if status == "COMPLETE" else [{"code": "KUBERNETES_FORBIDDEN", "summary": "Denied."}]
    return {
        "schema_version": "0.1",
        "evidence_id": evidence_id or f"ev-{kind}-{name}",
        "plane": "observed",
        "subject": {
            "system": "kubernetes",
            "cluster": "k3s-main",
            "api_group": "apps" if kind in {"Deployment", "StatefulSet", "DaemonSet"} else "",
            "kind": kind,
            "namespace": namespace,
            "name": name,
        },
        "existence": "PRESENT" if status == "COMPLETE" else "UNKNOWN",
        "observation_status": status,
        "attempted_at": NOW.isoformat().replace("+00:00", "Z"),
        "observed_at": observed,
        "expires_at": expires,
        "data": data if status == "COMPLETE" else {},
        "provenance": {
            "source_type": "kubernetes_api",
            "source_id": "k3s-main",
            "collector": "kubernetes-inventory-observer",
            "collector_version": "0.2.0",
            "operation": f"LIST {kind}",
        },
        "errors": errors,
    }


def _collection(kind, count):
    return _envelope(
        f"{kind}Collection",
        "*",
        {"resource_kind": kind, "item_count": count, "scope": "cluster"},
    )


def test_compacts_healthy_resources_and_keeps_exceptions():
    snapshot = {
        "snapshot_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "evidence": [
            _collection("Namespace", 10),
            _collection("Node", 3),
            _collection("Deployment", 20),
            _collection("StatefulSet", 3),
            _collection("DaemonSet", 4),
            _collection("Service", 30),
            _collection("Ingress", 12),
            _collection("PersistentVolumeClaim", 9),
            _envelope("Deployment", "healthy", {"desired_replicas": 2, "ready_replicas": 2, "available_replicas": 2}, namespace="apps"),
            _envelope("Deployment", "paused", {"desired_replicas": 0, "ready_replicas": 0, "available_replicas": 0}, namespace="apps"),
            _envelope("StatefulSet", "db", {"desired_replicas": 2, "ready_replicas": 1}, namespace="apps"),
            _envelope("Node", "worker-02", {"ready": False, "unschedulable": False}),
            _envelope("PersistentVolumeClaim", "data", {"phase": "Pending", "storage_class": "local-path"}, namespace="apps"),
        ],
    }

    context = build_operational_context(snapshot, now=NOW)

    assert context["task"]["mutation_allowed"] is False
    assert len([f for f in context["facts"] if f["subject"].endswith("Collection/*")]) == 8
    assert not any(f["subject"] == "Deployment/apps/healthy" for f in context["facts"])
    assert any(f["subject"] == "Deployment/apps/paused" for f in context["facts"])
    statements = [item["statement"] for item in context["inferences"]]
    assert any("StatefulSet/apps/db" in statement and "1/2" in statement for statement in statements)
    assert any("Node/worker-02 is not Ready" in statement for statement in statements)
    assert any("PersistentVolumeClaim/apps/data is not Bound" in statement for statement in statements)
    assert not any("Deployment/apps/paused" in statement for statement in statements)


def test_context_validates_against_milestone_zero_schema():
    snapshot = {
        "snapshot_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "evidence": [_collection("Deployment", 1)],
    }
    context = build_operational_context(snapshot, now=NOW)
    schema = json.loads(Path("schemas/ai-context.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(context)


def test_failed_collection_stays_unknown_and_requires_verification():
    failed = _envelope(
        "IngressCollection",
        "*",
        {},
        status="FAILED_TO_OBSERVE",
        evidence_id="ev-ingress-failed",
    )
    snapshot = {
        "snapshot_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "evidence": [failed],
    }
    context = build_operational_context(snapshot, now=NOW)
    assert len(context["unknowns"]) == 1
    assert context["observation_failures"][0]["evidence_id"] == "ev-ingress-failed"
    assert len(context["required_live_verification"]) == 1


def test_stale_collection_requires_live_verification():
    collection = _collection("Deployment", 4)
    snapshot = {
        "snapshot_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "evidence": [collection],
    }
    context = build_operational_context(snapshot, now=NOW + timedelta(minutes=6))
    assert context["facts"][0]["freshness"] == "STALE"
    assert len(context["required_live_verification"]) == 1


def test_markdown_is_operator_oriented_not_raw_inventory_dump():
    snapshot = {
        "snapshot_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": NOW.isoformat().replace("+00:00", "Z"),
        "evidence": [
            _collection("Deployment", 20),
            _envelope("Deployment", "healthy", {"desired_replicas": 2, "ready_replicas": 2, "available_replicas": 2}, namespace="apps"),
        ],
    }
    context = build_operational_context(snapshot, now=NOW)
    markdown = render_operational_context_markdown(snapshot, context)
    assert "Deployment: 20 (CURRENT)" in markdown
    assert "Deployment/apps/healthy" not in markdown
    assert "Raw normalized evidence remains in `kubernetes.json`" in markdown
