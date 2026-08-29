from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "discovery" / "m6_terraform_root_module_coverage.py"
SPEC = importlib.util.spec_from_file_location("m6_terraform_root_module_coverage", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _git_add_all(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)


def test_module_source_parser_ignores_commented_module_blocks():
    text = '''
    # module "commented" { source = "../../modules/nope" }
    module "internal_name" {
      source = "../../modules/proxmox_vm"
    }
    /* module "also_commented" { source = "../../modules/nope2" } */
    '''
    assert MODULE._module_source_literals(text) == ["../../modules/proxmox_vm"]


def test_local_module_resolution_is_bounded_to_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    root = repo / "terraform" / "environments" / "bm1"
    module_dir = repo / "terraform" / "modules" / "proxmox_vm"
    root.mkdir(parents=True)
    module_dir.mkdir(parents=True)

    tracked = {"terraform/environments/bm1", "terraform/modules/proxmox_vm"}

    status, resolved = MODULE._resolve_local_module_directory(
        repo,
        "terraform/environments/bm1",
        "../../modules/proxmox_vm",
        tracked,
    )
    assert status == "RESOLVED_LOCAL_MODULE"
    assert resolved == "terraform/modules/proxmox_vm"

    status, resolved = MODULE._resolve_local_module_directory(
        repo,
        "terraform/environments/bm1",
        "../../../../outside",
        tracked,
    )
    assert status == "LOCAL_SOURCE_OUTSIDE_BOUNDED_REPO"
    assert resolved is None


def test_discover_resolves_root_to_local_module_resource_type(tmp_path: Path):
    repo = tmp_path / "repo"
    root = repo / "terraform" / "environments" / "bm1"
    module_dir = repo / "terraform" / "modules" / "proxmox_vm"
    root.mkdir(parents=True)
    module_dir.mkdir(parents=True)

    (root / "main.tf").write_text(
        'module "vm" {\n  source = "../../modules/proxmox_vm"\n}\n',
        encoding="utf-8",
    )
    (module_dir / "main.tf").write_text(
        'resource "proxmox_vm_qemu" "internal_instance" {\n}\n',
        encoding="utf-8",
    )
    _git_add_all(repo)

    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["relationships_resolved"] == 1
    assert result["roots_with_resolved_local_module"] == 1
    assert result["roots_with_declared_resource_path"] == 1
    assert len(result["roots"]) == 1
    row = result["roots"][0]
    assert row["root_directory"] == "terraform/environments/bm1"
    assert row["resolved_module_directories"] == ["terraform/modules/proxmox_vm"]
    assert row["reachable_resource_types"] == {"proxmox_vm_qemu": 1}
    assert row["structural_declared_resource_path_status"] == "RESOLVED_LOCAL_MODULE_TO_DECLARED_RESOURCE"
    assert "source_value" not in row
    assert "module_name" not in row


def test_nonlocal_module_source_is_counted_but_not_followed(tmp_path: Path):
    repo = tmp_path / "repo"
    root = repo / "terraform" / "environments" / "bm1"
    root.mkdir(parents=True)
    (root / "main.tf").write_text(
        'module "remote" {\n  source = "example/vendor/module"\n}\n',
        encoding="utf-8",
    )
    _git_add_all(repo)

    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["relationships_resolved"] == 0
    assert result["module_sources_nonlocal"] == 1
    assert result["roots_with_declared_resource_path"] == 0
    row = result["roots"][0]
    assert row["resolved_module_directories"] == []
    assert row["reachable_resource_types"] == {}
    assert row["structural_declared_resource_path_status"] == "NO_RESOLVED_LOCAL_MODULE"
