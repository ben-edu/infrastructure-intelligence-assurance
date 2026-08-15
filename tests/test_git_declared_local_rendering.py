import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from infra_assurance.git_declared_observer import (
    _add_documents,
    _load_config,
    _parse_supported_document,
    _render_kustomize_target,
)

NOW = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)


def _source():
    return {
        "id": "github.com/ben-edu/api-cluster-infra",
        "repository": "git@github.com:ben-edu/api-cluster-infra.git",
        "branch": "main",
        "cluster_id": "k3s-main",
        "raw_manifest_paths": ["kubernetes/validation/nginx/nginx-validation.yaml"],
        "kustomize_targets": ["kubernetes/fastapi-platform/overlays/dev"],
        "private_key_file": "/etc/infra-assurance/git/key",
        "public_key_file": "/etc/infra-assurance/git/key.pub",
        "known_hosts_file": "/etc/infra-assurance/git/known_hosts",
    }


def test_local_manifest_parser_does_not_use_kubeconfig(monkeypatch):
    monkeypatch.setenv("KUBECONFIG", "/must/not/be/used")
    manifest = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-validation
  namespace: validation
spec:
  replicas: 1
"""

    def runner(command, **kwargs):
        assert command[:3] == ["kubectl", "patch", "--local"]
        assert "KUBECONFIG" not in kwargs["env"]
        assert "KUBERNETES_MASTER" not in kwargs["env"]
        assert kwargs["input"] == manifest
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {"name": "nginx-validation", "namespace": "validation"},
                    "spec": {"replicas": 1},
                }
            ),
            stderr="",
        )

    parsed, error = _parse_supported_document(manifest, runner=runner)
    assert error is None
    assert parsed["metadata"]["namespace"] == "validation"


def test_kustomize_render_is_local_and_target_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("KUBECONFIG", "/must/not/be/used")
    target = "kubernetes/fastapi-platform/overlays/dev"
    target_dir = tmp_path / target
    target_dir.mkdir(parents=True)
    (target_dir / "kustomization.yaml").write_text("resources: []\n", encoding="utf-8")

    def runner(command, **kwargs):
        assert command == ["kubectl", "kustomize", str(target_dir.resolve())]
        assert "KUBECONFIG" not in kwargs["env"]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="""apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: fastapi-platform-dev
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: fastapi-platform-dev
""",
            stderr="",
        )

    rendered, error = _render_kustomize_target(tmp_path, target, runner=runner)
    assert error is None
    assert "namespace: fastapi-platform-dev" in rendered


def test_sensitive_documents_are_gated_before_local_parser():
    text = """apiVersion: v1
kind: Secret
metadata:
  name: credentials
stringData:
  password: must-never-reach-parser
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: settings
data:
  connection: must-never-reach-parser
"""

    def runner(*args, **kwargs):
        raise AssertionError("sensitive document reached parser")

    records = {}
    errors = []
    skipped = _add_documents(
        text,
        source_ref="sensitive.yaml",
        operation="read",
        source=_source(),
        revision="abc123",
        runner=runner,
        now=NOW,
        ttl_seconds=900,
        records_by_identity=records,
        duplicate_identities=set(),
        errors=errors,
    )

    assert skipped == 2
    assert records == {}
    assert errors == []


def test_config_requires_explicit_raw_and_kustomize_targets(tmp_path):
    config = tmp_path / "git-source.json"
    config.write_text(
        json.dumps({"git_source_version": "0.2", "sources": [_source()]}),
        encoding="utf-8",
    )

    loaded = _load_config(config)
    assert loaded["raw_manifest_paths"] == [
        "kubernetes/validation/nginx/nginx-validation.yaml"
    ]
    assert loaded["kustomize_targets"] == [
        "kubernetes/fastapi-platform/overlays/dev"
    ]


def test_config_rejects_broad_legacy_include_paths(tmp_path):
    source = _source()
    source.pop("raw_manifest_paths")
    source.pop("kustomize_targets")
    source["include_paths"] = ["kubernetes"]
    config = tmp_path / "git-source.json"
    config.write_text(
        json.dumps({"git_source_version": "0.1", "sources": [source]}),
        encoding="utf-8",
    )

    try:
        _load_config(config)
    except ValueError as exc:
        assert "raw_manifest_paths" in str(exc)
    else:
        raise AssertionError("legacy broad include_paths config was accepted")
