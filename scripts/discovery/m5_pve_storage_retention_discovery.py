from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from infra_assurance.proxmox_ve_backup_evidence import build_getter_from_env

ENV_FILE = Path("/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env")
ACCEPTED_SOURCE = Path("/tmp/vm-backup-assurance.json")
EXPECTED_SOURCE_SHA256 = "14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a"

_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")
_SAFE_RETENTION = re.compile(r"^[A-Za-z0-9_=,;:+.\-\s]{1,200}$")


def safe_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if _SAFE_ID.fullmatch(value) else None


def safe_retention(value: Any) -> str | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if _SAFE_RETENTION.fullmatch(value) else None


def content_types(value: Any) -> set[str]:
    if not isinstance(value, str):
        return set()
    return {
        item.strip()
        for item in value.split(",")
        if item.strip() and _SAFE_ID.fullmatch(item.strip())
    }


def load_accepted_source() -> tuple[dict[str, Any] | None, bool]:
    if not ACCEPTED_SOURCE.exists():
        print(f"{ACCEPTED_SOURCE}: NOT_FOUND")
        return None, False
    try:
        raw = ACCEPTED_SOURCE.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        print(f"{ACCEPTED_SOURCE}: FAILED_TO_READ")
        return None, False

    matched = digest == EXPECTED_SOURCE_SHA256
    print(f"{ACCEPTED_SOURCE}: hash_match={matched}")
    if not matched or not isinstance(payload, dict):
        return None, False
    return payload, True


