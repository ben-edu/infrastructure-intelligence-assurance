from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "discovery" / "m6_ansible_declared_inventory.py"
SPEC = importlib.util.spec_from_file_location("m6_ansible_declared_inventory", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _git_add_all(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)


def test_discovers_inventory_playbook_and_role_without_returning_host_identifiers(tmp_path: Path):
    repo = tmp_path / "repo"
    inventory_dir = repo / "ansible" / "inventories" / "prod"
    playbook_dir = repo / "ansible" / "playbooks"
    role_dir = repo / "ansible" / "roles" / "web" / "tasks"
    inventory_dir.mkdir(parents=True)
    playbook_dir.mkdir(parents=True)
    role_dir.mkdir(parents=True)

    (inventory_dir / "hosts.ini").write_text(
        "[web]\nserver-a ansible_host=192.0.2.10\nserver-b ansible_host=192.0.2.11\n",
        encoding="utf-8",
    )
    (playbook_dir / "site.yml").write_text(
        "- hosts: web\n  roles:\n    - web\n",
        encoding="utf-8",
    )
    (role_dir / "main.yml").write_text("- name: noop\n  debug:\n    msg: safe\n", encoding="utf-8")
    _git_add_all(repo)

    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["inventory_files"] == ["ansible/inventories/prod/hosts.ini"]
    assert result["playbook_files"] == ["ansible/playbooks/site.yml"]
    assert result["role_directories"] == ["ansible/roles/web"]
    assert result["inventory_group_declarations"] == 1
    assert result["inventory_host_declarations"] == 2
    rendered = repr(result)
    assert "server-a" not in rendered
    assert "server-b" not in rendered
    assert "192.0.2.10" not in rendered
    assert "192.0.2.11" not in rendered


def test_sensitive_var_directories_are_not_read(tmp_path: Path):
    repo = tmp_path / "repo"
    group_vars = repo / "ansible" / "group_vars"
    host_vars = repo / "ansible" / "host_vars"
    group_vars.mkdir(parents=True)
    host_vars.mkdir(parents=True)
    (group_vars / "all.yml").write_text("ansible_password: super-secret\n", encoding="utf-8")
    (host_vars / "server.yml").write_text("become_password: another-secret\n", encoding="utf-8")
    _git_add_all(repo)

    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["excluded_sensitive_ansible_data_files"] == 2
    assert result["files_read"] == 0
    assert "super-secret" not in repr(result)
    assert "another-secret" not in repr(result)


def test_no_ansible_source_is_bounded_absence(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("no ansible source here\n", encoding="utf-8")
    _git_add_all(repo)

    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["ansible_scope_files"] == 0
    assert result["inventory_files"] == []
    assert result["playbook_files"] == []
    assert result["role_directories"] == []
