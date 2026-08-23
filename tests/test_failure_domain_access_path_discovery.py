from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/discovery/m5_failure_domain_access_path_discovery.py"


def load_module():
    spec = importlib.util.spec_from_file_location("m5_failure_domain_access_path", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_qemu_projection_returns_only_storage_ids_and_excludes_cdrom():
    module = load_module()
    config = {
        "scsi0": "local:100/vm-100-disk-0.qcow2,size=32G",
        "virtio1": "fast:100/vm-100-disk-1.qcow2,size=8G",
        "ide2": "local:cloudinit,media=cdrom",
        "description": "secret-like free form value that must not affect projection",
        "net0": "virtio=AA:BB:CC:DD:EE:FF,bridge=vmbr0",
    }
    assert module.qemu_storage_ids(config) == {"local", "fast"}


def test_lxc_projection_returns_only_storage_ids():
    module = load_module()
    config = {
        "rootfs": "local:subvol-200-disk-0,size=8G",
        "mp0": "archive:subvol-200-disk-1,mp=/data",
        "net0": "name=eth0,bridge=vmbr0",
    }
    assert module.lxc_storage_ids(config) == {"local", "archive"}


def test_logical_coupling_does_not_promote_physical_independence():
    module = load_module()
    assert (
        module.logical_separation_status(
            subject_node="delfan",
            backup_nodes={"delfan"},
            vm_storage_ids={"local"},
            backup_storage_ids={"local"},
            config_observed=True,
        )
        == "NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID"
    )
    assert (
        module.logical_separation_status(
            subject_node="delfan",
            backup_nodes={"delfan"},
            vm_storage_ids={"fast"},
            backup_storage_ids={"local"},
            config_observed=True,
        )
        == "NOT_SEPARATED_AT_PVE_NODE_LAYER"
    )
    assert (
        module.logical_separation_status(
            subject_node="delfan",
            backup_nodes={"other-node"},
            vm_storage_ids={"fast"},
            backup_storage_ids={"local"},
            config_observed=True,
        )
        == "SEPARATED_AT_OBSERVED_NODE_AND_STORAGE_ID_LAYER"
    )
    assert (
        module.logical_separation_status(
            subject_node="delfan",
            backup_nodes={"delfan"},
            vm_storage_ids=set(),
            backup_storage_ids={"local"},
            config_observed=False,
        )
        == "UNKNOWN"
    )


def test_source_contains_no_mutating_pve_operations_or_raw_config_prints():
    text = SCRIPT.read_text(encoding="utf-8")
    lowered = text.lower()
    forbidden = (
        "qm set",
        "qm destroy",
        "pct set",
        "pct destroy",
        "pvesm set",
        "pvesm remove",
        "print(data)",
        "print(config)",
    )
    for token in forbidden:
        assert token not in lowered
    assert "physical_failure_domain_independence_claims: 0" in text
    assert "No mutation was performed." in text
