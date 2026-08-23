from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from infra_assurance.proxmox_ve_backup_evidence import build_getter_from_env

ENV_FILE = Path("/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env")

_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")

PBS_TYPES = {"pbs"}
NETWORK_BACKUP_TYPES = {"nfs", "cifs", "cephfs", "glusterfs", "rbd"}
PATH_BASED_TYPES = {"dir"}


def safe_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if _SAFE_ID.fullmatch(value) else None


def content_types(value: Any) -> set[str]:
    if not isinstance(value, str):
        return set()
    result: set[str] = set()
    for item in value.split(","):
        item = item.strip()
        if item and _SAFE_ID.fullmatch(item):
            result.add(item)
    return result


def classify_target_type(storage_type: str) -> str:
    value = storage_type.lower()
    if value in PBS_TYPES:
        return "PBS_LIKE_TARGET"
    if value in NETWORK_BACKUP_TYPES:
        return "NETWORK_STORAGE_LIKE_TARGET"
    if value in PATH_BASED_TYPES:
        return "PATH_BASED_LOCATION_UNKNOWN"
    return "OTHER_STORAGE_TYPE_UNKNOWN"


def safe_storage_projection(item: dict[str, Any]) -> dict[str, Any] | None:
    storage_id = safe_id(item.get("storage"))
    storage_type = safe_id(item.get("type"))
    if not storage_id or not storage_type:
        return None

    contents = content_types(item.get("content"))
    return {
        "storage_id": storage_id,
        "storage_type": storage_type,
        "backup_content_enabled": "backup" in contents,
        "disabled": bool(item.get("disable", 0)),
        "target_classification": classify_target_type(storage_type),
    }


def main() -> int:
    print("===== M5 EXTERNAL BACKUP TARGET DISCOVERY =====")

    print("\n===== AUTHORITATIVE PVE STORAGE CONFIG =====")
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
        print("No external-target conclusion is allowed.")
        print("No mutation was performed.")
        return 0

    print("operation: GET /storage")
    print("http_status:", status if status is not None else "NONE")
    print("runtime_credential_approved:", trust["runtime_credential_approved"])

    if status != 200 or not isinstance(data, list):
        print("storage_config_source_status: FAILED_TO_OBSERVE")
        print("error_class:", error or "UNKNOWN")
        print("No external-target conclusion is allowed.")
        print("No mutation was performed.")
        return 0

    print("storage_config_source_status: COMPLETE")

    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        projection = safe_storage_projection(item)
        if projection is not None:
            rows.append(projection)

    rows.sort(key=lambda row: (row["storage_id"], row["storage_type"]))
    backup_rows = [row for row in rows if row["backup_content_enabled"]]
    enabled_backup_rows = [row for row in backup_rows if not row["disabled"]]

    pbs_rows = [row for row in enabled_backup_rows if row["target_classification"] == "PBS_LIKE_TARGET"]
    network_rows = [row for row in enabled_backup_rows if row["target_classification"] == "NETWORK_STORAGE_LIKE_TARGET"]
    path_rows = [row for row in enabled_backup_rows if row["target_classification"] == "PATH_BASED_LOCATION_UNKNOWN"]
    other_rows = [row for row in enabled_backup_rows if row["target_classification"] == "OTHER_STORAGE_TYPE_UNKNOWN"]

    print("\n===== SAFE BACKUP-CAPABLE TARGET PROJECTION =====")
    if not backup_rows:
        print("backup_capable_targets: NONE_OBSERVED")
    for row in backup_rows:
        print(
            f"storage={row['storage_id']}"
            f" type={row['storage_type']}"
            f" backup_content=True"
            f" disabled={row['disabled']}"
            f" target_classification={row['target_classification']}"
        )

    print("\n===== SUMMARY =====")
    print("storage_config_rows_projected:", len(rows))
    print("backup_capable_targets_total:", len(backup_rows))
    print("enabled_backup_capable_targets:", len(enabled_backup_rows))
    print("pbs_like_enabled_targets:", len(pbs_rows))
    print("network_storage_like_enabled_targets:", len(network_rows))
    print("path_based_location_unknown_enabled_targets:", len(path_rows))
    print("other_storage_type_unknown_enabled_targets:", len(other_rows))
    print("external_target_presence_claims:", len(pbs_rows) + len(network_rows))
    print("failure_domain_independence_claims: 0")
    print("restore_verification_claims: 0")
    print("unprotected_claims: 0")

    if pbs_rows or network_rows:
        print("external_backup_target_status: EXPLICIT_EXTERNAL_LIKE_TARGET_OBSERVED")
    else:
        print("external_backup_target_status: NONE_OBSERVED_IN_BOUNDED_PVE_STORAGE_SCOPE")

    print("\n===== INTERPRETATION BOUNDARY =====")
    print("This discovery classifies only current PVE storage plugin/type metadata for backup-capable targets.")
    print("PBS-like or network-storage-like type is an external-target signal, not proof of physical failure-domain independence.")
    print("A dir/path-based target cannot be classified as local or external from storage type alone.")
    print("NONE_OBSERVED_IN_BOUNDED_PVE_STORAGE_SCOPE is not proof that no external backup system exists elsewhere.")
    print("No restore, retention-effectiveness, RPO, RTO, or protection result is inferred.")

    print("\n===== TRUST BOUNDARY =====")
    print("Only GET/read-only PVE API calls were used.")
    print("Only storage ID, storage type, backup-content capability, disabled state, and derived type classification were projected.")
    print("No server, endpoint, path, mountpoint, portal, datastore connection detail, username, password, token, fingerprint, credential, raw storage object, or backup content was printed.")
    print("No storage, backup, retention, or infrastructure state was changed.")
    print("No mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
