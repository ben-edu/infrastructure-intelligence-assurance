from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from infra_assurance.operator_attention import (
    build_operator_attention_summary,
    load_json_artifact,
)


def _inputs():
    inventory = {
        "cluster_id": "k3s-main",
        "summary": {"workloads_total": 3, "workloads_with_attention": 1},
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
                        "field_mismatches": ["private-field"],
                    }
                ]
            }
        ],
    }
    context = {
        "task": {"scope": {"cluster": "k3s-main"}},
        "unknowns": [{"subject": "Node/node-1", "reason": "Latest collection attempt failed."}],
        "observation_failures": [
            {"subject": "Node/node-1", "evidence_id": "ev-2", "error_codes": ["READ_FAILED"]}
        ],
        "inferences": [
            {"statement": "Deployment/default/api has fewer ready replicas than desired.", "evidence_ids": ["ev-3"]}
        ],
        "required_live_verification": [
            {"question": "Can Node/node-1 be observed successfully now?", "reason": "Current state is unknown."}
        ],
    }
    change_context = {
        "task": {"scope": {"cluster": "k3s-main"}},
        "recent_changes": [
            {"classification": "MODIFIED", "subject": "Deployment/default/api", "evidence_ids": ["ev-4"]}
        ],
        "unknowns": [
            {"code": "UNSAFE_COMPARISON", "statement": "Comparison is unsafe.", "evidence_ids": ["ev-5"]}
        ],
        "required_live_verification": [
            {"code": "VERIFY_LIVE", "check": "Verify the live workload state before action."}
        ],
    }
    return inventory, context, change_context


def test_builds_four_operator_sections_from_existing_artifacts_only():
    inventory, context, change_context = _inputs()
    result = build_operator_attention_summary(
        inventory,
        context,
        change_context,
        now=datetime(2026, 8, 29, 15, 30, tzinfo=timezone.utc),
    )

    assert result["cluster_id"] == "k3s-main"
    assert result["mutation_allowed"] is False
    assert result["scope"] == "KUBERNETES_EXISTING_EVIDENCE_ONLY"
    assert result["summary"] == {
        "workloads_total": 3,
        "workloads_with_attention": 1,
        "attention_now_total": 3,
        "recent_changes_total": 1,
        "unknowns_total": 2,
        "required_live_verification_total": 2,
    }
    assert result["source_artifacts"] == ["inventory.json", "context.json", "change-context.json"]


def test_projection_does_not_retain_unallowlisted_attention_details():
    inventory, context, change_context = _inputs()
    result = build_operator_attention_summary(inventory, context, change_context)

    rendered = repr(result)
    assert "private-field" not in rendered
    assert "error_codes" not in rendered
    assert result["attention_now"][0]["evidence_ids"] == ["ev-1"]


def test_cluster_mismatch_fails_closed():
    inventory, context, change_context = _inputs()
    change_context["task"]["scope"]["cluster"] = "other-cluster"

    with pytest.raises(ValueError, match="matching cluster"):
        build_operator_attention_summary(inventory, context, change_context)


def test_sections_are_deduplicated_and_truncated():
    inventory, context, change_context = _inputs()
    inventory["entities"][0]["attention"] *= 3
    change_context["recent_changes"] *= 3

    result = build_operator_attention_summary(
        inventory,
        context,
        change_context,
        max_items=1,
    )

    assert result["summary"]["attention_now_total"] == 3
    assert result["summary"]["recent_changes_total"] == 1
    assert len(result["attention_now"]) == 1
    assert len(result["recent_changes"]) == 1
    assert result["truncation"]["attention_now_truncated"] is True
    assert result["truncation"]["recent_changes_truncated"] is False


def test_json_loader_rejects_symlinks_and_non_object_payload(tmp_path: Path):
    real = tmp_path / "real.json"
    real.write_text(json.dumps({"ok": True}), encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(real)

    with pytest.raises(ValueError, match="symlink"):
        load_json_artifact(link)

    scalar = tmp_path / "scalar.json"
    scalar.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="top-level shape"):
        load_json_artifact(scalar)
