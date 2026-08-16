from __future__ import annotations

import argparse
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .io_utils import atomic_write_json, atomic_write_text

PVE_VM_STORAGE_RELATIONSHIP_VERSION = "0.1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")
_QEMU_DISK_KEY = re.compile(r"^(?:ide|sata|scsi|virtio)\d+$")
_LXC_DISK_KEY = re.compile(r"^(?:rootfs|mp\d+)$")
GetJSON = Callable[[str, dict[str, str] | None], tuple[int | None, Any, str | None]]


def _rfc3339_now(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_id(value: Any, *, fallback: str = "") -> str:
    if not isinstance(value, str):
        return fallback
    value = value.strip()
    return value if _SAFE_ID.fullmatch(value) else fallback


def _safe_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _observation(operation: str, status_code: int | None, error_class: str | None) -> dict[str, Any]:
    return {
        "operation": operation,
        "status": "COMPLETE" if status_code == 200 else "FAILED_TO_OBSERVE",
        "http_status": status_code,
        "error_class": error_class,
    }


def _normalize_guests(data: Any) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    if not isinstance(data, list):
        return result
    for raw in data:
        if not isinstance(raw, dict):
            continue
        vmid = _safe_int(raw.get("vmid"))
        guest_type = _safe_id(raw.get("type")).upper()
        node = _safe_id(raw.get("node"))
        if vmid is None or guest_type not in {"QEMU", "LXC"} or not node:
            continue
        result[vmid] = {"vmid": vmid, "guest_type": guest_type, "node": node}
    return result


def _node_restrictions(value: Any) -> tuple[str, list[str]]:
    if value is None:
        return "NOT_EXPLICITLY_RETURNED", []
    if not isinstance(value, str):
        return "UNKNOWN", []
    nodes = sorted({_safe_id(part) for part in value.split(",") if _safe_id(part)})
    return ("OBSERVED", nodes) if nodes else ("UNKNOWN", [])


def _normalize_storages(data: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(data, list):
        return result
    for raw in data:
        if not isinstance(raw, dict):
            continue
        storage_id = _safe_id(raw.get("storage"))
        storage_type = _safe_id(raw.get("type"))
        if not storage_id or not storage_type:
            continue
        if raw.get("shared") is True or raw.get("shared") == 1:
            shared = "SHARED"
        elif raw.get("shared") is False or raw.get("shared") == 0:
            shared = "NOT_SHARED"
        else:
            shared = "NOT_EXPLICITLY_RETURNED"
        restriction_status, restrictions = _node_restrictions(raw.get("nodes"))
        content = {
            item
            for item in (_safe_id(part) for part in str(raw.get("content") or "").split(","))
            if item
        }
        result[storage_id] = {
            "storage_id": storage_id,
            "metadata_status": "OBSERVED",
            "storage_type": storage_type,
            "shared_status": shared,
            "node_restrictions_status": restriction_status,
            "node_restrictions": restrictions,
            "images_content_enabled": "images" in content,
            "backup_content_enabled": "backup" in content,
            "disabled": bool(raw.get("disable", 0)),
        }
    return result


def _storage_reference(
    storage_id: str,
    storage_index: dict[str, dict[str, Any]],
    *,
    storage_scope_complete: bool,
) -> dict[str, Any]:
    if storage_id in storage_index:
        return dict(storage_index[storage_id])
    return {
        "storage_id": storage_id,
        "metadata_status": (
            "NOT_OBSERVED_IN_COMPLETE_STORAGE_CONFIG_SCOPE"
            if storage_scope_complete
            else "FAILED_TO_OBSERVE"
        ),
        "storage_type": None,
        "shared_status": "UNKNOWN",
        "node_restrictions_status": "UNKNOWN",
        "node_restrictions": [],
        "images_content_enabled": None,
        "backup_content_enabled": None,
        "disabled": None,
    }


def _disk_values(config: Any, guest_type: str) -> list[str]:
    if not isinstance(config, dict):
        return []
    values: list[str] = []
    for key, value in config.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        if guest_type == "QEMU":
            if not _QEMU_DISK_KEY.fullmatch(key):
                continue
            lowered = value.lower()
            head = value.split(",", 1)[0].strip().lower()
            if "media=cdrom" in lowered or "cloudinit" in lowered or head in {"none", "cdrom"}:
                continue
        elif guest_type == "LXC":
            if not _LXC_DISK_KEY.fullmatch(key):
                continue
        else:
            continue
        values.append(value)
    return values


def _storage_id_from_disk(value: str) -> str | None:
    head = value.split(",", 1)[0].strip()
    if not head or ":" not in head:
        return None
    candidate = head.split(":", 1)[0].strip()
    return candidate if _SAFE_ID.fullmatch(candidate) else None


def _unknown_relationship(
    vmid: int,
    node: str,
    guest_type: str,
    backup_storage_id: str,
    config_status: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "vmid": vmid,
        "node": node,
        "guest_type": guest_type,
        "config_observation_status": config_status,
        "primary_disk_devices_observed": 0,
        "managed_primary_disk_count": 0,
        "direct_or_unresolved_disk_count": 0,
        "primary_storage_ids": [],
        "backup_storage_id": backup_storage_id,
        "relationship_status": (
            "FAILED_TO_OBSERVE" if config_status == "FAILED_TO_OBSERVE" else "UNKNOWN"
        ),
        "reason": reason,
        "basis": [],
    }


def _relationship(
    vmid: int,
    node: str,
    guest_type: str,
    config: Any,
    backup_storage_id: str,
) -> dict[str, Any]:
    values = _disk_values(config, guest_type)
    storage_ids: list[str] = []
    unresolved = 0
    managed = 0
    for value in values:
        storage_id = _storage_id_from_disk(value)
        if storage_id is None:
            unresolved += 1
        else:
            managed += 1
            storage_ids.append(storage_id)
    storage_ids = sorted(set(storage_ids))

    if unresolved or not storage_ids:
        status = "UNKNOWN"
        reason = "UNRESOLVED_OR_NO_MANAGED_PRIMARY_STORAGE"
        basis = ["PVE_GUEST_CONFIG_DISK_DEVICE_PROJECTION"]
    elif all(item == backup_storage_id for item in storage_ids):
        status = "SAME_PVE_STORAGE_ID_AS_BACKUP"
        reason = "ALL_RESOLVED_PRIMARY_STORAGE_IDS_MATCH_BACKUP_STORAGE_ID"
        basis = ["PVE_GUEST_CONFIG_DISK_DEVICE_PROJECTION", "SAME_PVE_STORAGE_IDENTIFIER"]
    elif all(item != backup_storage_id for item in storage_ids):
        status = "DIFFERENT_PVE_STORAGE_ID_FROM_BACKUP"
        reason = "ALL_RESOLVED_PRIMARY_STORAGE_IDS_DIFFER_FROM_BACKUP_STORAGE_ID"
        basis = ["PVE_GUEST_CONFIG_DISK_DEVICE_PROJECTION", "DIFFERENT_PVE_STORAGE_IDENTIFIER"]
    else:
        status = "UNKNOWN"
        reason = "MIXED_PRIMARY_STORAGE_IDS"
        basis = ["PVE_GUEST_CONFIG_DISK_DEVICE_PROJECTION"]

    return {
        "vmid": vmid,
        "node": node,
        "guest_type": guest_type,
        "config_observation_status": "COMPLETE",
        "primary_disk_devices_observed": len(values),
        "managed_primary_disk_count": managed,
        "direct_or_unresolved_disk_count": unresolved,
        "primary_storage_ids": storage_ids,
        "backup_storage_id": backup_storage_id,
        "relationship_status": status,
        "reason": reason,
        "basis": basis,
    }


def build_proxmox_ve_vm_storage_relationship(
    *,
    source_id: str,
    node: str,
    backup_storage_id: str,
    vmids: list[int],
    get_json: GetJSON,
    credential_metadata: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    source_id = _safe_id(source_id)
    node = _safe_id(node)
    backup_storage_id = _safe_id(backup_storage_id)
    safe_vmids = sorted({v for v in vmids if isinstance(v, int) and not isinstance(v, bool) and v > 0})
    if not source_id or not node or not backup_storage_id or not safe_vmids:
        raise ValueError("source_id, node, backup_storage_id, and at least one numeric VMID are required")

    observations: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    def query(operation: str, path: str, params: dict[str, str] | None = None) -> Any:
        status_code, data, error_class = get_json(path, params)
        observation = _observation(operation, status_code, error_class)
        observations.append(observation)
        if observation["status"] != "COMPLETE":
            errors.append({
                "code": "PVE_GET_FAILED",
                "operation": operation,
                "http_status": status_code,
                "error_class": error_class,
            })
        return data if observation["status"] == "COMPLETE" else None

    version_data = query("GET_VERSION", "/api2/json/version")
    guests_data = query("GET_GUEST_RESOURCES", "/api2/json/cluster/resources", {"type": "vm"})
    storage_data = query("GET_STORAGE_CONFIG", "/api2/json/storage")

    pve_identity: dict[str, Any] = {}
    if isinstance(version_data, dict):
        for key in ("version", "release", "repoid"):
            if isinstance(version_data.get(key), (str, int, float, bool)):
                pve_identity[key] = version_data[key]

    guests = _normalize_guests(guests_data)
    storage_index = _normalize_storages(storage_data)
    storage_scope_complete = storage_data is not None
    relationships: list[dict[str, Any]] = []
    referenced_storage_ids = {backup_storage_id}

    for vmid in safe_vmids:
        guest = guests.get(vmid)
        if guest is None:
            relationships.append(_unknown_relationship(
                vmid, node, "UNKNOWN", backup_storage_id, "NOT_ATTEMPTED",
                "VM_NOT_OBSERVED_IN_CURRENT_GUEST_INVENTORY",
            ))
            continue
        guest_type = guest["guest_type"]
        guest_node = guest["node"]
        if guest_node != node:
            relationships.append(_unknown_relationship(
                vmid, guest_node, guest_type, backup_storage_id, "NOT_ATTEMPTED",
                "VM_OBSERVED_ON_DIFFERENT_NODE",
            ))
            continue
        config_path = (
            f"/api2/json/nodes/{node}/qemu/{vmid}/config"
            if guest_type == "QEMU"
            else f"/api2/json/nodes/{node}/lxc/{vmid}/config"
        )
        config = query(f"GET_VM_CONFIG:{vmid}", config_path)
        if config is None:
            relationships.append(_unknown_relationship(
                vmid, node, guest_type, backup_storage_id, "FAILED_TO_OBSERVE",
                "VM_CONFIG_FAILED_TO_OBSERVE",
            ))
            continue
        item = _relationship(vmid, node, guest_type, config, backup_storage_id)
        referenced_storage_ids.update(item["primary_storage_ids"])
        relationships.append(item)

    storage_references = [
        _storage_reference(storage_id, storage_index, storage_scope_complete=storage_scope_complete)
        for storage_id in sorted(referenced_storage_ids)
    ]

    if not observations or observations[0]["status"] != "COMPLETE":
        overall = "FAILED_TO_OBSERVE"
    elif all(item["status"] == "COMPLETE" for item in observations):
        overall = "COMPLETE"
    else:
        overall = "PARTIAL"

    counts = Counter(item["relationship_status"] for item in relationships)
    unknowns = [
        {
            "code": "PHYSICAL_FAILURE_DOMAIN_NOT_ESTABLISHED",
            "subject": None,
            "statement": "Matching or differing PVE storage identifiers do not establish physical disk, host, controller, power, or hardware failure-domain separation.",
        },
        {
            "code": "FAILURE_DOMAIN_ASSURANCE_NOT_PROMOTED",
            "subject": None,
            "statement": "This source artifact records bounded storage relationships only. VM BACKUP_FAILURE_DOMAIN assurance remains unchanged until separate accepted evidence supports promotion.",
        },
    ]
    not_explicit = [
        item["storage_id"] for item in storage_references
        if item["shared_status"] == "NOT_EXPLICITLY_RETURNED"
    ]
    if not_explicit:
        unknowns.append({
            "code": "STORAGE_SHARED_STATUS_NOT_EXPLICITLY_RETURNED",
            "subject": ",".join(not_explicit),
            "statement": "Authoritative storage metadata did not explicitly return shared status for these storage IDs; node-locality is not inferred from storage name or type.",
        })

    return {
        "pve_vm_storage_relationship_version": PVE_VM_STORAGE_RELATIONSHIP_VERSION,
        "generated_at": _rfc3339_now(now),
        "mutation_allowed": False,
        "source": {
            "type": "proxmox_ve_api",
            "source_id": source_id,
            "node": node,
            "operation": "BOUNDED_HTTP_GET_VM_STORAGE_RELATIONSHIP",
            "status": overall,
            "collector": "infra_assurance.proxmox_ve_vm_storage_relationship",
            "collector_version": PVE_VM_STORAGE_RELATIONSHIP_VERSION,
            "credential_runtime_approved": bool(credential_metadata.get("runtime_credential_approved", False)),
            "credential_file_mode_secure": bool(credential_metadata.get("credential_file_mode_secure", False)),
            "tls_verification": bool(credential_metadata.get("tls_verification", False)),
            "discovery_override_used": bool(credential_metadata.get("discovery_override_used", False)),
        },
        "scope": {
            "target_vmids": safe_vmids,
            "backup_storage_id": backup_storage_id,
            "disk_device_scope": "GUEST_DATA_DISK_DEVICES_ONLY",
        },
        "pve_identity": pve_identity,
        "observations": observations,
        "storage_references": storage_references,
        "vm_storage_relationships": relationships,
        "summary": {
            "target_vms": len(safe_vmids),
            "config_complete": sum(item["config_observation_status"] == "COMPLETE" for item in relationships),
            "same_pve_storage_id_as_backup": counts["SAME_PVE_STORAGE_ID_AS_BACKUP"],
            "different_pve_storage_id_from_backup": counts["DIFFERENT_PVE_STORAGE_ID_FROM_BACKUP"],
            "unknown": counts["UNKNOWN"],
            "failed_to_observe": counts["FAILED_TO_OBSERVE"],
            "direct_or_unresolved_disks": sum(item["direct_or_unresolved_disk_count"] for item in relationships),
            "referenced_storage_ids": len(storage_references),
        },
        "unknowns": unknowns,
        "errors": errors,
        "caveats": [
            "Same PVE storage identifier is a bounded source relationship, not proof of the same physical disk or hardware failure domain.",
            "Different PVE storage identifiers are not proof of independent failure domains.",
            "Storage name or type is not interpreted as node-local or shared unless authoritative metadata explicitly states it.",
            "Raw VM config, disk strings, volume IDs, paths, serials, cloud-init content, network values, MAC/IP data, snippets, and credentials are not persisted.",
            "This collector does not modify VM Backup Assurance or promote BACKUP_FAILURE_DOMAIN.",
        ],
    }


def render_proxmox_ve_vm_storage_relationship_markdown(artifact: dict[str, Any]) -> str:
    source = artifact["source"]
    lines = [
        "# Proxmox VE VM Storage Relationship Evidence",
        "",
        f"Generated: `{artifact['generated_at']}`",
        f"Source: `{source['source_id']}`",
        f"Node: `{source['node']}`",
        f"Source status: `{source['status']}`",
        f"Mutation allowed: `{str(artifact['mutation_allowed']).lower()}`",
        f"Runtime credential approved: `{str(source['credential_runtime_approved']).lower()}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in artifact["summary"].items():
        lines.append(f"- {key}: {value}")
    lines += ["", "## VM storage relationships", ""]
    for item in artifact["vm_storage_relationships"]:
        primary = ",".join(item["primary_storage_ids"]) or "unknown"
        lines.append(
            f"- VMID {item['vmid']} status={item['relationship_status']} "
            f"primary_storage_ids={primary} backup_storage_id={item['backup_storage_id']} "
            f"unresolved_disks={item['direct_or_unresolved_disk_count']}"
        )
    lines += ["", "## Storage metadata projection", ""]
    for item in artifact["storage_references"]:
        lines.append(
            f"- {item['storage_id']} metadata={item['metadata_status']} "
            f"type={item['storage_type'] or 'unknown'} shared={item['shared_status']} "
            f"node_restrictions={','.join(item['node_restrictions']) or 'none returned'}"
        )
    lines += [
        "", "## Trust boundary", "",
        "Storage-ID equality is source evidence only. It does not prove the same physical disk or hardware failure domain.",
        "Storage-ID difference does not prove failure-domain separation.",
        "BACKUP_FAILURE_DOMAIN remains unchanged until separate accepted evidence supports promotion.",
        "",
    ]
    return "\n".join(lines)


def _parse_vmids(value: str) -> list[int]:
    result: list[int] = []
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        if not item.isdigit() or int(item) <= 0:
            raise argparse.ArgumentTypeError("VMIDs must be positive comma-separated integers")
        result.append(int(item))
    if not result:
        raise argparse.ArgumentTypeError("at least one VMID is required")
    return result


def main() -> int:
    from .proxmox_ve_backup_evidence import build_getter_from_env

    parser = argparse.ArgumentParser(description="Collect bounded read-only Proxmox VE VM primary-storage relationship evidence.")
    parser.add_argument("--credential-env-file", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--backup-storage-id", required=True)
    parser.add_argument("--vmids", required=True, type=_parse_vmids)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path, required=True)
    parser.add_argument("--allow-discovery-credential", action="store_true")
    parser.add_argument("--allow-insecure-tls-discovery", action="store_true")
    args = parser.parse_args()

    getter, credential_metadata = build_getter_from_env(
        args.credential_env_file,
        allow_discovery_credential=args.allow_discovery_credential,
        allow_insecure_tls_discovery=args.allow_insecure_tls_discovery,
    )
    artifact = build_proxmox_ve_vm_storage_relationship(
        source_id=args.source_id,
        node=args.node,
        backup_storage_id=args.backup_storage_id,
        vmids=args.vmids,
        get_json=getter,
        credential_metadata=credential_metadata,
    )
    atomic_write_json(args.out, artifact)
    atomic_write_text(args.summary_out, render_proxmox_ve_vm_storage_relationship_markdown(artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
