from __future__ import annotations

import json

from infra_assurance import inventory_cli


def _inventory() -> dict:
    return {
        "inventory_version": "0.2",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T10:00:00Z",
        "mutation_allowed": False,
        "observability_source_status": "COMPLETE",
        "summary": {
            "workloads_total": 2,
            "workloads_with_operator_monitor_match": 1,
            "workloads_without_operator_monitor_match": 1,
        },
        "entities": [
            {
                "subject": {
                    "kind": "Deployment",
                    "namespace": "monitoring",
                    "name": "covered",
                },
                "declared": {"coverage": "OUTSIDE_DECLARED_SCOPE", "comparison": None},
                "recent_change": {"state": "UNCHANGED"},
                "observability": {"status": "OPERATOR_MONITOR_MATCH"},
                "attention": [],
            },
            {
                "subject": {
                    "kind": "Deployment",
                    "namespace": "validation",
                    "name": "not-covered",
                },
                "declared": {"coverage": "DECLARED", "comparison": "IN_SYNC"},
                "recent_change": {"state": "UNCHANGED"},
                "observability": {"status": "NO_OPERATOR_MONITOR_MATCH"},
                "attention": [],
            },
        ],
    }


def test_list_filters_generated_artifact_by_observability_status(tmp_path, monkeypatch, capsys):
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(_inventory()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "iia-inventory",
            "--inventory",
            str(path),
            "list",
            "--observability-status",
            "OPERATOR_MONITOR_MATCH",
        ],
    )

    assert inventory_cli.main() == 0
    output = capsys.readouterr().out
    assert "Deployment/monitoring/covered" in output
    assert "observability=OPERATOR_MONITOR_MATCH" in output
    assert "not-covered" not in output


def test_summary_exposes_observability_source_status(tmp_path, monkeypatch, capsys):
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(_inventory()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["iia-inventory", "--inventory", str(path), "summary"],
    )

    assert inventory_cli.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["observability_source_status"] == "COMPLETE"
    assert output["summary"]["workloads_with_operator_monitor_match"] == 1
