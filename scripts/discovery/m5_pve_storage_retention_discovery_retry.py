from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BASE_SCRIPT = ROOT / "scripts/discovery/m5_pve_storage_retention_discovery.py"


def load_base_module():
    spec = importlib.util.spec_from_file_location("m5_pve_storage_retention_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load base storage-retention discovery")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def accepted_recovery_point_storage_ids_from_vm_assurance(
    source: dict[str, Any],
) -> set[str]:
    """Extract accepted recovery-point storage targets from VM Backup Assurance v0.1.

    The accepted artifact preserves source recovery-point ownership on each asset and
    authoritative PVE storage mechanism evidence under assurance.backup_mechanisms.
    A storage is accepted here only when the asset has at least one source recovery-point
    ID and the mechanism is explicitly the PVE storage archive mechanism derived from an
    observed recovery point.
    """
    if source.get("vm_backup_assurance_version") != "0.1":
        return set()
    if source.get("mutation_allowed") is not False:
        return set()

    result: set[str] = set()
    for asset in source.get("assets", []):
        if not isinstance(asset, dict):
            continue

        recovery_point_ids = {
            value
            for value in asset.get("source_recovery_point_ids", [])
            if isinstance(value, str) and value
        }
        if not recovery_point_ids:
            continue

        assurance = asset.get("assurance", {})
        if not isinstance(assurance, dict):
            continue

        for mechanism in assurance.get("backup_mechanisms", []):
            if not isinstance(mechanism, dict):
                continue
            if mechanism.get("type") != "PROXMOX_VE_STORAGE_ARCHIVE":
                continue
            if mechanism.get("source_type") != "PROXMOX_VE":
                continue
            if mechanism.get("basis") != ["RECOVERY_POINT_OBSERVED_IN_SOURCE_SCOPE"]:
                continue

            storage_id = mechanism.get("storage_id")
            if isinstance(storage_id, str):
                storage_id = storage_id.strip()
                if storage_id and len(storage_id) <= 200:
                    result.add(storage_id)

    return result


def main() -> int:
    module = load_base_module()
    module.accepted_recovery_point_storage_ids = (
        accepted_recovery_point_storage_ids_from_vm_assurance
    )
    print("retry_basis: VM_BACKUP_ASSURANCE_V0.1_PRESERVED_RECOVERY_POINT_STORAGE_MECHANISM")
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
