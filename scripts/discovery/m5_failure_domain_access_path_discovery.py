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
_QEMU_DISK_KEY = re.compile(r"^(?:ide|sata|scsi|virtio)\d+$")
_LXC_DISK_KEY = re.compile(r"^(?:rootfs|mp\d+)$")


def safe_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if _SAFE_ID.fullmatch(value) else None


def storage_id_from_volume(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw or raw == "none":
        return None
    first = raw.split(",", 1)[0].strip()
    if ":" not in first:
        return None
    storage_id = first.split(":", 1)[0].strip()
    return safe_id(storage_id)


def qemu_storage_ids(config: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for key, value in config.items():
        if not isinstance(key, str) or not _QEMU_DISK_KEY.fullmatch(key):
            continue
        if isinstance(value, str) and "media=cdrom" in value.lower():
            continue
        storage_id = storage_id_from_volume(value)
        if storage_id:
            result.add(storage_id)
    return result


def lxc_storage_ids(config: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for key, value in config.items():
        if not isinstance(key, str) or not _LXC_DISK_KEY.fullmatch(key):
            continue
        storage_id = storage_id_from_volume(value)
        if storage_id:
            result.add(storage_id)
    return result


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
    if payload.get("vm_backup_assurance_version") != "0.1":
        print("accepted_source_version_status: UNSUPPORTED")
        return None, False
    if payload.get("mutation_allowed") is not False:
        print("accepted_source_mutation_boundary: REJECTED")
        return None, False
    return payload, True


def accepted_assets(source: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in source.get("assets", []):
        if not isinstance(asset, dict):
            continue
        subject = asset.get("subject", {})
        assurance = asset.get("assurance", {})
        if not isinstance(subject, dict) or not isinstance(assurance, dict):
            continue
        vmid = subject.get("vmid")
        node = safe_id(subject.get("node"))
        guest_type = safe_id(subject.get("guest_type"))
        if isinstance(vmid, bool) or not isinstance(vmid, int) or not node or not guest_type:
            continue

        mechanisms: list[dict[str, Any]] = []
        for mechanism in assurance.get("backup_mechanisms", []):
            if not isinstance(mechanism, dict):
                continue
            if mechanism.get("type") != "PROXMOX_VE_STORAGE_ARCHIVE":
                continue
            if mechanism.get("source_type") != "PROXMOX_VE":
                continue
            if mechanism.get("basis") != ["RECOVERY_POINT_OBSERVED_IN_SOURCE_SCOPE"]:
                continue
            storage_id = safe_id(mechanism.get("storage_id"))
            mechanism_node = safe_id(mechanism.get("node"))
            if not storage_id or not mechanism_node:
                continue
            mechanisms.append({"storage_id": storage_id, "node": mechanism_node})

        recovery_ids = [
            value
            for value in asset.get("source_recovery_point_ids", [])
            if isinstance(value, str) and value
        ]
        if not mechanisms or not recovery_ids:
            continue

        rows.append(
            {
                "vmid": vmid,
                "node": node,
                "guest_type": guest_type.lower(),
                "backup_storage_ids": sorted({m["storage_id"] for m in mechanisms}),
                "backup_nodes": sorted({m["node"] for m in mechanisms}),
            }
        )
    rows.sort(key=lambda row: row["vmid"])
    return rows


def logical_separation_status(
    *,
    subject_node: str,
    backup_nodes: set[str],
    vm_storage_ids: set[str],
    backup_storage_ids: set[str],
    config_observed: bool,
) -> str:
    if not config_observed or not vm_storage_ids or not backup_storage_ids or not backup_nodes:
        return "UNKNOWN"
    same_node = backup_nodes == {subject_node}
    overlap = bool(vm_storage_ids & backup_storage_ids)
    if same_node and overlap:
        return "NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID"
    if same_node:
        return "NOT_SEPARATED_AT_PVE_NODE_LAYER"
    if not overlap:
        return "SEPARATED_AT_OBSERVED_NODE_AND_STORAGE_ID_LAYER"
    return "UNKNOWN"


def main() -> int:
    print("===== M5 FAILURE-DOMAIN ACCESS-PATH DISCOVERY =====")

    print("\n===== ACCEPTED VM ASSURANCE SOURCE =====")
    source, source_ok = load_accepted_source()
    if not source_ok or source is None:
        print("accepted_source_status: FAILED_TO_OBSERVE")
        print("No failure-domain relationship conclusion is allowed.")
        print("No mutation was performed.")
        return 0

    assets = accepted_assets(source)
    print("accepted_assets_with_recovery_point_mechanism:", len(assets))

    print("\n===== BOUNDED LIVE VM STORAGE RELATIONSHIP =====")
    try:
        getter, trust = build_getter_from_env(
            ENV_FILE,
            allow_discovery_credential=True,
            allow_insecure_tls_discovery=True,
        )
    except Exception as exc:
        print("pve_getter_status: FAILED_TO_OBSERVE")
        print("error_class:", type(exc).__name__)
        print("No mutation was performed.")
        return 0

    print("runtime_credential_approved:", trust["runtime_credential_approved"])

    results: list[dict[str, Any]] = []
    for asset in assets:
        vmid = asset["vmid"]
        node = asset["node"]
        guest_type = asset["guest_type"]
        backup_storage_ids = set(asset["backup_storage_ids"])
        backup_nodes = set(asset["backup_nodes"])

        if guest_type in {"qemu", "vm", "virtualmachine"}:
            endpoint = f"/api2/json/nodes/{node}/qemu/{vmid}/config"
            parser = qemu_storage_ids
        elif guest_type in {"lxc", "container"}:
            endpoint = f"/api2/json/nodes/{node}/lxc/{vmid}/config"
            parser = lxc_storage_ids
        else:
            results.append(
                {
                    "vmid": vmid,
                    "node": node,
                    "config_status": "FAILED_TO_OBSERVE",
                    "vm_storage_ids": set(),
                    "backup_storage_ids": backup_storage_ids,
                    "backup_nodes": backup_nodes,
                    "logical_status": "UNKNOWN",
                }
            )
            print(
                f"vmid={vmid} config_status=FAILED_TO_OBSERVE "
                "reason=UNSUPPORTED_GUEST_TYPE logical_access_path_separation=UNKNOWN"
            )
            continue

        status, data, error = getter(endpoint, None)
        config_observed = status == 200 and isinstance(data, dict)
        vm_storage_ids = parser(data) if config_observed else set()
        logical_status = logical_separation_status(
            subject_node=node,
            backup_nodes=backup_nodes,
            vm_storage_ids=vm_storage_ids,
            backup_storage_ids=backup_storage_ids,
            config_observed=config_observed,
        )

        results.append(
            {
                "vmid": vmid,
                "node": node,
                "config_status": "OBSERVED" if config_observed else "FAILED_TO_OBSERVE",
                "vm_storage_ids": vm_storage_ids,
                "backup_storage_ids": backup_storage_ids,
                "backup_nodes": backup_nodes,
                "logical_status": logical_status,
            }
        )

        same_node = backup_nodes == {node}
        overlap = sorted(vm_storage_ids & backup_storage_ids)
        print(
            f"vmid={vmid}"
            f" config_status={'OBSERVED' if config_observed else 'FAILED_TO_OBSERVE'}"
            f" same_pve_node={same_node if config_observed else 'UNKNOWN'}"
            f" vm_storage_ids={','.join(sorted(vm_storage_ids)) if vm_storage_ids else 'NONE_OBSERVED'}"
            f" backup_storage_ids={','.join(sorted(backup_storage_ids)) if backup_storage_ids else 'NONE_OBSERVED'}"
            f" storage_id_overlap={','.join(overlap) if overlap else 'NONE_OBSERVED'}"
            f" logical_access_path_separation={logical_status}"
        )
        if not config_observed and error:
            print(f"vmid={vmid} observation_error_class={error}")

    observed = sum(row["config_status"] == "OBSERVED" for row in results)
    failed = sum(row["config_status"] == "FAILED_TO_OBSERVE" for row in results)
    same_node = sum(
        row["config_status"] == "OBSERVED" and row["backup_nodes"] == {row["node"]}
        for row in results
    )
    overlap = sum(
        row["config_status"] == "OBSERVED"
        and bool(row["vm_storage_ids"] & row["backup_storage_ids"])
        for row in results
    )
    coupled = sum(
        row["logical_status"] == "NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID"
        for row in results
    )
    node_only_coupled = sum(
        row["logical_status"] == "NOT_SEPARATED_AT_PVE_NODE_LAYER"
        for row in results
    )
    logically_separated = sum(
        row["logical_status"] == "SEPARATED_AT_OBSERVED_NODE_AND_STORAGE_ID_LAYER"
        for row in results
    )
    unknown = sum(row["logical_status"] == "UNKNOWN" for row in results)

    print("\n===== SUMMARY =====")
    print("accepted_assets_with_recovery_point_mechanism:", len(results))
    print("live_vm_config_observed:", observed)
    print("live_vm_config_failed_to_observe:", failed)
    print("same_pve_node_observed:", same_node)
    print("storage_id_overlap_observed:", overlap)
    print("not_separated_at_pve_node_and_storage_id:", coupled)
    print("not_separated_at_pve_node_layer_only:", node_only_coupled)
    print("separated_at_observed_node_and_storage_id_layer:", logically_separated)
    print("logical_access_path_separation_unknown:", unknown)
    print("physical_failure_domain_independence_claims: 0")
    print("restore_verification_claims: 0")
    print("unprotected_claims: 0")
    print("rpo_violation_claims: 0")

    print("\n===== INTERPRETATION BOUNDARY =====")
    print(
        "Logical access-path coupling means the accepted recovery-point mechanism and the current VM storage relationship share PVE node and/or storage-ID layers."
    )
    print(
        "It does not establish physical disk, RAID, mount, host, rack, facility, or external-storage topology."
    )
    print(
        "NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID is a logical coupling observation, not a claim that backup data and VM data occupy the same physical medium."
    )
    print("Physical failure-domain independence remains UNKNOWN.")
    print("No restore, retention-effectiveness, RPO, RTO, or protection result is inferred.")

    print("\n===== TRUST BOUNDARY =====")
    print("Only hash-verified accepted VM assurance and GET/read-only PVE VM config metadata were used.")
    print(
        "Raw VM config values, disk volume names, paths, device identifiers, serials, mountpoints, endpoints, credentials, and backup contents were not printed or persisted."
    )
    print("No VM, storage, backup, or infrastructure state was changed.")
    print("No mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