def accepted_recovery_point_storage_ids(source: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for item in source.get("recovery_points", []):
        if not isinstance(item, dict):
            continue
        storage_id = safe_id(item.get("storage_id"))
        if storage_id:
            result.add(storage_id)
    return result


def main() -> int:
    print("===== PVE STORAGE-LEVEL RETENTION DECLARATION DISCOVERY =====")

    print()
    print("===== ACCEPTED RECOVERY-POINT SOURCE VERIFICATION =====")
    source, source_ok = load_accepted_source()
    if not source_ok or source is None:
        print("accepted_source_status: FAILED_TO_OBSERVE")
        print("No retention conclusion is allowed.")
        print("No mutation was performed.")
        return 0

    accepted_storage_ids = accepted_recovery_point_storage_ids(source)
    print("accepted_recovery_point_storage_ids:", len(accepted_storage_ids))
    print(
        "accepted_recovery_point_storage_id_list:",
        ",".join(sorted(accepted_storage_ids)) if accepted_storage_ids else "NONE_OBSERVED",
    )

    print()
    print("===== AUTHORITATIVE PVE STORAGE CONFIG =====")
    try:
        getter, trust = build_getter_from_env(
            ENV_FILE,
            allow_discovery_credential=True,
            allow_insecure_tls_discovery=True,
        )
        status, data, error = getter("/api2/json/storage", None)
    except Exception as exc:
        print("operation: GET /storage")
        print("storage_config_source_status: FAILED_TO_OBSERVE")
        print("error_class:", type(exc).__name__)
        print("No retention conclusion is allowed.")
        print("No mutation was performed.")
        return 0

    print("operation: GET /storage")
    print("http_status:", status if status is not None else "NONE")
    print("runtime_credential_approved:", trust["runtime_credential_approved"])

    if status != 200 or not isinstance(data, list):
        print("storage_config_source_status: FAILED_TO_OBSERVE")
        print("error_class:", error or "UNKNOWN")
        print("No retention conclusion is allowed.")
        print("No mutation was performed.")
        return 0

    print("storage_config_source_status: COMPLETE")

    safe_rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        storage_id = safe_id(item.get("storage"))
        storage_type = safe_id(item.get("type"))
        if not storage_id or not storage_type:
            continue

        contents = content_types(item.get("content"))
        prune = safe_retention(item.get("prune-backups"))
        maxfiles = safe_retention(item.get("maxfiles"))

        safe_rows.append(
            {
                "storage_id": storage_id,
                "storage_type": storage_type,
                "backup_content_enabled": "backup" in contents,
                "disabled": bool(item.get("disable", 0)),
                "prune_backups": prune,
                "legacy_maxfiles": maxfiles,
                "accepted_recovery_point_target": storage_id in accepted_storage_ids,
            }
        )

    safe_rows.sort(key=lambda row: row["storage_id"])

    print()
    print("===== SAFE BACKUP-CAPABLE STORAGE PROJECTION =====")
    backup_rows = [row for row in safe_rows if row["backup_content_enabled"]]
    target_rows = [row for row in safe_rows if row["accepted_recovery_point_target"]]

    for row in backup_rows:
        if row["prune_backups"] is not None:
            retention = f"prune-backups={row['prune_backups']}"
        elif row["legacy_maxfiles"] is not None:
            retention = f"maxfiles={row['legacy_maxfiles']}"
        else:
            retention = "NOT_EXPLICITLY_RETURNED"

        print(
            f"storage={row['storage_id']}"
            f" type={row['storage_type']}"
            f" backup_content=True"
            f" disabled={row['disabled']}"
            f" accepted_recovery_point_target={row['accepted_recovery_point_target']}"
            f" retention={retention}"
        )

    print()
    print("===== ACCEPTED RECOVERY-POINT TARGETS =====")
    if not accepted_storage_ids:
        print("accepted_recovery_point_target_status: UNKNOWN")
    for storage_id in sorted(accepted_storage_ids):
        matches = [row for row in target_rows if row["storage_id"] == storage_id]
        if len(matches) != 1:
            print(
                f"storage={storage_id} config_status=UNKNOWN "
                "retention_declaration=UNKNOWN"
            )
            continue
        row = matches[0]
        if row["prune_backups"] is not None:
            declaration = "PRUNE_BACKUPS_DECLARED"
            value = row["prune_backups"]
        elif row["legacy_maxfiles"] is not None:
            declaration = "LEGACY_MAXFILES_DECLARED"
            value = row["legacy_maxfiles"]
        else:
            declaration = "RETENTION_NOT_EXPLICITLY_RETURNED"
            value = "UNKNOWN"

        print(
            f"storage={storage_id}"
            f" config_status=OBSERVED"
            f" backup_content={row['backup_content_enabled']}"
            f" disabled={row['disabled']}"
            f" retention_declaration={declaration}"
            f" retention_value={value}"
        )

    target_prune = sum(
        row["prune_backups"] is not None for row in target_rows
    )
    target_maxfiles = sum(
        row["prune_backups"] is None and row["legacy_maxfiles"] is not None
        for row in target_rows
    )
    target_no_retention = sum(
        row["prune_backups"] is None and row["legacy_maxfiles"] is None
        for row in target_rows
    )

    print()
    print("===== SUMMARY =====")
    print("storage_config_rows_projected:", len(safe_rows))
    print("backup_capable_storages:", len(backup_rows))
    print("accepted_recovery_point_storage_ids:", len(accepted_storage_ids))
    print("accepted_target_configs_observed:", len(target_rows))
    print("accepted_targets_with_prune_backups_declared:", target_prune)
    print("accepted_targets_with_legacy_maxfiles_declared:", target_maxfiles)
    print("accepted_targets_without_explicit_retention_field:", target_no_retention)
    print("retention_effectiveness_claims: 0")
    print("unprotected_claims: 0")
    print("rpo_violation_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("This source describes current DECLARED PVE storage configuration only.")
    print(
        "An explicit prune-backups or maxfiles value is a retention declaration, not "
        "evidence that pruning executed successfully or that expected recovery points remain."
    )
    print(
        "RETENTION_NOT_EXPLICITLY_RETURNED is bounded field absence in the inspected "
        "authoritative storage configuration, not universal absence of retention behavior."
    )
    print("No protection, retention-effectiveness, restore, RPO, or RTO result is inferred.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only GET/read-only PVE API calls were used.")
    print(
        "No storage paths, mountpoints, endpoints, server addresses, credentials, raw storage "
        "objects, backup contents, VM config, or connection strings were printed."
    )
    print("No storage, retention, backup, schedule, or infrastructure state was changed.")
    print("No mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
