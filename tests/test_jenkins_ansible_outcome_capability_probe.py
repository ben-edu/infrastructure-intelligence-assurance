from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "discovery" / "m6_jenkins_ansible_outcome_capability_probe.py"
spec = importlib.util.spec_from_file_location("m6_jenkins_ansible_outcome_capability_probe", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_job_and_build_metadata_capability_signals_are_observed(tmp_path: Path) -> None:
    root = tmp_path / "jenkins-readonly"
    root.mkdir()
    (root / "server.py").write_text(
        "def list_jobs():\n    return []\n\ndef get_build_info():\n    return {}\n",
        encoding="utf-8",
    )

    result = module.inspect_integration_source((root,))

    assert result["source_status"] == "COMPLETE"
    assert result["capability_status"] == "JOB_AND_BUILD_METADATA_CAPABILITY_SIGNAL_OBSERVED"
    assert result["job_metadata_signal_files"] == 1
    assert result["build_metadata_signal_files"] == 1


def test_console_only_signal_does_not_become_safe_metadata_capability(tmp_path: Path) -> None:
    root = tmp_path / "jenkins-readonly"
    root.mkdir()
    (root / "server.py").write_text(
        "def get_console_log():\n    return None\n",
        encoding="utf-8",
    )

    result = module.inspect_integration_source((root,))

    assert result["console_capability_signal_files"] == 1
    assert result["job_metadata_signal_files"] == 0
    assert result["build_metadata_signal_files"] == 0
    assert result["capability_status"] == "NONE_OBSERVED_IN_BOUNDED_INTEGRATION_SOURCE"


def test_sensitive_env_file_is_excluded_without_secret_projection(tmp_path: Path) -> None:
    root = tmp_path / "jenkins-readonly"
    root.mkdir()
    secret = "DO_NOT_PROJECT_THIS_SECRET"
    (root / ".env").write_text(f"JENKINS_TOKEN={secret}\n", encoding="utf-8")
    (root / "server.py").write_text("def list_jobs():\n    return []\n", encoding="utf-8")

    result = module.inspect_integration_source((root,))

    assert result["sensitive_files_excluded"] == 1
    assert secret not in repr(result)
    assert result["credential_values_inspected"] is False
    assert result["environment_values_inspected"] is False


def test_missing_integration_root_preserves_no_source_status(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    result = module.inspect_integration_source((missing,))

    assert result["source_status"] == "NO_INTEGRATION_SOURCE_OBSERVED"
    assert result["capability_status"] == "NO_INTEGRATION_SOURCE_OBSERVED"
    assert result["jenkins_api_invoked"] is False
