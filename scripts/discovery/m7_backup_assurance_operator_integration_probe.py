#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from infra_assurance.operator_attention import load_json_artifact
from infra_assurance.operator_attention_backup import build_operator_attention_with_backup

EVIDENCE_DIR = Path("/var/lib/infra-assurance/evidence")


def main() -> int:
    print("===== M7 BACKUP ASSURANCE OPERATOR INTEGRATION PROBE =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("live_infrastructure_query_performed: False")
    print("source_artifacts_written: False")
    print("raw_source_artifacts_projected: False")
    print("backup_asset_details_projected: False")
    print("secrets_or_credentials_projected: False")

    try:
        inventory = load_json_artifact(EVIDENCE_DIR / "inventory.json")
        context = load_json_artifact(EVIDENCE_DIR / "context.json")
        change_context = load_json_artifact(EVIDENCE_DIR / "change-context.json")
        backup = load_json_artifact(EVIDENCE_DIR / "backup-assurance.json")
        result = build_operator_attention_with_backup(
            inventory,
            context,
            change_context,
            backup,
        )
    except Exception as exc:
        print()
        print("===== SOURCE STATUS =====")
        print("source_status: FAILED_TO_OBSERVE")
        print(f"failure_category: {type(exc).__name__}")
        print("No combined operator-attention conclusion is allowed from this failed observation.")
        return 2

    print()
    print("===== SOURCE STATUS =====")
    print("source_status: COMPLETE")
    print("source_artifacts_loaded: 4")
    print(f"cluster_id: {result['cluster_id']}")
    print(f"scope: {result['scope']}")

    summary = result["summary"]
    print()
    print("===== COMBINED OPERATOR SUMMARY =====")
    for key in (
        "workloads_total",
        "workloads_with_attention",
        "attention_now_total",
        "recent_changes_total",
        "unknowns_total",
        "required_live_verification_total",
        "backup_assets_total",
        "backup_protection_unknown",
        "backup_restore_verification_unknown",
        "backup_unprotected_claims",
    ):
        print(f"{key}: {summary.get(key)}")

    print()
    print("===== ATTENTION NOW =====")
    if result["attention_now"]:
        for index, item in enumerate(result["attention_now"], 1):
            parts = [
                f"item={index}",
                f"source={item.get('source')}",
                f"code={item.get('code')}",
                f"severity={item.get('severity')}",
            ]
            if item.get("subject"):
                parts.append(f"subject={item.get('subject')}")
            if item.get("count") is not None:
                parts.append(f"count={item.get('count')}")
            print(" ".join(parts))
    else:
        print("NONE_OBSERVED")

    print()
    print("===== BACKUP VERIFICATION CATEGORIES =====")
    backup_required = [
        item
        for item in result["required_live_verification"]
        if item.get("source") == "backup_assurance"
    ]
    if backup_required:
        for index, item in enumerate(backup_required, 1):
            print(
                f"item={index} code={item.get('code')} target={item.get('target')} "
                f"authoritative_source_required={item.get('authoritative_source_required')}"
            )
    else:
        print("NONE_OBSERVED")

    trust = result["backup_assurance"]["trust"]
    print()
    print("===== TRUST BOUNDARY =====")
    print(f"unknown_is_not_unprotected: {trust.get('unknown_is_not_unprotected')}")
    print(f"recovery_test_overdue_claimed: {trust.get('recovery_test_overdue_claimed')}")
    print(
        "authoritative_backup_evidence_required_for_unprotected: "
        f"{trust.get('authoritative_backup_evidence_required_for_unprotected')}"
    )
    print("Backup gaps are aggregate evidence-routing signals; no per-asset backup details are projected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
