from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "discovery" / "m6_terraform_local_state_structure.py"
SPEC = importlib.util.spec_from_file_location("m6_terraform_local_state_structure", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _write_state(path: Path, resources: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 4,
                "serial": 77,
                "lineage": "internal-lineage-marker",
                "outputs": {"internal_output_name": {"value": "hidden-output-marker"}},
                "resources": resources,
            }
        ),
        encoding="utf-8",
    )


def test_parse_state_projects_only_safe_aggregate_structure(tmp_path):
    state_path = tmp_path / "terraform.tfstate"
    _write_state(
        state_path,
        [
            {
                "mode": "managed",
                "type": "proxmox_vm_qemu",
                "name": "internal_vm_name",
                "provider": "provider.internal.alias",
                "instances": [
                    {"index_key": "internal-key", "attributes": {"internal_field": "hidden-attribute-marker"}},
                    {"attributes": {"another_field": "another-hidden-marker"}},
                ],
            },
            {
                "mode": "data",
                "type": "external",
                "name": "internal_data_name",
                "instances": [{"attributes": {"result": "hidden-data-marker"}}],
            },
        ],
    )

    result = MODULE._parse_state("bm1", state_path)

    assert result["parse_status"] == "COMPLETE"
    assert result["managed_resource_blocks"] == 1
    assert result["managed_instances"] == 2
    assert result["data_resource_blocks"] == 1
    assert result["data_instances"] == 1
    assert result["managed_resource_type_counts"] == {"proxmox_vm_qemu": 1}

    rendered = repr(result)
    for forbidden in (
        "internal_vm_name",
        "internal_data_name",
        "internal-key",
        "hidden-attribute-marker",
        "another-hidden-marker",
        "hidden-data-marker",
        "hidden-output-marker",
        "internal-lineage-marker",
        "provider.internal.alias",
        "77",
    ):
        assert forbidden not in rendered


def test_sensitive_looking_resource_type_is_redacted(tmp_path):
    state_path = tmp_path / "terraform.tfstate"
    _write_state(
        state_path,
        [{"mode": "managed", "type": "example_secret_object", "name": "x", "instances": [{}]}],
    )

    result = MODULE._parse_state("bm1", state_path)

    assert result["managed_resource_type_counts"] == {"REDACTED_TYPE_CATEGORY": 1}
    assert "example_secret_object" not in repr(result)


def test_symlink_state_fails_closed(tmp_path):
    target = tmp_path / "target.json"
    _write_state(target, [])
    state_path = tmp_path / "terraform.tfstate"
    state_path.symlink_to(target)

    result = MODULE._parse_state("bm1", state_path)

    assert result["parse_status"] == "SYMLINK_REJECTED"


def test_discover_preserves_coverage_and_outcome_unknown(tmp_path):
    roots = {}
    for name in ("bm1", "bm2"):
        root = tmp_path / name
        root.mkdir()
        _write_state(
            root / "terraform.tfstate",
            [{"mode": "managed", "type": "proxmox_vm_qemu", "name": name, "instances": [{}]}],
        )
        roots[name] = root

    result = MODULE.discover(roots)

    assert result["source_status"] == "COMPLETE"
    assert result["roots_parsed_complete"] == 2
    assert result["managed_resource_blocks"] == 2
    assert result["managed_instances"] == 2
    assert result["managed_resource_type_counts"] == {"proxmox_vm_qemu": 2}
    assert result["state_structure_status"] == "STRUCTURAL_AGGREGATE_OBSERVED"
    assert result["state_backed_coverage_status"] == "UNKNOWN"
    assert result["live_resource_coverage_status"] == "UNKNOWN"
    assert result["plan_result_status"] == "UNKNOWN"
    assert result["apply_result_status"] == "UNKNOWN"
    assert result["drift_status"] == "UNKNOWN"
    assert result["destructive_change_status"] == "UNKNOWN"
    assert result["state_backed_coverage_claims"] == 0
    assert result["drift_claims"] == 0
    assert result["destructive_change_claims"] == 0
