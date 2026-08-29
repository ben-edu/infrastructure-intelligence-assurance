from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "discovery" / "m6_ansible_execution_declaration_discovery.py"
SPEC = importlib.util.spec_from_file_location("m6_ansible_execution_declaration_discovery", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _git_add_all(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)


def test_classification_accepts_only_tightly_bounded_execution_entrypoints():
    text = '''
    # ansible-playbook ignored-comment.yml
    sh 'ansible-playbook site.yml --check'
    ansible-runner run ./runner-data
    ansible-navigator run site.yml
    ansible-lint site.yml
    ansible all -m ping
    input message: 'Approve deployment?'
    '''

    entrypoints, gate_signal = MODULE._classify_text(text)

    assert entrypoints["ansible_playbook"] == 1
    assert entrypoints["ansible_runner_run"] == 1
    assert entrypoints["ansible_navigator_run"] == 1
    assert len(entrypoints) == 3
    assert gate_signal is True


def test_discover_excludes_sensitive_paths_and_does_not_return_raw_commands(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    (repo / "Jenkinsfile").write_text(
        "stage('Deploy') { sh 'ansible-playbook secret-playbook-name.yml -i sensitive-inventory' }\n"
        "input message: 'Approve?'\n",
        encoding="utf-8",
    )

    secret_dir = repo / "credentials"
    secret_dir.mkdir()
    (secret_dir / "deploy.sh").write_text(
        "ansible-playbook should-not-be-read.yml\n",
        encoding="utf-8",
    )

    group_vars = repo / "group_vars"
    group_vars.mkdir()
    (group_vars / "all.yml").write_text(
        "command: ansible-playbook should-not-be-read.yml\n",
        encoding="utf-8",
    )

    _git_add_all(repo)
    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["entrypoint_file_counts"]["ansible_playbook"] == 1
    assert result["files_with_gate_signal"] == 1
    assert len(result["files"]) == 1

    row = result["files"][0]
    assert row["path"] == "Jenkinsfile"
    assert row["ansible_execution_entrypoints"] == ["ansible_playbook"]
    assert row["gate_signal"] is True
    assert "command" not in row
    assert "arguments" not in row
    assert "raw_line" not in row
    assert "secret-playbook-name" not in repr(result)
    assert "sensitive-inventory" not in repr(result)
    assert "should-not-be-read" not in repr(result)


def test_gate_only_and_generic_ansible_tooling_do_not_enter_execution_evidence(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "deploy.py").write_text(
        "approval = True\n"
        "tool = 'ansible-lint'\n"
        "generic = 'ansible all -m ping'\n",
        encoding="utf-8",
    )
    _git_add_all(repo)

    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["candidate_files_scanned"] == 1
    assert result["files"] == []
    assert not result["entrypoint_file_counts"]
    assert not result["entrypoint_signal_counts"]
    assert result["files_with_gate_signal"] == 0


def test_no_signal_is_bounded_absence_not_execution_failure(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "deploy.sh").write_text("echo safe\n", encoding="utf-8")
    _git_add_all(repo)

    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["candidate_files_scanned"] == 1
    assert result["files"] == []
    assert not result["entrypoint_file_counts"]
    assert not result["entrypoint_signal_counts"]
