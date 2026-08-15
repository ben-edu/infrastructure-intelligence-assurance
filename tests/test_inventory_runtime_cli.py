from __future__ import annotations

import json

from infra_assurance import inventory_cli


def sample_inventory():
    return {
        "inventory_version": "0.3",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T10:00:00Z",
        "mutation_allowed": False,
        "observability_source_status": "COMPLETE",
        "prometheus_runtime_source_status": "COMPLETE",
        "scope": {
            "entity_type": "KUBERNETES_WORKLOAD",
            "workload_kinds": ["DaemonSet", "Deployment", "StatefulSet"],
        },
        "summary": {"workloads_total": 2},
        "namespace_counts": {"app": 2},
        "entities": [
            {
                "entity_id": "one",
                "entity_type": "KUBERNETES_WORKLOAD",
                "subject": {"kind": "Deployment", "namespace": "app", "name": "up"},
                "declared": {},
                "recent_change": {},
                "attention": [],
                "observability": {"status": "OPERATOR_MONITOR_MATCH"},
                "runtime_observability": {"state": "PROMETHEUS_TARGETS_UP"},
            },
            {
                "entity_id": "two",
                "entity_type": "KUBERNETES_WORKLOAD",
                "subject": {"kind": "Deployment", "namespace": "app", "name": "down"},
                "declared": {},
                "recent_change": {},
                "attention": [],
                "observability": {"status": "OPERATOR_MONITOR_MATCH"},
                "runtime_observability": {"state": "PROMETHEUS_TARGET_DOWN"},
            },
        ],
    }


def test_runtime_state_filter_reads_inventory_artifact_only(tmp_path, monkeypatch, capsys):
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(sample_inventory()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "iia-inventory",
            "--inventory",
            str(path),
            "list",
            "--runtime-state",
            "PROMETHEUS_TARGET_DOWN",
        ],
    )
    assert inventory_cli.main() == 0
    output = capsys.readouterr().out
    assert "Deployment/app/down" in output
    assert "Deployment/app/up" not in output
    assert "runtime=PROMETHEUS_TARGET_DOWN" in output


def test_summary_exposes_runtime_source_status(tmp_path, monkeypatch, capsys):
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(sample_inventory()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["iia-inventory", "--inventory", str(path), "summary"],
    )
    assert inventory_cli.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["prometheus_runtime_source_status"] == "COMPLETE"
