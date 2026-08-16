from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

from infra_assurance.proxmox_ve_vm_storage_relationship import (
    build_proxmox_ve_vm_storage_relationship,
    render_proxmox_ve_vm_storage_relationship_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 16, 10, 0, 0, tzinfo=timezone.utc)


def _responses(*, config_101_status=200, storage_status=200, include_9000=True):
    guests = [
        {"vmid": 100, "type": "qemu", "node": "delfan", "name": "private-name"},
        {"vmid": 101, "type": "qemu", "node": "delfan"},
        {"vmid": 102, "type": "lxc", "node": "delfan"},
    ]
    if include_9000:
        guests.append({"vmid": 9000, "type": "qemu", "node": "delfan"})
    return {
        ("/api2/json/version", None): (200, {"version": "9.1.9", "release": "9.1"}, None),
        ("/api2/json/cluster/resources", (("type", "vm"),)): (200, guests, None),
        ("/api2/json/storage", None): (
            storage_status,
            [
                {"storage": "local", "type": "dir", "content": "images,backup", "path": "/var/lib/vz"},
                {"storage": "fast", "type": "lvmthin", "content": "images", "shared": 0, "vgname": "private-vg"},
            ] if storage_status == 200 else None,
            None if storage_status == 200 else "HTTP_ERROR",
        ),
        ("/api2/json/nodes/delfan/qemu/100/config", None): (
            200,
            {
                "scsi0": "local:100/vm-100-disk-0.qcow2,size=20G",
                "ide2": "local:cloudinit",
                "net0": "virtio=AA:BB:CC:DD:EE:FF,ip=192.0.2.10",
                "serial0": "socket",
            },
            None,
        ),
        ("/api2/json/nodes/delfan/qemu/101/config", None): (
            config_101_status,
            {"virtio0": "fast:vm-101-disk-0,size=10G"} if config_101_status == 200 else None,
            None if config_101_status == 200 else "HTTP_ERROR",
        ),
        ("/api2/json/nodes/delfan/lxc/102/config", None): (
            200,
            {
                "rootfs": "local:subvol-102-disk-0,size=8G",
                "mp0": "/srv/private-bind,mp=/data",
                "net0": "name=eth0,bridge=vmbr0,hwaddr=11:22:33:44:55:66",
            },
            None,
        ),
        ("/api2/json/nodes/delfan/qemu/9000/config", None): (
            200,
            {"scsi0": "local:9000/base-9000-disk-0.qcow2"},
            None,
        ),
    }


def _getter(responses):
    def get_json(path, params=None):
        key = (path, tuple(sorted(params.items())) if params else None)
        return responses[key]
    return get_json


def _build(responses=None, vmids=None):
    return build_proxmox_ve_vm_storage_relationship(
        source_id="pve-bm2",
        node="delfan",
        backup_storage_id="local",
        vmids=vmids or [100, 101, 102, 9000],
        get_json=_getter(responses or _responses()),
        credential_metadata={
            "runtime_credential_approved": False,
            "credential_file_mode_secure": False,
            "tls_verification": False,
            "discovery_override_used": True,
        },
        now=NOW,
    )


def test_complete_projection_is_bounded_and_relationships_are_conservative():
    artifact = _build()
    by_vmid = {item["vmid"]: item for item in artifact["vm_storage_relationships"]}

    assert artifact["mutation_allowed"] is False
    assert artifact["source"]["status"] == "COMPLETE"
    assert artifact["source"]["credential_runtime_approved"] is False
    assert by_vmid[100]["relationship_status"] == "SAME_PVE_STORAGE_ID_AS_BACKUP"
    assert by_vmid[101]["relationship_status"] == "DIFFERENT_PVE_STORAGE_ID_FROM_BACKUP"
    assert by_vmid[102]["relationship_status"] == "UNKNOWN"
    assert by_vmid[102]["direct_or_unresolved_disk_count"] == 1
    assert by_vmid[9000]["relationship_status"] == "SAME_PVE_STORAGE_ID_AS_BACKUP"

    storages = {item["storage_id"]: item for item in artifact["storage_references"]}
    assert storages["local"]["shared_status"] == "NOT_EXPLICITLY_RETURNED"
    assert storages["fast"]["shared_status"] == "NOT_SHARED"

    raw = json.dumps(artifact)
    for forbidden in (
        "vm-100-disk-0.qcow2",
        "private-name",
        "/var/lib/vz",
        "private-vg",
        "/srv/private-bind",
        "AA:BB:CC:DD:EE:FF",
        "192.0.2.10",
        "11:22:33:44:55:66",
        "cloudinit",
    ):
        assert forbidden not in raw


def test_failed_config_is_failed_to_observe_not_unknown_absence():
    artifact = _build(_responses(config_101_status=403))
    item = next(row for row in artifact["vm_storage_relationships"] if row["vmid"] == 101)
    assert artifact["source"]["status"] == "PARTIAL"
    assert item["config_observation_status"] == "FAILED_TO_OBSERVE"
    assert item["relationship_status"] == "FAILED_TO_OBSERVE"
    assert item["primary_storage_ids"] == []


def test_missing_target_in_complete_inventory_remains_unknown_without_config_query():
    artifact = _build(_responses(include_9000=False), vmids=[9000])
    item = artifact["vm_storage_relationships"][0]
    assert item["relationship_status"] == "UNKNOWN"
    assert item["config_observation_status"] == "NOT_ATTEMPTED"
    assert item["reason"] == "VM_NOT_OBSERVED_IN_CURRENT_GUEST_INVENTORY"


def test_storage_metadata_failure_does_not_invent_shared_or_local_scope():
    artifact = _build(_responses(storage_status=403), vmids=[100])
    storage = artifact["storage_references"][0]
    assert artifact["source"]["status"] == "PARTIAL"
    assert storage["metadata_status"] == "FAILED_TO_OBSERVE"
    assert storage["shared_status"] == "UNKNOWN"
    assert storage["node_restrictions_status"] == "UNKNOWN"


def test_mixed_primary_storage_ids_remain_unknown():
    responses = _responses()
    responses[("/api2/json/nodes/delfan/qemu/100/config", None)] = (
        200,
        {"scsi0": "local:100/a", "scsi1": "fast:100/b"},
        None,
    )
    artifact = _build(responses, vmids=[100])
    item = artifact["vm_storage_relationships"][0]
    assert item["primary_storage_ids"] == ["fast", "local"]
    assert item["relationship_status"] == "UNKNOWN"
    assert item["reason"] == "MIXED_PRIMARY_STORAGE_IDS"


def test_schema_accepts_artifact_and_rejects_raw_projection():
    artifact = _build()
    schema = json.loads((ROOT / "schemas/proxmox-ve-vm-storage-relationship.schema.json").read_text())
    validator = jsonschema.Draft202012Validator(schema)
    validator.validate(artifact)

    bad = deepcopy(artifact)
    bad["vm_storage_relationships"][0]["raw_disk"] = "local:private"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad)

    bad = deepcopy(artifact)
    bad["storage_references"][0]["path"] = "/var/lib/vz"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad)


def test_markdown_keeps_failure_domain_boundary_explicit():
    text = render_proxmox_ve_vm_storage_relationship_markdown(_build())
    assert "SAME_PVE_STORAGE_ID_AS_BACKUP" in text
    assert "does not prove the same physical disk" in text
    assert "BACKUP_FAILURE_DOMAIN remains unchanged" in text
