from __future__ import annotations

import hashlib
import json
import re
import socket
import subprocess
from pathlib import Path
from typing import Any

from infra_assurance.proxmox_ve_backup_evidence import build_getter_from_env
from infra_assurance.vm_last_successful_backup_integration import (
    build_vm_last_successful_backup_integration,
)

ENV_FILE = Path(
    "/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env"
)
VM_SOURCE = Path("/tmp/vm-backup-assurance.json")
TASK_SOURCE = Path("/tmp/proxmox-ve-backup-task-results.json")

EXPECTED_HASHES = {
    VM_SOURCE: "14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a",
    TASK_SOURCE: "18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de",
}

POSTGRESQL_UNIT = "postgresql@15-main.service"


def _run(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(args, text=True, capture_output=True)
    return result.returncode, result.stdout.strip()


def _local_hostname() -> str:
    value = socket.gethostname().strip()
    return value or "UNKNOWN"


def _local_virtualization() -> str:
    rc, output = _run(["systemd-detect-virt", "--vm"])
    if rc == 0 and output:
        return output
    if rc == 1:
        return "NONE_DETECTED"
    return "FAILED_TO_OBSERVE"


def _postgresql_service_state() -> tuple[str, str]:
    rc, output = _run(
        [
            "systemctl",
            "show",
            POSTGRESQL_UNIT,
            "--no-pager",
            "-p",
            "ActiveState",
            "-p",
            "SubState",
        ]
    )
    if rc != 0:
        return "FAILED_TO_OBSERVE", "FAILED_TO_OBSERVE"

    values: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value

    return (
        values.get("ActiveState") or "UNKNOWN",
        values.get("SubState") or "UNKNOWN",
    )


def _read_local_dmi_uuid() -> str | None:
    path = Path("/sys/class/dmi/id/product_uuid")
    try:
        value = path.read_text(encoding="utf-8").strip().lower()
    except (OSError, UnicodeError):
        return None
    return value or None


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


def main() -> int:
    print("===== MANAGEMENT-HOST POSTGRESQL INFRASTRUCTURE DISCOVERY =====")

    hostname = _local_hostname()
    short_hostname = hostname.split(".", 1)[0]
    local_uuid = _read_local_dmi_uuid()
    virtualization = _local_virtualization()
    pg_active, pg_sub = _postgresql_service_state()

    print()
    print("===== LOCAL HOST =====")
    print("hostname:", hostname)
    print("virtualization:", virtualization)
    print("dmi_uuid_available:", local_uuid is not None)
    print("postgresql_unit:", POSTGRESQL_UNIT)
    print("postgresql_active_state:", pg_active)
    print("postgresql_sub_state:", pg_sub)

    print()
    print("===== BOUNDED PVE IDENTITY DISCOVERY =====")

    try:
        getter, trust = build_getter_from_env(
            ENV_FILE,
            allow_discovery_credential=True,
            allow_insecure_tls_discovery=True,
        )
    except Exception as exc:  # safe class-only reporting below
        print("pve_observation: FAILED_TO_OBSERVE")
        print("error_class:", type(exc).__name__)
        print("infrastructure_identity_status: UNKNOWN")
        print("No mutation was performed.")
        return 0

    status, data, error = getter(
        "/api2/json/cluster/resources",
        {"type": "vm"},
    )

    print("operation: GET /cluster/resources?type=vm")
    print("http_status:", status if status is not None else "NONE")
    print("runtime_credential_approved:", trust["runtime_credential_approved"])

    if status != 200 or not isinstance(data, list):
        print("pve_observation: FAILED_TO_OBSERVE")
        print("error_class:", error or "UNKNOWN")
        print("infrastructure_identity_status: UNKNOWN")
        print("No mutation was performed.")
        return 0

    candidate_names = {hostname.lower(), short_hostname.lower()}
    matches = [
        item
        for item in data
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and item["name"].lower() in candidate_names
    ]

    print("exact_name_candidates:", len(matches))

    if len(matches) != 1:
        print("infrastructure_identity_status: UNKNOWN")
        print("identity_reason: EXACT_PVE_GUEST_NAME_NOT_UNIQUE_OR_NOT_OBSERVED")
        print()
        print("===== TRUST BOUNDARY =====")
        print("No host-to-PVE VMID relationship was promoted.")
        print("No PostgreSQL connection or database read was performed.")
        print("No raw PVE VM config, DMI UUID, disk, network, or credential value was printed.")
        print("No mutation was performed.")
        return 0

    candidate = matches[0]
    vmid = candidate.get("vmid")
    pve_node = candidate.get("node")
    guest_type = candidate.get("type")
    guest_status = candidate.get("status")
    guest_name = candidate.get("name")

    if (
        isinstance(vmid, bool)
        or not isinstance(vmid, int)
        or vmid < 1
        or not isinstance(pve_node, str)
        or not pve_node
    ):
        print("infrastructure_identity_status: UNKNOWN")
        print("identity_reason: PVE_GUEST_IDENTITY_FIELDS_INCOMPLETE")
        print("No mutation was performed.")
        return 0

    print("candidate_guest:", guest_name)
    print("candidate_vmid:", vmid)
    print("candidate_pve_node:", pve_node)
    print("candidate_type:", guest_type or "UNKNOWN")
    print("candidate_runtime_status:", guest_status or "UNKNOWN")

    identity_status = "UNKNOWN"
    identity_basis = "EXACT_PVE_GUEST_NAME_ONLY"

    if guest_type == "qemu" and local_uuid:
        config_status, config, config_error = getter(
            f"/api2/json/nodes/{pve_node}/qemu/{vmid}/config",
            None,
        )
        print("config_probe_http_status:", config_status if config_status is not None else "NONE")

        if config_status == 200 and isinstance(config, dict):
            pve_uuid = _parse_smbios_uuid(config.get("smbios1"))
            if pve_uuid is not None and pve_uuid == local_uuid:
                identity_status = "OBSERVED"
                identity_basis = "EXACT_GUEST_NAME_AND_SMBIOS_UUID_MATCH"
            elif pve_uuid is None:
                identity_basis = "EXACT_GUEST_NAME_BUT_SMBIOS_UUID_NOT_EXPLICITLY_RETURNED"
            else:
                identity_basis = "EXACT_GUEST_NAME_BUT_SMBIOS_UUID_MISMATCH"
        else:
            print("config_probe_error_class:", config_error or "UNKNOWN")
            identity_basis = "EXACT_GUEST_NAME_BUT_CONFIG_FAILED_TO_OBSERVE"

    print("infrastructure_identity_status:", identity_status)
    print("identity_basis:", identity_basis)

    if identity_status != "OBSERVED":
        print()
        print("===== TRUST BOUNDARY =====")
        print("Exact guest-name similarity alone was not treated as authoritative VM identity.")
        print("The local PostgreSQL infrastructure recovery relationship remains UNKNOWN.")
        print("No PostgreSQL connection or database read was performed.")
        print("No raw PVE VM config, DMI UUID, disk, network, or credential value was printed.")
        print("No mutation was performed.")
        return 0

    sources_ok, source_objects = _verify_accepted_sources()

    print()
    print("===== ACCEPTED VM BACKUP CORRELATION =====")

    if not sources_ok:
        print("vm_assurance_source_status: NOT_ACCEPTED_FOR_DERIVATION")
        print("local_postgresql_infrastructure_recovery_status: UNKNOWN")
        print("No mutation was performed.")
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
        print("No mutation was performed.")
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
        print("No mutation was performed.")
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
    print("vm_protection_status:", assurance.get("protection_status", "UNKNOWN"))
    print("vm_restore_verification_status:", assurance.get("restore_verification_status", "UNKNOWN"))
    print("vm_integrity_verification_status:", assurance.get("integrity_verification_status", "UNKNOWN"))
    print("vm_rpo_status:", assurance.get("rpo_status", "UNKNOWN"))
    print("vm_rto_status:", assurance.get("rto_status", "RTO_UNKNOWN"))

    recovery_status = (
        "OBSERVED"
        if last_status == "OBSERVED" and strict_basis
        else "UNKNOWN"
    )

    print("local_postgresql_infrastructure_recovery_status:", recovery_status)

    print()
    print("===== TRUST BOUNDARY =====")
    print("OBSERVED would mean host identity -> PVE VMID -> accepted strict VM backup evidence only.")
    print("It would not mean PostgreSQL-consistent backup or PostgreSQL restore/integrity assurance.")
    print("Timestamp age is not classified as stale or an RPO violation without an accepted target.")
    print("No PostgreSQL connection or database read was performed.")
    print("No raw PVE VM config, DMI UUID, disk, network, or credential value was printed.")
    print("No mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
