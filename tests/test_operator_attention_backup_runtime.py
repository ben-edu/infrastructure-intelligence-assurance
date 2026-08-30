from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from infra_assurance.operator_attention_backup import main


def _write_inputs(tmp_path: Path):
    inventory = {
        "cluster_id": "k3s-main",
        "summary": {"workloads_total": 2, "workloads_with_attention": 1},
        "entities": [
            {
                "attention": [
                    {
                        "source": "drift",
                        "code": "DECLARED_OBSERVED_DRIFT",
                        "severity": "DRIFT",
                        "subject": "Deployment/default/api",
                        "statement": "bounded drift signal",
                        "evidence_ids": ["ev-1"],
                    }
                ]
            }
        ],
    }
    context = {
        "task": {"scope": {"cluster": "k3s-main"}},
        "unknowns": [],
        "observation_failures": [],
        "inferences": [],
        "required_live_verification": [],
    }
    change_context = {
        "task": {"scope": {"cluster": "k3s-main"}},
        "recent_changes": [],
        "unknowns": [],
        "required_live_verification": [],
    }
    backup = {
        "cluster_id": "k3s-main",
        "source_status": {"overall": "COMPLETE"},
        "summary": {
            "assets_total": 1,
            "assets_stale": 0,
            "assets_freshness_unknown": 0,
            "protection_unknown": 1,
            "restore_verification_unknown": 1,
            "unprotected_claims": 0,
            "authoritative_backup_sources_integrated": 0,
        },
        "assets": [
            {
                "subject": {"name": "must-not-project-pvc"},
                "required_evidence": [
                    {
                        "code": "OBSERVE_RESTORE_TEST",
                        "target": "RESTORE_TEST",
                        "check": "Observe the latest restore test from the authoritative backup system.",
                        "authoritative_source_required": True,
                    }
                ],
            }
        ],
    }

    paths = {}
    for name, payload in (
        ("inventory", inventory),
        ("context", context),
        ("change", change_context),
        ("backup", backup),
    ):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path
    return paths


def test_cross_domain_runtime_main_writes_safe_json_and_markdown(tmp_path: Path, monkeypatch):
    paths = _write_inputs(tmp_path)
    out = tmp_path / "operator-attention.json"
    markdown_out = tmp_path / "operator-attention.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "operator_attention_backup",
            "--inventory", str(paths["inventory"]),
            "--context", str(paths["context"]),
            "--change-context", str(paths["change"]),
            "--backup-assurance", str(paths["backup"]),
            "--out", str(out),
            "--summary-out", str(markdown_out),
        ],
    )

    assert main() == 0
    artifact = json.loads(out.read_text(encoding="utf-8"))
    markdown = markdown_out.read_text(encoding="utf-8")

    assert artifact["scope"] == "KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY"
    assert artifact["mutation_allowed"] is False
    assert artifact["summary"]["attention_now_total"] == 4
    assert artifact["summary"]["backup_protection_unknown"] == 1
    assert artifact["summary"]["backup_unprotected_claims"] == 0
    assert "must-not-project-pvc" not in repr(artifact)
    assert "must-not-project-pvc" not in markdown
    assert "BACKUP_PROTECTION_UNKNOWN" in markdown
    assert "Backup assets: 1" in markdown
    assert "existing Kubernetes and backup-assurance evidence artifacts only" in markdown


def test_cross_domain_runtime_rejects_non_positive_projection_limit(tmp_path: Path, monkeypatch):
    paths = _write_inputs(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "operator_attention_backup",
            "--inventory", str(paths["inventory"]),
            "--context", str(paths["context"]),
            "--change-context", str(paths["change"]),
            "--backup-assurance", str(paths["backup"]),
            "--out", str(tmp_path / "out.json"),
            "--max-items", "0",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
