from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from infra_assurance.proxmox_ve_backup_evidence import build_getter_from_env
from infra_assurance.vm_last_successful_backup_integration import (
    build_vm_last_successful_backup_integration,
)

ENV_FILE = Path(
    "/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env"
)
LOCAL_DMI_UUID = Path("/sys/class/dmi/id/product_uuid")
VM_SOURCE = Path("/tmp/vm-backup-assurance.json")
TASK_SOURCE = Path("/tmp/proxmox-ve-backup-task-results.json")

EXPECTED_HASHES = {
    VM_SOURCE: "14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a",
    TASK_SOURCE: "18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de",
}


def _parse_smbios_uuid(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.search(
        r"(?:^|,)uuid=([0-9a-fA-F-]{32,36})(?:,|$)",
        value,
    )
    if not match:
        return None
    return match.group(1).lower()


def _read_local_uuid() -> str | None:
    try:
        value = LOCAL_DMI_UUID.read_text(encoding="utf-8").strip().lower()
    except (OSError, UnicodeError):
        return None
    return value or None


def _verify_accepted_sources() -> tuple[bool, dict[Path, dict[str, Any]]]:
    objects: dict[Path, dict[str, Any]] = {}
    all_ok = True

    print()
    print("===== ACCEPTED VM SOURCE VERIFICATION =====")

    for path, expected in EXPECTED_HASHES.items():
        if not path.exists():
            print(f"{path}: NOT_FOUND")
            all_ok = False
            continue

        try:
            raw = path.read_bytes()
            actual = hashlib.sha256(raw).hexdigest()
            payload = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            print(f"{path}: FAILED_TO_READ")
            all_ok = False
            continue

        match = actual == expected
        print(f"{path}: hash_match={match}")
        if not match:
            all_ok = False
            continue

        objects[path] = payload

    return all_ok, objects


def _trust_boundary() -> None:
    print()
    print("===== TRUST BOUNDARY =====")
    print(
        "DMI/SMBIOS UUID values were compared in memory only and were not printed."
    )
    print(
        "Only GET requests were used against PVE; raw VM config was not persisted or printed."
    )
    print("No PostgreSQL connection or database read was performed.")
    print(
        "No disk, network, credential, Secret, connection string, or backup content was printed."
    )
    print("No mutation was performed.")


def main() -> int:
    print("===== MANAGEMENT-HOST PVE UUID RETRY =====")
    print("effective_uid:", os.geteuid())

    if os.geteuid() != 0:
        print("retry_status: NOT_RUN")
        print("reason: ROOT_REQUIRED_FOR_BOUNDED_LOCAL_DMI_UUID_READ")
        _trust_boundary()
        return 0

    local_uuid = _read_local_uuid()
    print("local_dmi_uuid_available:", local_uuid is not None)

    if local_uuid is None:
        print("infrastructure_identity_status: UNKNOWN")
        print("identity_reason: LOCAL_DMI_UUID_FAILED_TO_OBSERVE_AS_ROOT")
        _trust_boundary()
        return 0

    try:
        getter, trust = build_getter_from_env(
            ENV_FILE,
            allow_discovery_credential=True,
            allow_insecure_tls_discovery=True,
        )
    except Exception as exc:
        print("pve_observation: FAILED_TO_OBSERVE")
        print("error_class:", type(exc).__name__)
        print("infrastructure_identity_status: UNKNOWN")
        _trust_boundary()
        return 0

    status, data, error = getter(
        "/api2/json/cluster/resources",
        {"type": "vm"},
    )

    print()
    print("===== BOUNDED PVE UUID CORRELATION =====")
    print("operation: GET /cluster/resources?type=vm")
    print("http_status:", status if status is not None else "NONE")
    print(
        "runtime_credential_approved:",
        trust["runtime_credential_approved"],
    )

    if status != 200 or not isinstance(data, list):
        print("pve_observation: FAILED_TO_OBSERVE")
        print("error_class:", error or "UNKNOWN")
        print("infrastructure_identity_status: UNKNOWN")
        _trust_boundary()
        return 0

    qemu_guests: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict) or item.get("type") != "qemu":
            continue
        vmid = item.get("vmid")
        node = item.get("node")
        if (
            isinstance(vmid, bool)
            or not isinstance(vmid, int)
            or vmid < 1
            or not isinstance(node, str)
            or not node
        ):
            continue
        qemu_guests.append(item)

    print("bounded_qemu_candidates:", len(qemu_guests))

    config_probes = 0
    config_complete = 0
    explicit_smbios_uuid = 0
    uuid_matches: list[dict[str, Any]] = []

    for item in qemu_guests:
        vmid = item["vmid"]
        node = item["node"]
        config_probes += 1

        config_status, config, _config_error = getter(
            f"/api2/json/nodes/{node}/qemu/{vmid}/config",
            None,
        )

        if config_status != 200 or not isinstance(config, dict):
            continue

        config_complete += 1
        pve_uuid = _parse_smbios_uuid(config.get("smbios1"))
        if pve_uuid is None:
            continue

        explicit_smbios_uuid += 1
        if pve_uuid == local_uuid:
            uuid_matches.append(item)

    print("config_probes:", config_probes)
    print("config_complete:", config_complete)
    print("explicit_smbios_uuid_candidates:", explicit_smbios_uuid)
    print("uuid_matches:", len(uuid_matches))

    if len(uuid_matches) != 1:
        print("infrastructure_identity_status: UNKNOWN")
        if not uuid_matches:
            print("identity_reason: NO_UNIQUE_PVE_SMBIOS_UUID_MATCH")
        else:
            print("identity_reason: MULTIPLE_PVE_SMBIOS_UUID_MATCHES")
        _trust_boundary()
        return 0

    candidate = uuid_matches[0]
    vmid = candidate["vmid"]
    pve_node = candidate["node"]

    print("infrastructure_identity_status: OBSERVED")
    print("identity_basis: LOCAL_DMI_UUID_EQUALS_PVE_SMBIOS_UUID")
    print("candidate_guest:", candidate.get("name") or "UNKNOWN")
    print("candidate_vmid:", vmid)
    print("candidate_pve_node:", pve_node)
    print("candidate_type:", candidate.get("type") or "UNKNOWN")
    print("candidate_runtime_status:", candidate.get("status") or "UNKNOWN")

    sources_ok, source_objects = _verify_accepted_sources()

    print()
    print("===== ACCEPTED VM BACKUP CORRELATION =====")

    if not sources_ok:
        print("vm_assurance_source_status: NOT_ACCEPTED_FOR_DERIVATION")
        print("local_postgresql_infrastructure_recovery_status: UNKNOWN")
        _trust_boundary()
        return 0

    try:
        vm_assurance = build_vm_last_successful_backup_integration(
            source_objects[VM_SOURCE],
            source_objects[TASK_SOURCE],
        )
    except Exception as exc:
        print("vm_assurance_derivation: FAILED")
        print("error_class:", type(exc).__name__)
        print("local_postgresql_infrastructure_recovery_status: UNKNOWN")
        _trust_boundary()
        return 0

    vm_asset = None
    for asset in vm_assurance.get("assets", []):
        if not isinstance(asset, dict):
            continue
        if asset.get("subject", {}).get("vmid") == vmid:
            vm_asset = asset
            break

    if vm_asset is None:
        print("vmid_in_accepted_vm_assurance: False")
        print("local_postgresql_infrastructure_recovery_status: UNKNOWN")
        _trust_boundary()
        return 0

    assurance = vm_asset.get("assurance", {})
    last_status = assurance.get("last_successful_backup_status", "UNKNOWN")
    last_at = assurance.get("last_successful_backup_at") or "UNKNOWN"
    evidence = assurance.get("last_successful_backup_evidence")
    strict_basis = (
        isinstance(evidence, dict)
        and evidence.get("basis") == ["STRICT_SUCCESS_TASK_MATCH"]
    )

    print("vmid_in_accepted_vm_assurance: True")
    print("vm_last_successful_backup_status:", last_status)
    print("vm_last_successful_backup_at:", last_at)
    print("strict_success_task_evidence:", strict_basis)
    print(
        "vm_protection_status:",
        assurance.get("protection_status", "UNKNOWN"),
    )
    print(
        "vm_restore_verification_status:",
        assurance.get("restore_verification_status", "UNKNOWN"),
    )
    print(
        "vm_integrity_verification_status:",
        assurance.get("integrity_verification_status", "UNKNOWN"),
    )
    print("vm_rpo_status:", assurance.get("rpo_status", "UNKNOWN"))
    print("vm_rto_status:", assurance.get("rto_status", "RTO_UNKNOWN"))

    recovery_status = (
        "OBSERVED"
        if last_status == "OBSERVED" and strict_basis
        else "UNKNOWN"
    )
    print(
        "local_postgresql_infrastructure_recovery_status:",
        recovery_status,
    )

    print()
    print("===== INTERPRETATION =====")
    print(
        "OBSERVED infrastructure recovery means host identity -> PVE VMID -> accepted strict VM backup evidence only."
    )
    print(
        "It does not establish PostgreSQL-consistent backup, database restore verification, integrity, retention, RPO, or RTO."
    )
    print(
        "Timestamp age is not classified as stale or an RPO violation without an accepted target."
    )

    _trust_boundary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
