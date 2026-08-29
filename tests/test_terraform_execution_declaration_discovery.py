from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "discovery" / "m6_terraform_execution_declaration_discovery.py"
SPEC = importlib.util.spec_from_file_location("m6_terraform_execution_declaration_discovery", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _git_add_all(repo: Path) -> None:
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)


def test_classification_returns_only_phase_categories_and_gate_signal():
    text = '''
    # terraform destroy should be ignored as a full-line comment
    stage('Plan') {
      sh 'terraform init -input=false'
      sh 'terraform validate'
      sh 'terraform plan -out=plan.bin'
    }
    input message: 'Approve deployment?'
    sh 'terraform apply plan.bin'
    '''

    phases, gate_signal = MODULE._classify_text(text)

    assert phases["init"] == 1
    assert phases["validate"] == 1
    assert phases["plan"] == 1
    assert phases["apply"] == 1
    assert phases.get("destroy", 0) == 0
    assert gate_signal is True


def test_discover_excludes_sensitive_paths_and_does_not_return_raw_commands(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()

    (repo / "Jenkinsfile").write_text(
        "stage('Plan') { sh 'terraform plan -out=sensitive-plan-name' }\n"
        "input message: 'Approve?'\n"
        "stage('Apply') { sh 'terraform apply sensitive-plan-name' }\n",
        encoding="utf-8",
    )

    secret_dir = repo / "credentials"
    secret_dir.mkdir()
    (secret_dir / "deploy.sh").write_text(
        "terraform destroy -auto-approve\n",
        encoding="utf-8",
    )

    docs = repo / "README.md"
    docs.write_text("terraform apply example only\n", encoding="utf-8")

    _git_add_all(repo)
    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["candidate_files_selected"] == 1
    assert result["candidate_files_scanned"] == 1
    assert result["phase_file_counts"]["plan"] == 1
    assert result["phase_file_counts"]["apply"] == 1
    assert result["phase_file_counts"].get("destroy", 0) == 0
    assert result["files_with_gate_signal"] == 1
    assert len(result["files"]) == 1

    row = result["files"][0]
    assert row["path"] == "Jenkinsfile"
    assert row["terraform_phase_signals"] == ["apply", "plan"]
    assert row["gate_signal"] is True
    assert "command" not in row
    assert "arguments" not in row
    assert "raw_line" not in row
    assert "sensitive-plan-name" not in repr(result)


def test_gate_only_file_is_not_terraform_execution_evidence(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "service.py").write_text(
        "approval_required = True\nconfirm = 'manual'\n",
        encoding="utf-8",
    )
    _git_add_all(repo)

    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["candidate_files_scanned"] == 1
    assert result["files"] == []
    assert result["files_with_gate_signal"] == 0
    assert not result["phase_file_counts"]
    assert not result["phase_signal_counts"]


def test_no_signal_is_bounded_absence_not_execution_failure(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "deploy.sh").write_text("echo safe\n", encoding="utf-8")
    _git_add_all(repo)

    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["candidate_files_scanned"] == 1
    assert result["files"] == []
    assert not result["phase_file_counts"]
    assert not result["phase_signal_counts"]
