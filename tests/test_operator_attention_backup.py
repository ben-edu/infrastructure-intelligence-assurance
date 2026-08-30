from __future__ import annotations

from datetime import datetime, timezone

import pytest

from infra_assurance.operator_attention_backup import build_operator_attention_with_backup


def _inputs():
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
        "required_live_verification": [
            {"question": "Verify current workload state.", "reason": "Pre-change verification required."}
        ],
    }
    change_context = {
        "task": {"scope": {"cluster": "k3s-main"}},
        "recent_changes": [],
        "unknowns": [],
        "required_live_verification": [],
    }
    required = [
        ("OBSERVE_BACKUP_MECHANISM", "BACKUP_MECHANISM"),
        ("OBSERVE_LAST_SUCCESSFUL_BACKUP", "LAST_SUCCESSFUL_BACKUP"),
        ("OBSERVE_BACKUP_RETENTION", "BACKUP_RETENTION"),
        ("OBSERVE_BACKUP_FAILURE_DOMAIN", "BACKUP_FAILURE_DOMAIN"),
        ("OBSERVE_BACKUP_INTEGRITY_VERIFICATION", "BACKUP_INTEGRITY_VERIFICATION"),
        ("OBSERVE_RESTORE_TEST", "RESTORE_TEST"),
        ("OBSERVE_RPO_TARGET_AND_RESULT", "RPO_TARGET_AND_RESULT"),
        ("OBSERVE_RTO_TARGET_AND_RESULT", "RTO_TARGET_AND_RESULT"),
    ]
    backup = {
        "cluster_id": "k3s-main",
        "source_status": {"overall": "COMPLETE"},
        "summary": {
            "assets_total": 2,
            "assets_stale": 0,
            "assets_freshness_unknown": 0,
            "protection_unknown": 2,
            "restore_verification_unknown": 2,
            "unprotected_claims": 0,
            "authoritative_backup_sources_integrated": 0,
        },
        "assets": [
            {
                "subject": {"name": "secret-pvc-name"},
                "required_evidence": [
                    {
                        "code": code,
                        "target": target,
                        "check": f"Check {target} from the authoritative backup system.",
                        "authoritative_source_required": True,
                    }
                    for code, target in required
                ],
            }
        ],
    }
    return inventory, context, change_context, backup


def test_combines_kubernetes_and_backup_attention_without_per_asset_details():
    inventory, context, change_context, backup = _inputs()
    result = build_operator_attention_with_backup(
        inventory,
        context,
        change_context,
        backup,
        now=datetime(2026, 8, 29, 16, 30, tzinfo=timezone.utc),
    )

    assert result["scope"] == "KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY"
    assert result["mutation_allowed"] is False
    assert result["source_artifacts"] == [
        "inventory.json",
        "context.json",
        "change-context.json",
        "backup-assurance.json",
    ]
    assert result["summary"]["attention_now_total"] == 4
    assert result["summary"]["required_live_verification_total"] == 9
    assert result["summary"]["backup_assets_total"] == 2
    assert result["summary"]["backup_protection_unknown"] == 2
    assert result["summary"]["backup_restore_verification_unknown"] == 2
    assert result["summary"]["backup_unprotected_claims"] == 0
    assert "secret-pvc-name" not in repr(result)


def test_preserves_unknown_not_unprotected_semantics():
    inventory, context, change_context, backup = _inputs()
    result = build_operator_attention_with_backup(inventory, context, change_context, backup)

    backup_codes = {
        item["code"]
        for item in result["attention_now"]
        if item.get("source") == "backup_assurance"
    }
    assert "BACKUP_PROTECTION_UNKNOWN" in backup_codes
    assert "RESTORE_VERIFICATION_UNKNOWN" in backup_codes
    assert "AUTHORITATIVE_BACKUP_SOURCE_NOT_INTEGRATED" in backup_codes
    assert "UNPROTECTED_CLAIMS_OBSERVED" not in backup_codes
    assert result["backup_assurance"]["trust"]["unknown_is_not_unprotected"] is True
    assert result["backup_assurance"]["trust"]["recovery_test_overdue_claimed"] is False


def test_explicit_unprotected_claim_is_projected_only_when_source_reports_it():
    inventory, context, change_context, backup = _inputs()
    backup["summary"]["unprotected_claims"] = 1
    result = build_operator_attention_with_backup(inventory, context, change_context, backup)

    items = [item for item in result["attention_now"] if item.get("code") == "UNPROTECTED_CLAIMS_OBSERVED"]
    assert len(items) == 1
    assert items[0]["severity"] == "RISK"
    assert items[0]["count"] == 1


def test_cluster_mismatch_fails_closed():
    inventory, context, change_context, backup = _inputs()
    backup["cluster_id"] = "other-cluster"

    with pytest.raises(ValueError, match="same cluster"):
        build_operator_attention_with_backup(inventory, context, change_context, backup)


def test_combined_totals_survive_projection_truncation():
    inventory, context, change_context, backup = _inputs()
    result = build_operator_attention_with_backup(
        inventory,
        context,
        change_context,
        backup,
        max_items=2,
    )

    assert result["summary"]["attention_now_total"] == 4
    assert result["summary"]["required_live_verification_total"] == 9
    assert len(result["attention_now"]) == 2
    assert len(result["required_live_verification"]) == 2
    assert result["truncation"]["attention_now_truncated"] is True
    assert result["truncation"]["required_live_verification_truncated"] is True


def test_backup_verification_categories_keep_authoritative_requirement():
    inventory, context, change_context, backup = _inputs()
    result = build_operator_attention_with_backup(inventory, context, change_context, backup)

    backup_required = [
        item
        for item in result["required_live_verification"]
        if item.get("source") == "backup_assurance"
    ]
    assert len(backup_required) == 8
    assert all(item["authoritative_source_required"] is True for item in backup_required)
