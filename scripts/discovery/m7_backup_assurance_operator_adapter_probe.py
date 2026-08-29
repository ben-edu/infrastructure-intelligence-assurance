from __future__ import annotations

import json
from pathlib import Path

from infra_assurance.backup_operator_adapter import build_backup_operator_adapter
from infra_assurance.operator_attention import load_json_artifact

SOURCE = Path("/var/lib/infra-assurance/evidence/backup-assurance.json")
MAX_PRINTED = 12


def _safe(value: object) -> str:
    if value is None:
        return "-"
    return str(value).replace("\n", " ")[:180]


def main() -> int:
    print("===== M7 BACKUP ASSURANCE OPERATOR ADAPTER PROBE =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("live_infrastructure_query_performed: False")
    print("source_artifact_written: False")
    print("raw_source_artifact_projected: False")
    print("asset_details_projected: False")
    print("secrets_or_credentials_projected: False")

    try:
        artifact = load_json_artifact(SOURCE)
        projection = build_backup_operator_adapter(artifact)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print()
        print("===== SOURCE STATUS =====")
        print("source_status: FAILED_TO_OBSERVE")
        print("failure_category:", type(exc).__name__)
        print("No backup/recovery operator conclusion is allowed from this failed observation.")
        return 2

    summary = projection["summary"]
    print()
    print("===== SOURCE STATUS =====")
    print("source_status: COMPLETE")
    print("backup_assurance_source_status:", projection["source_status"])
    print("cluster_id:", projection["cluster_id"])
    print("scope:", projection["scope"])

    print()
    print("===== COMPACT ASSURANCE SUMMARY =====")
    for key in (
        "assets_total",
        "assets_stale",
        "assets_freshness_unknown",
        "protection_unknown",
        "restore_verification_unknown",
        "unprotected_claims",
        "authoritative_backup_sources_integrated",
        "attention_total",
        "required_verification_categories_total",
    ):
        print(f"{key}:", summary[key])

    print()
    print("===== ATTENTION =====")
    if projection["attention"]:
        for index, item in enumerate(projection["attention"][:MAX_PRINTED], start=1):
            print(
                f"item={index} code={_safe(item.get('code'))} severity={_safe(item.get('severity'))} "
                f"count={_safe(item.get('count'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== REQUIRED VERIFICATION CATEGORIES =====")
    if projection["required_live_verification"]:
        for index, item in enumerate(projection["required_live_verification"][:MAX_PRINTED], start=1):
            print(
                f"item={index} code={_safe(item.get('code'))} target={_safe(item.get('target'))} "
                f"authoritative_source_required={_safe(item.get('authoritative_source_required'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== TRUST BOUNDARY =====")
    print("unknown_is_not_unprotected:", projection["trust"]["unknown_is_not_unprotected"])
    print("recovery_test_overdue_claimed:", projection["trust"]["recovery_test_overdue_claimed"])
    print("authoritative_backup_evidence_required_for_unprotected:", projection["trust"]["authoritative_backup_evidence_required_for_unprotected"])
    print("Only aggregate counts and allowlisted verification categories are projected; asset details are discarded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
