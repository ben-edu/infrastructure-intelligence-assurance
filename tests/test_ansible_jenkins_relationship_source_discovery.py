from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "discovery" / "m6_ansible_jenkins_relationship_source_discovery.py"
SPEC = importlib.util.spec_from_file_location("m6_ansible_jenkins_relationship_source_discovery", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_relationship_requires_jenkins_context_and_explicit_ansible_entrypoint():
    assert MODULE._relationship_signal(
        "Jenkinsfile",
        "pipeline { stages { stage('x') { steps { sh 'ansible-playbook site.yml' } } } }",
    )
    assert not MODULE._relationship_signal("scripts/deploy.sh", "echo jenkins ansible deployment")
    assert not MODULE._relationship_signal(
        "Jenkinsfile",
        "pipeline { stages { stage('x') { steps { echo 'ansible automation' } } } }",
    )


def test_non_evidence_paths_are_excluded():
    assert MODULE._safe_candidate_path("ci/Jenkinsfile")
    assert MODULE._safe_candidate_path("ci/pipeline.groovy")
    assert not MODULE._safe_candidate_path("mcp/jenkins-readonly/.env")
    assert not MODULE._safe_candidate_path("ansible/group_vars/all.yml")
    assert not MODULE._safe_candidate_path("terraform/prod.tfvars")


def test_discover_reports_explicit_relationship_without_projecting_content(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "Jenkinsfile").write_text(
        "pipeline { stages { stage('deploy') { steps { sh 'ansible-playbook site.yml' } } } }",
        encoding="utf-8",
    )
    (repo / "notes.py").write_text("print('jenkins ansible')\n", encoding="utf-8")

    monkeypatch.setattr(MODULE, "_tracked_files", lambda _: ("COMPLETE", ["Jenkinsfile", "notes.py"]))
    result = MODULE.discover(repo)

    assert result["source_status"] == "COMPLETE"
    assert result["jenkins_context_files"] == 2
    assert result["ansible_entrypoint_signal_files"] == 1
    assert result["explicit_relationship_signal_files"] == 1
    assert result["relationship_source_status"] == "EXPLICIT_DECLARED_RELATIONSHIP_SIGNAL_OBSERVED"
    rendered = repr(result)
    assert "site.yml" not in rendered
    assert "deploy" not in rendered


def test_discover_preserves_ansible_outcome_unknown_when_none_observed(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "Jenkinsfile").write_text("pipeline { stages { stage('build') { steps { echo 'ok' } } } }", encoding="utf-8")

    monkeypatch.setattr(MODULE, "_tracked_files", lambda _: ("COMPLETE", ["Jenkinsfile"]))
    result = MODULE.discover(repo)

    assert result["relationship_source_status"] == "NONE_OBSERVED_IN_BOUNDED_SOURCE"
    assert result["execution_outcome_status"] == "UNKNOWN"
    assert result["execution_success_status"] == "UNKNOWN"
    assert result["idempotence_status"] == "UNKNOWN"
    assert result["configuration_drift_status"] == "UNKNOWN"
    assert result["successful_execution_claims"] == 0
    assert result["drift_claims"] == 0


def test_stream_scan_handles_candidate_larger_than_old_half_megabyte_limit(tmp_path):
    candidate = tmp_path / "pipeline.json"
    candidate.write_text("x" * (600 * 1024) + " jenkins ", encoding="utf-8")

    status, jenkins, ansible = MODULE._scan_candidate_file("pipeline.json", candidate)

    assert status == "COMPLETE"
    assert jenkins is True
    assert ansible is False


def test_stream_scan_fails_closed_above_hard_ceiling(tmp_path, monkeypatch):
    candidate = tmp_path / "pipeline.json"
    candidate.write_text("jenkins ansible-playbook" * 10, encoding="utf-8")
    monkeypatch.setattr(MODULE, "MAX_SCAN_BYTES", 32)

    status, jenkins, ansible = MODULE._scan_candidate_file("pipeline.json", candidate)

    assert status == "OVERSIZE"
    assert jenkins is False
    assert ansible is False
