from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "discovery" / "m6_terraform_declared_state_structural_coverage.py"
SPEC = importlib.util.spec_from_file_location("m6_terraform_declared_state_structural_coverage", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _declared(resource_counts_bm1, resource_counts_bm2):
    return {
        "source_status": "COMPLETE",
        "directories": {
            "terraform/environments/bm1": {"resource_types": resource_counts_bm1},
            "terraform/environments/bm2": {"resource_types": resource_counts_bm2},
        },
    }


def _state(resource_counts_bm1, resource_counts_bm2):
    return {
        "source_status": "COMPLETE",
        "root_results": [
            {
                "root": "bm1",
                "parse_status": "COMPLETE",
                "managed_resource_type_counts": resource_counts_bm1,
            },
            {
                "root": "bm2",
                "parse_status": "COMPLETE",
                "managed_resource_type_counts": resource_counts_bm2,
            },
        ],
    }


def test_complete_match_reports_limited_structural_match(monkeypatch, tmp_path):
    monkeypatch.setattr(
        MODULE.DECLARED,
        "discover_resource_locations",
        lambda repo: _declared({"proxmox_vm_qemu": 1}, {"proxmox_vm_qemu": 1}),
    )
    monkeypatch.setattr(
        MODULE.STATE,
        "discover",
        lambda roots: _state({"proxmox_vm_qemu": 1}, {"proxmox_vm_qemu": 1}),
    )

    result = MODULE.discover(tmp_path)

    assert result["source_status"] == "COMPLETE"
    assert result["roots_compared_complete"] == 2
    assert result["declared_resource_blocks"] == 2
    assert result["state_managed_resource_blocks"] == 2
    assert result["matched_resource_type_block_count"] == 2
    assert result["declared_to_local_state_structural_coverage_status"] == "DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH"
    assert result["state_backed_coverage_status"] == "UNKNOWN"
    assert result["live_resource_coverage_status"] == "UNKNOWN"
    assert result["drift_status"] == "UNKNOWN"


def test_mismatch_is_not_promoted_to_drift(monkeypatch, tmp_path):
    monkeypatch.setattr(
        MODULE.DECLARED,
        "discover_resource_locations",
        lambda repo: _declared({"proxmox_vm_qemu": 1}, {"proxmox_vm_qemu": 1}),
    )
    monkeypatch.setattr(
        MODULE.STATE,
        "discover",
        lambda roots: _state({"proxmox_vm_qemu": 1}, {"proxmox_vm_qemu": 2}),
    )

    result = MODULE.discover(tmp_path)

    assert result["source_status"] == "COMPLETE"
    assert result["declared_to_local_state_structural_coverage_status"] == "DECLARED_TO_LOCAL_STATE_STRUCTURAL_MISMATCH"
    assert result["drift_status"] == "UNKNOWN"
    assert result["drift_claims"] == 0
    assert result["destructive_change_status"] == "UNKNOWN"
    assert result["destructive_change_claims"] == 0


def test_incomplete_declared_or_state_source_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(
        MODULE.DECLARED,
        "discover_resource_locations",
        lambda repo: {"source_status": "INCOMPLETE", "directories": {}},
    )
    monkeypatch.setattr(
        MODULE.STATE,
        "discover",
        lambda roots: _state({"proxmox_vm_qemu": 1}, {"proxmox_vm_qemu": 1}),
    )

    result = MODULE.discover(tmp_path)

    assert result["source_status"] == "INCOMPLETE"
    assert result["declared_to_local_state_structural_coverage_status"] == "SOURCE_INCOMPLETE"
    assert result["state_backed_coverage_status"] == "UNKNOWN"


def test_projection_does_not_carry_identity_or_state_values(monkeypatch, tmp_path):
    sentinel_name = "private-resource-name-sentinel"
    sentinel_value = "private-state-value-sentinel"
    monkeypatch.setattr(
        MODULE.DECLARED,
        "discover_resource_locations",
        lambda repo: {
            **_declared({"proxmox_vm_qemu": 1}, {"proxmox_vm_qemu": 1}),
            "raw_hcl": sentinel_name,
        },
    )
    state_payload = _state({"proxmox_vm_qemu": 1}, {"proxmox_vm_qemu": 1})
    state_payload["root_results"][0]["resource_name"] = sentinel_name
    state_payload["root_results"][0]["attributes"] = {"value": sentinel_value}
    monkeypatch.setattr(MODULE.STATE, "discover", lambda roots: state_payload)

    result = MODULE.discover(tmp_path)
    rendered = repr(result)

    assert sentinel_name not in rendered
    assert sentinel_value not in rendered
    assert result["declared_to_local_state_structural_coverage_status"] == "DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH"
