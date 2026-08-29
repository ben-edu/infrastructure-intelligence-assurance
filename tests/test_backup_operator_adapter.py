from __future__ import annotations

from datetime import datetime, timezone

import pytest

from infra_assurance.backup_operator_adapter import build_backup_operator_adapter


def _artifact():
    required = [
        {
            "code": "OBSERVE_BACKUP_MECHANISM",
            "target": "BACKUP_MECHANISM",
            "check": "Identify the authoritative backup mechanism that protects this asset, if any.",
            "authoritative_source_required": True,
        },
        {
            "code": "OBSERVE_RESTORE_TEST",
            "target": "RESTORE_TEST",
            "check": "Observe the latest actual restore test and whether application/data recovery was verified.",
            "authoritative_source_required": True,
        },
    ]
    return {
        "backup_assurance_version": "0.1",
        "cluster_id": "k3s-main",
        "mutation_allowed": False,
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
            {"required_evidence": required, "sensitive": "must-not-project"},
            {"required_evidence": required},
        ],
        "unknowns": [{"statement": "raw unknown detail"}],
    }


def test_projects_compact_unknowns_without_unprotected_overclaim():
    result = build_backup_operator_adapter(
        _artifact(),
        now=datetime(2026, 8, 29, 16, 0, tzinfo=timezone.utc),
    )

    assert result["cluster_id"] == "k3s-main"
    assert result["mutation_allowed"] is False
    assert result["scope"] == "BACKUP_ASSURANCE_EXISTING_EVIDENCE_ONLY"
    assert result["summary"]["protection_unknown"] == 2
    assert result["summary"]["restore_verification_unknown"] == 2
    assert result["summary"]["unprotected_claims"] == 0
    assert result["trust"]["unknown_is_not_unprotected"] is True
    assert result["trust"]["recovery_test_overdue_claimed"] is False
    codes = {item["code"] for item in result["attention"]}
    assert "BACKUP_PROTECTION_UNKNOWN" in codes
    assert "RESTORE_VERIFICATION_UNKNOWN" in codes
    assert "AUTHORITATIVE_BACKUP_SOURCE_NOT_INTEGRATED" in codes
    assert "UNPROTECTED_CLAIMS_OBSERVED" not in codes


def test_required_verification_categories_are_deduplicated_across_assets():
    result = build_backup_operator_adapter(_artifact())
    assert result["summary"]["required_verification_categories_total"] == 2
    assert [item["code"] for item in result["required_live_verification"]] == [
        "OBSERVE_BACKUP_MECHANISM",
        "OBSERVE_RESTORE_TEST",
    ]


def test_unprotected_claim_requires_explicit_source_count():
    artifact = _artifact()
    artifact["summary"]["unprotected_claims"] = 1
    result = build_backup_operator_adapter(artifact)
    claim = [item for item in result["attention"] if item["code"] == "UNPROTECTED_CLAIMS_OBSERVED"]
    assert claim == [
        {
            "source": "backup_assurance",
            "code": "UNPROTECTED_CLAIMS_OBSERVED",
            "severity": "RISK",
            "count": 1,
            "statement": "Authoritative backup-assurance evidence contains one or more unprotected claims.",
        }
    ]


def test_incomplete_source_is_attention_not_absence():
    artifact = _artifact()
    artifact["source_status"]["overall"] = "PARTIAL"
    result = build_backup_operator_adapter(artifact)
    assert result["source_status"] == "PARTIAL"
    assert result["attention"][0]["code"] == "BACKUP_ASSURANCE_SOURCE_INCOMPLETE"


def test_rejects_missing_cluster_or_summary():
    artifact = _artifact()
    artifact.pop("cluster_id")
    with pytest.raises(ValueError, match="identify a cluster"):
        build_backup_operator_adapter(artifact)

    artifact = _artifact()
    artifact.pop("summary")
    with pytest.raises(ValueError, match="summary object"):
        build_backup_operator_adapter(artifact)


def test_projection_does_not_retain_asset_details_or_raw_unknowns():
    result = build_backup_operator_adapter(_artifact())
    rendered = repr(result)
    assert "must-not-project" not in rendered
    assert "raw unknown detail" not in rendered
