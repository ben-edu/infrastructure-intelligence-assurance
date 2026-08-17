from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/discovery/m5_pve_storage_retention_discovery_retry.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pve_storage_retention_retry", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extracts_storage_only_from_preserved_recovery_point_mechanism():
    module = load_module()
    artifact = {
        "vm_backup_assurance_version": "0.1",
        "mutation_allowed": False,
        "assets": [
            {
                "source_recovery_point_ids": ["pve-rp-abc"],
                "assurance": {
                    "backup_mechanisms": [
                        {
                            "type": "PROXMOX_VE_STORAGE_ARCHIVE",
                            "source_type": "PROXMOX_VE",
                            "storage_id": "local",
                            "basis": ["RECOVERY_POINT_OBSERVED_IN_SOURCE_SCOPE"],
                        }
                    ]
                },
            },
            {
                "source_recovery_point_ids": [],
                "assurance": {
                    "backup_mechanisms": [
                        {
                            "type": "PROXMOX_VE_STORAGE_ARCHIVE",
                            "source_type": "PROXMOX_VE",
                            "storage_id": "must-not-promote",
                            "basis": ["RECOVERY_POINT_OBSERVED_IN_SOURCE_SCOPE"],
                        }
                    ]
                },
            },
        ],
    }

    assert module.accepted_recovery_point_storage_ids_from_vm_assurance(artifact) == {
        "local"
    }


def test_fails_closed_for_wrong_version_or_mutation_allowed():
    module = load_module()
    artifact = {
        "vm_backup_assurance_version": "0.2",
        "mutation_allowed": False,
        "assets": [],
    }
    assert module.accepted_recovery_point_storage_ids_from_vm_assurance(artifact) == set()

    artifact["vm_backup_assurance_version"] = "0.1"
    artifact["mutation_allowed"] = True
    assert module.accepted_recovery_point_storage_ids_from_vm_assurance(artifact) == set()
