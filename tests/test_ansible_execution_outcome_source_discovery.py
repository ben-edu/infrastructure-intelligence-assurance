from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path("scripts/discovery/m6_ansible_execution_outcome_source_discovery.py")


def load_module():
    spec = importlib.util.spec_from_file_location("m6_ansible_execution_outcome_source_discovery", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_jenkins_candidate_inspection_uses_metadata_only(tmp_path: Path):
    module = load_module()
    root = tmp_path / "jenkins-readonly"
    root.mkdir()
    secret_file = root / ".env"
    secret_file.write_text("JENKINS_TOKEN=SUPERSECRET\n", encoding="utf-8")
    (root / "server.py").write_text("print('safe')\n", encoding="utf-8")

    result = module.inspect_jenkins_candidate_roots((root,))

    assert result["status"] == "CONFIG_CANDIDATE_OBSERVED"
    assert result["candidate_directories_observed"] == 1
    assert result["candidate_files_observed"] == 2
    assert result["env_like_files_observed"] == 1
    assert result["credential_values_inspected"] is False
    assert "SUPERSECRET" not in repr(result)


def test_scheduler_parsers_project_only_explicit_ansible_names():
    module = load_module()

    unit_text = """
ansible-refresh.service enabled enabled
infra-assurance.service enabled enabled
not*safe.service enabled enabled
"""
    timer_text = """
Sat 2026-08-29 14:00:00 CEST 1h left Sat 2026-08-29 13:00:00 CEST 5min ago ansible-nightly.timer ansible-nightly.service
Sat 2026-08-29 15:00:00 CEST 2h left Sat 2026-08-29 12:00:00 CEST 1h ago apt-daily.timer apt-daily.service
"""

    assert module._ansible_units_from_unit_files(unit_text) == ["ansible-refresh.service"]
    assert module._ansible_timers_from_timer_list(timer_text) == ["ansible-nightly.timer"]


def test_source_preference_is_jenkins_then_scheduler_then_none():
    module = load_module()

    jenkins = {"status": "CONFIG_CANDIDATE_OBSERVED"}
    scheduler = {"source_status": "COMPLETE", "explicit_scheduler_signal_count": 2}
    assert module.choose_preferred_source(jenkins, scheduler) == "JENKINS_READ_ONLY_SOURCE_CANDIDATE"

    jenkins = {"status": "NONE_OBSERVED_IN_BOUNDED_PATHS"}
    assert module.choose_preferred_source(jenkins, scheduler) == "MANAGEMENT_HOST_SCHEDULER_SOURCE_CANDIDATE"

    scheduler = {"source_status": "COMPLETE", "explicit_scheduler_signal_count": 0}
    assert module.choose_preferred_source(jenkins, scheduler) == "NO_AUTHORITATIVE_OUTCOME_SOURCE_OBSERVED_IN_BOUNDED_DISCOVERY"


def test_source_code_preserves_read_only_boundary():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "jenkins_api_invoked: False" in text
    assert "jenkins_credentials_inspected: False" in text
    assert "cron_contents_inspected: False" in text
    assert "execution_outcome_status: UNKNOWN" in text
    assert "successful_execution_claims: 0" in text
    assert "idempotence_claims: 0" in text
    assert "drift_claims: 0" in text

    forbidden = (
        "ansible-playbook ",
        "ansible-runner run ",
        "ansible-navigator run ",
        "curl ",
        "requests.get",
        "urllib.request.urlopen",
        "journalctl",
        "systemctl start",
        "systemctl restart",
        "systemctl enable",
        "crontab -e",
    )
    for token in forbidden:
        assert token not in text
