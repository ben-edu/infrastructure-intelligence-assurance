from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

SOURCE = Path("/tmp/vm-backup-assurance.json")
EXPECTED_SHA256 = "14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a"


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def main() -> int:
    print("===== VM ASSURANCE STORAGE SHAPE PROBE =====")
    if not SOURCE.exists():
        print("source_status: NOT_FOUND")
        return 0

    try:
        raw = SOURCE.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print("source_status: FAILED_TO_READ")
        print("error_class:", type(exc).__name__)
        return 0

    print("hash_match:", digest == EXPECTED_SHA256)
    if digest != EXPECTED_SHA256 or not isinstance(payload, dict):
        print("source_status: NOT_ACCEPTED")
        return 0

    print("source_status: ACCEPTED")
    print("vm_backup_assurance_version:", payload.get("vm_backup_assurance_version", "MISSING"))
    print("mutation_allowed:", payload.get("mutation_allowed", "MISSING"))

    assets = _list(payload.get("assets"))
    print("assets_total:", len(assets))

    assets_with_source_rp_ids = 0
    source_rp_id_count = 0
    assets_with_backup_mechanisms = 0
    mechanism_count = 0
    mechanism_types: Counter[str] = Counter()
    mechanism_basis_shapes: Counter[str] = Counter()
    mechanism_storage_id_present = 0
    assets_with_retention_context = 0
    retention_rows = 0
    retention_storage_id_present = 0
    source_scope_rows = 0
    source_scope_storage_id_present = 0

    for asset in assets:
        if not isinstance(asset, dict):
            continue

        rp_ids = [value for value in _list(asset.get("source_recovery_point_ids")) if isinstance(value, str) and value]
        if rp_ids:
            assets_with_source_rp_ids += 1
            source_rp_id_count += len(rp_ids)

        assurance = asset.get("assurance")
        if not isinstance(assurance, dict):
            assurance = {}

        mechanisms = [item for item in _list(assurance.get("backup_mechanisms")) if isinstance(item, dict)]
        if mechanisms:
            assets_with_backup_mechanisms += 1
            mechanism_count += len(mechanisms)
        for item in mechanisms:
            mechanism_types[str(item.get("type", "MISSING"))] += 1
            basis = item.get("basis")
            if isinstance(basis, list):
                mechanism_basis_shapes["|".join(str(v) for v in basis)] += 1
            else:
                mechanism_basis_shapes["MISSING_OR_NONLIST"] += 1
            if isinstance(item.get("storage_id"), str) and item.get("storage_id"):
                mechanism_storage_id_present += 1

        retention = [item for item in _list(assurance.get("retention_context")) if isinstance(item, dict)]
        if retention:
            assets_with_retention_context += 1
            retention_rows += len(retention)
        for item in retention:
            if isinstance(item.get("storage_id"), str) and item.get("storage_id"):
                retention_storage_id_present += 1

        source_context = asset.get("source_context")
        if isinstance(source_context, dict):
            scopes = [item for item in _list(source_context.get("selected_storage_scopes")) if isinstance(item, dict)]
            source_scope_rows += len(scopes)
            for item in scopes:
                if isinstance(item.get("storage_id"), str) and item.get("storage_id"):
                    source_scope_storage_id_present += 1

    print("assets_with_source_recovery_point_ids:", assets_with_source_rp_ids)
    print("source_recovery_point_id_count:", source_rp_id_count)
    print("assets_with_backup_mechanisms:", assets_with_backup_mechanisms)
    print("backup_mechanism_rows:", mechanism_count)
    print("backup_mechanism_storage_id_present:", mechanism_storage_id_present)
    print("backup_mechanism_types:", ",".join(f"{k}={v}" for k, v in sorted(mechanism_types.items())) or "NONE")
    print("backup_mechanism_basis_shapes:", ",".join(f"{k}={v}" for k, v in sorted(mechanism_basis_shapes.items())) or "NONE")
    print("assets_with_retention_context:", assets_with_retention_context)
    print("retention_context_rows:", retention_rows)
    print("retention_context_storage_id_present:", retention_storage_id_present)
    print("selected_storage_scope_rows:", source_scope_rows)
    print("selected_storage_scope_storage_id_present:", source_scope_storage_id_present)

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only accepted artifact structure, field presence, enum-like type/basis values, and counts were printed.")
    print("No recovery-point IDs, storage IDs, task IDs, timestamps, paths, endpoints, credentials, or backup contents were printed.")
    print("No mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
