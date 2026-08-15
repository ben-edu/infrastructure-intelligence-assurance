import json
from datetime import datetime, timedelta, timezone

from infra_assurance.drift import build_drift_report, load_declared_records
from infra_assurance.git_declared_observer import (
    _kind_from_text,
    _normalize_object,
    _split_documents,
)

NOW = datetime(2026, 8, 14, 17, 30, tzinfo=timezone.utc)


def _ts(value):
    return value.isoformat().replace("+00:00", "Z")


def _observed_snapshot():
    collection = {
        "schema_version": "0.1",
        "evidence_id": "ev-deployments",
        "plane": "observed",
        "subject": {
            "system": "kubernetes",
            "cluster": "k3s-main",
            "api_group": "apps",
            "kind": "DeploymentCollection",
            "namespace": None,
            "name": "*",
        },
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": _ts(NOW),
        "observed_at": _ts(NOW),
        "expires_at": _ts(NOW + timedelta(minutes=5)),
        "data": {"resource_kind": "Deployment", "item_count": 1, "scope": "cluster"},
        "provenance": {
            "source_type": "kubernetes_api",
            "source_id": "k3s-main",
            "collector": "test",
            "collector_version": "0.1",
            "operation": "LIST deployments.apps",
        },
        "errors": [],
    }
    deployment = {
        "schema_version": "0.1",
        "evidence_id": "ev-nginx",
        "plane": "observed",
        "subject": {
            "system": "kubernetes",
            "cluster": "k3s-main",
            "api_group": "apps",
            "kind": "Deployment",
            "namespace": "validation",
            "name": "nginx-validation",
        },
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": _ts(NOW),
        "observed_at": _ts(NOW),
        "expires_at": _ts(NOW + timedelta(minutes=5)),
        "data": {
            "desired_replicas": 1,
            "images": ["nginx:stable"],
            "selector": {"app": "nginx-validation"},
        },
        "provenance": {
            "source_type": "kubernetes_api",
            "source_id": "k3s-main",
            "collector": "test",
            "collector_version": "0.1",
            "operation": "LIST deployments.apps",
        },
        "errors": [],
    }
    return {
        "snapshot_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": _ts(NOW),
        "evidence": [collection, deployment],
    }


def _declared_record():
    return {
        "schema_version": "0.1",
        "evidence_id": "ev-git-nginx",
        "plane": "declared",
        "subject": {
            "system": "kubernetes",
            "cluster": "k3s-main",
            "api_group": "apps",
            "kind": "Deployment",
            "namespace": "validation",
            "name": "nginx-validation",
        },
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": _ts(NOW),
        "observed_at": _ts(NOW),
        "expires_at": _ts(NOW + timedelta(minutes=15)),
        "data": {
            "desired_replicas": 1,
            "images": ["nginx:stable"],
            "selector": {"app": "nginx-validation"},
        },
        "provenance": {
            "source_type": "git",
            "source_id": "github.com/ben-edu/api-cluster-infra",
            "collector": "git-declared-observer",
            "collector_version": "0.1.0",
            "operation": "read kubernetes/validation/nginx/nginx-validation.yaml#document=2",
            "revision": "abc123",
        },
        "errors": [],
    }


def test_document_gate_identifies_sensitive_and_supported_kinds_without_yaml_deserialization():
    text = """
apiVersion: v1
kind: Secret
metadata:
  name: do-not-ingest
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: safe
"""
    docs = _split_documents(text)
    assert [_kind_from_text(item) for item in docs] == ["Secret", "Deployment"]


def test_declared_deployment_normalization_keeps_only_modeled_non_sensitive_fields():
    value = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "nginx-validation", "namespace": "validation"},
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "nginx-validation"}},
            "template": {
                "metadata": {"labels": {"app": "nginx-validation"}},
                "spec": {
                    "containers": [
                        {
                            "name": "nginx",
                            "image": "nginx:stable",
                            "env": [{"name": "PASSWORD", "value": "must-not-survive"}],
                        }
                    ]
                },
            },
        },
    }
    normalized, error = _normalize_object(value, cluster_id="k3s-main")
    assert error is None
    assert normalized["data"] == {
        "desired_replicas": 1,
        "images": ["nginx:stable"],
        "selector": {"app": "nginx-validation"},
    }
    assert "PASSWORD" not in json.dumps(normalized)


def test_failed_git_observation_blocks_prior_declared_records(tmp_path):
    declared = tmp_path / "current"
    declared.mkdir()
    (declared / "records.json").write_text(
        json.dumps({"records": [_declared_record()]}), encoding="utf-8"
    )
    status = tmp_path / "source-status.json"
    status.write_text(
        json.dumps(
            {
                "source_status_version": "0.1",
                "source_id": "github.com/ben-edu/api-cluster-infra",
                "attempted_at": _ts(NOW),
                "status": "FAILED_TO_OBSERVE",
                "observed_at": None,
                "revision": None,
                "normalized_records": 0,
                "skipped_documents": 0,
                "errors": [{"code": "GIT_AUTH_FAILED", "summary": "Git source authentication failed."}],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_declared_records(declared, source_status_path=status)
    report = build_drift_report(_observed_snapshot(), loaded, now=NOW)

    assert loaded["status"] == "DECLARED_STATE_OBSERVATION_FAILED"
    assert report["status"] == "DECLARED_STATE_OBSERVATION_FAILED"
    assert report["summary"]["drift"] == 0
    assert report["required_live_verification"][0]["code"] == "REFRESH_DECLARED_GIT_SOURCE"


def test_current_git_declared_record_evaluates_against_live_observation(tmp_path):
    declared = tmp_path / "current"
    declared.mkdir()
    (declared / "records.json").write_text(
        json.dumps({"records": [_declared_record()]}), encoding="utf-8"
    )
    status = tmp_path / "source-status.json"
    status.write_text(
        json.dumps(
            {
                "source_status_version": "0.1",
                "source_id": "github.com/ben-edu/api-cluster-infra",
                "attempted_at": _ts(NOW),
                "status": "COMPLETE",
                "observed_at": _ts(NOW),
                "revision": "abc123",
                "normalized_records": 1,
                "skipped_documents": 0,
                "errors": [],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_declared_records(declared, source_status_path=status)
    report = build_drift_report(_observed_snapshot(), loaded, now=NOW)

    assert loaded["status"] == "AVAILABLE"
    assert report["status"] == "EVALUATED"
    assert report["summary"]["in_sync"] == 1
    assert report["summary"]["drift"] == 0


def test_declared_cluster_mismatch_is_unknown_not_drift():
    declared = _declared_record()
    declared["subject"]["cluster"] = "other-cluster"

    report = build_drift_report(
        _observed_snapshot(),
        {"status": "AVAILABLE", "records": [declared], "errors": []},
        now=NOW,
    )

    assert report["summary"]["drift"] == 0
    assert report["summary"]["unknown"] == 1
    assert report["unknowns"][0]["code"] == "DECLARED_CLUSTER_MISMATCH"
