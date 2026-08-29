from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "discovery" / "m6_terraform_readonly_plan_evidence.py"
SPEC = importlib.util.spec_from_file_location("m6_terraform_readonly_plan_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_commands_are_read_only_and_do_not_write_saved_plan():
    configuration = MODULE._command("configuration_vs_state")
    refresh_only = MODULE._command("refresh_only")

    for command in (configuration, refresh_only):
        rendered = " ".join(command)
        assert command[:2] == ["terraform", "plan"]
        assert "-lock=false" in command
        assert "-input=false" in command
        assert "-detailed-exitcode" in command
        assert "-json" in command
        assert "-out" not in rendered
        assert "apply" not in command
        assert "state" not in command
        assert "import" not in command
    assert "-refresh=false" in configuration
    assert "-refresh-only" in refresh_only


def test_json_stream_projects_only_planned_action_counts():
    payload = b"\n".join(
        [
            b'{"type":"planned_change","change":{"resource":{"addr":"proxmox_vm_qemu.private-name"},"action":"update"}}',
            b'{"type":"planned_change","change":{"resource":{"addr":"proxmox_vm_qemu.secret-name"},"action":["delete","create"]}}',
            b'{"type":"diagnostic","diagnostic":{"summary":"private diagnostic text"}}',
        ]
    )

    result = MODULE._parse_json_stream(payload)

    assert result["planned_action_counts"] == {"replace": 1, "update": 1}
    assert result["drift_action_counts"] == {}
    assert result["planned_change_events"] == 2
    assert result["resource_drift_events"] == 0
    assert result["recognized_planned_action_events"] == 2
    rendered = repr(result)
    assert "private-name" not in rendered
    assert "secret-name" not in rendered
    assert "private diagnostic text" not in rendered


def test_json_stream_classifies_resource_drift_without_identity():
    payload = b"\n".join(
        [
            b'{"type":"resource_drift","change":{"resource":{"addr":"proxmox_vm_qemu.private-one"},"action":"update"}}',
            b'{"type":"resource_drift","change":{"resource":{"addr":"proxmox_vm_qemu.private-two"},"action":"delete"}}',
            b'{"type":"planned_change","change":{"resource":{"addr":"proxmox_vm_qemu.private-three"},"action":"noop"}}',
        ]
    )

    result = MODULE._parse_json_stream(payload)

    assert result["drift_action_counts"] == {"delete": 1, "update": 1}
    assert result["planned_action_counts"] == {"noop": 1}
    assert result["resource_drift_events"] == 2
    assert result["recognized_drift_action_events"] == 2
    rendered = repr(result)
    assert "private-one" not in rendered
    assert "private-two" not in rendered
    assert "private-three" not in rendered


def test_destructive_status_fails_closed_for_unclassified_changes():
    unclassified = MODULE._empty_mode("configuration_vs_state", "COMPLETE_CHANGES_UNCLASSIFIED")
    unclassified["change_signal"] = "CHANGES_OBSERVED"
    assert MODULE._destructive_status(unclassified) == "UNKNOWN"

    destructive = MODULE._empty_mode("configuration_vs_state", "COMPLETE_CHANGES_OBSERVED")
    destructive["action_counts"] = {"delete": 1}
    assert MODULE._destructive_status(destructive) == "DESTRUCTIVE_ACTIONS_OBSERVED"


def test_drift_signal_uses_refresh_only_completion_boundary():
    no_change = MODULE._empty_mode("refresh_only", "COMPLETE_NO_CHANGES")
    assert MODULE._drift_signal_status(no_change) == "NONE_OBSERVED_IN_COMPLETE_REFRESH_ONLY_PLAN"

    changed = MODULE._empty_mode("refresh_only", "COMPLETE_CHANGES_UNCLASSIFIED")
    changed["change_signal"] = "CHANGES_OBSERVED"
    assert MODULE._drift_signal_status(changed) == "STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED"

    failed = MODULE._empty_mode("refresh_only", "FAILED_TO_OBSERVE")
    assert MODULE._drift_signal_status(failed) == "UNKNOWN"


def test_discover_preserves_apply_and_coverage_unknown(monkeypatch, tmp_path):
    roots = {"bm1": tmp_path / "bm1", "bm2": tmp_path / "bm2"}
    for root in roots.values():
        root.mkdir()

    def fake_run(root: Path, mode: str):
        result = MODULE._empty_mode(mode, "COMPLETE_NO_CHANGES")
        result["terraform_exit_code"] = 0
        result["change_signal"] = "NONE_OBSERVED"
        return result

    monkeypatch.setattr(MODULE, "_run_plan", fake_run)
    result = MODULE.discover(roots)

    assert result["source_status"] == "COMPLETE"
    assert result["roots_configuration_plan_complete"] == 2
    assert result["roots_refresh_only_plan_complete"] == 2
    assert result["state_tracked_refresh_drift_status"] == "NONE_OBSERVED_IN_COMPLETE_REFRESH_ONLY_PLAN"
    assert result["destructive_change_status"] == "NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN"
    assert result["apply_result_status"] == "UNKNOWN"
    assert result["live_resource_coverage_status"] == "UNKNOWN"
    assert result["state_backed_coverage_status"] == "UNKNOWN"
