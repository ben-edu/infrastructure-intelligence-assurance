from __future__ import annotations

import json

from infra_assurance import inventory_cli


def sample_inventory():
    return {
        "inventory_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T10:00:00Z",
        "mutation_allowed": False,
        "scope": {
            "entity_type": "KUBERNETES_WORKLOAD",
            "workload_kinds": ["DaemonSet", "Deployment", "StatefulSet"],
        },
        "summary": {
            "workloads_total": 1,
            "namespaces_total": 1,
            "declared_workloads": 1,
            "workloads_in_sync": 1,
            "workloads_outside_declared_scope": 0,
            "workloads_with_attention": 1,
            "workloads_changed_in_latest_diff": 0,
            "service_links": 1,
            "ingress_route_candidates": 1,
            "pvc_links": 0,
            "related_drift_subjects": 1,
        },
        "namespace_counts": {"validation": 1},
        "entities": [
            {
                "entity_id": "kubernetes:k3s-main:apps:Deployment:validation:nginx-validation",
                "entity_type": "KUBERNETES_WORKLOAD",
                "subject": {
                    "system": "kubernetes",
                    "cluster": "k3s-main",
                    "api_group": "apps",
                    "kind": "Deployment",
                    "namespace": "validation",
                    "name": "nginx-validation",
                },
                "observed": {},
                "declared": {"coverage": "DECLARED", "comparison": "IN_SYNC"},
                "relationships": {},
                "recent_change": {"state": "UNCHANGED", "items": []},
                "attention": [{"code": "RELATED_DRIFT"}],
                "evidence_ids": ["ev-workload"],
            }
        ],
    }


def test_summary_reads_artifact_only(tmp_path, monkeypatch, capsys):
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(sample_inventory()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["iia-inventory", "--inventory", str(path), "summary"],
    )
    assert inventory_cli.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mutation_allowed"] is False
    assert output["summary"]["workloads_total"] == 1


def test_attention_only_list(tmp_path, monkeypatch, capsys):
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(sample_inventory()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["iia-inventory", "--inventory", str(path), "list", "--attention-only"],
    )
    assert inventory_cli.main() == 0
    output = capsys.readouterr().out
    assert "Deployment/validation/nginx-validation" in output
    assert "attention=1" in output


def test_exact_show_returns_projected_entity(tmp_path, monkeypatch, capsys):
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(sample_inventory()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "iia-inventory",
            "--inventory",
            str(path),
            "show",
            "--namespace",
            "validation",
            "--kind",
            "Deployment",
            "--name",
            "nginx-validation",
        ],
    )
    assert inventory_cli.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["entity_type"] == "KUBERNETES_WORKLOAD"
    assert output["declared"]["comparison"] == "IN_SYNC"
