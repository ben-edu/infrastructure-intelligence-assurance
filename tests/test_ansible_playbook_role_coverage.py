from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "discovery" / "m6_ansible_playbook_role_coverage.py"
SPEC = importlib.util.spec_from_file_location("m6_ansible_playbook_role_coverage", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _git_add_all(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)


def test_role_parser_extracts_only_supported_simple_role_tokens():
    text = '''
    - name: Secret play name that must not be projected
      hosts: private-prod.example.internal
      roles:
        - common
        - role: ssh_hardening
          vars:
            password_like_value: do-not-project
      tasks:
        - name: Not a role name
          ansible.builtin.include_role:
            name: baseline
        - import_role:
            name: harbor_service
        - include_role:
            name: "{{ dynamic_role }}"
    '''

    tokens, unparsed = MODULE._extract_direct_role_reference_tokens(text)

    assert tokens == ["common", "ssh_hardening", "baseline", "harbor_service"]
    assert unparsed == 1
    assert "private-prod.example.internal" not in repr((tokens, unparsed))
    assert "do-not-project" not in repr((tokens, unparsed))
    assert "dynamic_role" not in repr((tokens, unparsed))


def test_discover_resolves_playbooks_to_accepted_local_roles_without_host_leak(tmp_path: Path):
    repo = tmp_path / "repo"
    playbooks = repo / "ansible" / "playbooks"
    roles = repo / "ansible" / "roles"
    playbooks.mkdir(parents=True)
    (roles / "common" / "tasks").mkdir(parents=True)
    (roles / "baseline" / "tasks").mkdir(parents=True)
    (roles / "unused" / "tasks").mkdir(parents=True)

    (roles / "common" / "tasks" / "main.yml").write_text("---\n- debug:\n    msg: safe\n", encoding="utf-8")
    (roles / "baseline" / "tasks" / "main.yml").write_text("---\n- debug:\n    msg: safe\n", encoding="utf-8")
    (roles / "unused" / "tasks" / "main.yml").write_text("---\n- debug:\n    msg: safe\n", encoding="utf-8")

    (playbooks / "site.yml").write_text(
        '''
- name: Internal deployment
  hosts: 10.10.10.10
  roles:
    - common
  tasks:
    - include_role:
        name: baseline
''',
        encoding="utf-8",
    )
    (playbooks / "ping.yml").write_text(
        '''
- name: Connectivity check
  hosts: all
  tasks:
    - ping:
''',
        encoding="utf-8",
    )

    _git_add_all(repo)
    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["playbook_files_scanned"] == 2
    assert result["playbooks_with_resolved_local_role"] == 1
    assert result["playbooks_with_no_role_reference"] == 1
    assert result["playbooks_with_unknown_role_reference"] == 0
    assert result["referenced_role_directories"] == ["ansible/roles/baseline", "ansible/roles/common"]
    assert result["unreferenced_role_directories"] == ["ansible/roles/unused"]

    site = next(row for row in result["playbooks"] if row["path"] == "ansible/playbooks/site.yml")
    assert site["relationship_status"] == "RESOLVED_LOCAL_ROLE"
    assert site["resolved_local_role_directories"] == ["ansible/roles/baseline", "ansible/roles/common"]
    assert site["role_reference_signals"] == 2

    serialized = repr(result)
    assert "10.10.10.10" not in serialized
    assert "Internal deployment" not in serialized
    assert "Connectivity check" not in serialized
    assert "hosts" not in serialized.lower()


def test_unknown_role_reference_is_preserved_without_printing_token(tmp_path: Path):
    repo = tmp_path / "repo"
    playbooks = repo / "ansible" / "playbooks"
    roles = repo / "ansible" / "roles"
    playbooks.mkdir(parents=True)
    (roles / "local_role" / "tasks").mkdir(parents=True)
    (roles / "local_role" / "tasks" / "main.yml").write_text("---\n", encoding="utf-8")
    (playbooks / "site.yml").write_text(
        '''
- hosts: all
  roles:
    - external_role_name
''',
        encoding="utf-8",
    )
    _git_add_all(repo)

    result = MODULE.discover(repo)

    assert result["playbooks_with_unknown_role_reference"] == 1
    row = result["playbooks"][0]
    assert row["relationship_status"] == "UNKNOWN"
    assert row["unresolved_role_reference_count"] == 1
    assert row["resolved_local_role_directories"] == []
    assert "external_role_name" not in repr(result)


def test_sensitive_ansible_data_files_are_not_playbook_candidates(tmp_path: Path):
    repo = tmp_path / "repo"
    group_vars = repo / "ansible" / "group_vars"
    roles = repo / "ansible" / "roles" / "common" / "tasks"
    group_vars.mkdir(parents=True)
    roles.mkdir(parents=True)
    (roles / "main.yml").write_text("---\n", encoding="utf-8")
    (group_vars / "all.yml").write_text(
        "hosts: secret-target\nroles:\n  - common\nansible_password: secret-value\n",
        encoding="utf-8",
    )
    _git_add_all(repo)

    result = MODULE.discover(repo)

    assert result["playbook_files_scanned"] == 0
    assert result["playbooks"] == []
    assert "secret-target" not in repr(result)
    assert "secret-value" not in repr(result)
