from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "discovery" / "m6_terraform_declared_resource_location_probe.py"
SPEC = importlib.util.spec_from_file_location("m6_resource_location_probe", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _git_add_all(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)


def test_resource_locations_distinguish_root_and_module(tmp_path: Path):
    repo = tmp_path / "repo"
    root = repo / "terraform" / "environments" / "bm1"
    module_dir = repo / "terraform" / "modules" / "proxmox_vm"
    root.mkdir(parents=True)
    module_dir.mkdir(parents=True)

    (root / "main.tf").write_text(
        'resource "proxmox_vm_qemu" "root_instance" {}\n'
        'module "vm" { source = "../../modules/proxmox_vm" }\n',
        encoding="utf-8",
    )
    (module_dir / "main.tf").write_text(
        'variable "name" { type = string }\n',
        encoding="utf-8",
    )
    _git_add_all(repo)

    result = MODULE.discover_resource_locations(repo)
    assert result["source_status"] == "COMPLETE"
    directories = result["directories"]
    assert directories["terraform/environments/bm1"]["classification"] == "ROOT_CANDIDATE"
    assert directories["terraform/environments/bm1"]["resource_types"] == {"proxmox_vm_qemu": 1}
    assert directories["terraform/modules/proxmox_vm"]["classification"] == "MODULE_DIRECTORY"
    assert directories["terraform/modules/proxmox_vm"]["resource_types"] == {}


def test_probe_does_not_expose_resource_instance_names(tmp_path: Path):
    repo = tmp_path / "repo"
    root = repo / "terraform" / "environments" / "bm1"
    root.mkdir(parents=True)
    (root / "main.tf").write_text(
        'resource "proxmox_vm_qemu" "sensitive_internal_name" {}\n',
        encoding="utf-8",
    )
    _git_add_all(repo)

    result = MODULE.discover_resource_locations(repo)
    serialized = repr(result)
    assert "sensitive_internal_name" not in serialized
    assert "proxmox_vm_qemu" in serialized
