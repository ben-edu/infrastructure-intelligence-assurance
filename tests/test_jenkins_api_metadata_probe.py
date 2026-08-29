from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "discovery" / "m6_jenkins_api_metadata_probe.py"
SPEC = importlib.util.spec_from_file_location("m6_jenkins_api_metadata_probe", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_metadata_url_rejects_userinfo_and_query_values():
    assert MODULE._metadata_url("http://user:secret@jenkins.local") is None
    assert MODULE._metadata_url("https://jenkins.local/?token=secret") is None

    safe = MODULE._metadata_url("https://jenkins.local/jenkins")
    assert safe is not None
    assert safe.startswith("https://jenkins.local/jenkins/api/json?")
    assert "console" not in safe.lower()
    assert "config.xml" not in safe.lower()


def test_env_reader_keeps_only_approved_keys(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "JENKINS_URL=https://jenkins.local\n"
        "JENKINS_USER=reader\n"
        "JENKINS_API_TOKEN=super-secret\n"
        "OTHER_SECRET=must-not-be-loaded\n",
        encoding="utf-8",
    )

    values = MODULE._read_approved_env_file(env_file)

    assert set(values) == {"JENKINS_URL", "JENKINS_USER", "JENKINS_API_TOKEN"}
    assert "OTHER_SECRET" not in values


def test_aggregate_metadata_does_not_return_job_names_or_build_numbers():
    payload = {
        "jobs": [
            {
                "name": "ansible-deploy-sensitive-project",
                "lastBuild": {"number": 88, "result": "SUCCESS", "building": False},
            },
            {
                "name": "ordinary-build-private-name",
                "lastBuild": {"number": 99, "result": "FAILURE", "building": False},
            },
            {"name": "ansible-running", "lastBuild": {"number": 100, "result": None, "building": True}},
        ]
    }

    result = MODULE._aggregate_metadata(payload)

    assert result["jobs_total"] == 3
    assert result["jobs_with_last_build_metadata"] == 3
    assert result["ansible_name_signal_jobs"] == 2
    assert result["ansible_name_signal_jobs_with_last_build_metadata"] == 2
    assert result["last_build_result_counts"] == {"FAILURE": 1, "RUNNING": 1, "SUCCESS": 1}
    assert result["ansible_name_signal_last_build_result_counts"] == {"RUNNING": 1, "SUCCESS": 1}
    rendered = repr(result)
    assert "ansible-deploy-sensitive-project" not in rendered
    assert "ordinary-build-private-name" not in rendered
    assert "88" not in rendered
    assert "99" not in rendered
    assert "100" not in rendered


def test_discover_preserves_ansible_outcome_unknown(monkeypatch):
    monkeypatch.setattr(
        MODULE,
        "_load_local_connection_material",
        lambda: {
            "status": "CONNECTION_CONFIG_READY",
            "base_url": "https://jenkins.local",
            "username": "reader",
            "secret": "not-projected",
            "env_files_observed": 1,
            "env_files_read_for_approved_keys": 1,
            "credential_material_loaded_locally": True,
        },
    )
    monkeypatch.setattr(
        MODULE,
        "_fetch_metadata_json",
        lambda base_url, username, secret: (
            "COMPLETE",
            {"jobs": [{"name": "ansible-safe", "lastBuild": {"result": "SUCCESS", "building": False}}]},
        ),
    )

    result = MODULE.discover()

    assert result["jenkins_api_invoked"] is True
    assert result["api_observation_status"] == "COMPLETE"
    assert result["ansible_name_signal_jobs"] == 1
    assert result["execution_outcome_status"] == "UNKNOWN"
    assert result["execution_success_status"] == "UNKNOWN"
    assert result["idempotence_status"] == "UNKNOWN"
    assert result["configuration_drift_status"] == "UNKNOWN"
    assert result["credential_values_projected"] is False
    assert result["endpoint_value_projected"] is False
