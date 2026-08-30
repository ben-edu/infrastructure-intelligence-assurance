from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path


SCRIPT = Path("scripts/discovery/m8_runtime_hardening_baseline_probe.py")


def load_module():
    spec = importlib.util.spec_from_file_location("m8_runtime_hardening_baseline", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parser_preserves_repeated_directives():
    module = load_module()
    unit = module.parse_unit(
        """
[Service]
User=infra-assurance
ExecStart=/usr/bin/python3 -m infra_assurance.kubernetes_runtime
ExecStartPost=/usr/bin/python3 -m infra_assurance.incident_runtime
ExecStartPost=/usr/bin/python3 -m infra_assurance.operator_attention_incident
"""
    )
    assert module._last(unit, "Service", "User") == "infra-assurance"
    assert len(module._values(unit, "Service", "ExecStartPost")) == 2
    assert module._module_entrypoints(unit) == [
        "infra_assurance.kubernetes_runtime",
        "infra_assurance.incident_runtime",
        "infra_assurance.operator_attention_incident",
    ]


def test_repository_declarations_preserve_manager_default_boundary():
    module = load_module()
    declared = module.declared_state(Path.cwd())
    assert declared["identity"] == {"user": "infra-assurance", "group": "infra-assurance"}
    assert declared["sandbox"]["no_new_privileges"] is True
    assert declared["sandbox"]["private_tmp"] is True
    assert declared["sandbox"]["protect_system"] == "strict"
    assert set(declared["sandbox"]["read_write_paths"]) == set(module.WRITABLE_PATHS)
    assert declared["schedule"]["on_unit_active_sec"] == "5min"
    assert declared["failure"]["timeout_start_sec"] == "MANAGER_DEFAULT"
    assert declared["failure"]["restart"] == "MANAGER_DEFAULT"
    assert declared["failure"]["on_failure_declared"] is False
    assert declared["runtime"]["explicit_process_lock"] is False
    assert declared["atomic"]["entrypoints_total"] == 12
    assert declared["atomic"]["entrypoints_using_atomic_helper"] == 12
    assert declared["atomic"]["atomic_replace"] is True
    assert declared["atomic"]["explicit_history_lock"] is False


def test_metadata_inspection_does_not_open_or_project_artifacts(tmp_path: Path):
    module = load_module()
    root = tmp_path / "evidence"
    root.mkdir()
    secret = "DO_NOT_PROJECT_SUPERSECRET"
    (root / "artifact.json").write_text(secret, encoding="utf-8")
    account = {"uid": os.getuid(), "gid": os.getgid(), "gids": {os.getgid()}}
    result = module.metadata_summary(root, account, os.getuid(), os.getgid())
    assert result["status"] == "OBSERVED"
    assert result["entries_inspected"] == 2
    assert result["artifact_contents_inspected"] is False
    assert result["artifact_names_projected"] is False
    assert secret not in repr(result)
    assert "artifact.json" not in repr(result)


def test_backup_signal_scan_reads_filenames_only(tmp_path: Path):
    module = load_module()
    (tmp_path / "infra-assurance-backup.timer").write_text(
        "PASSWORD=DO_NOT_PROJECT_SUPERSECRET\n", encoding="utf-8"
    )
    result = module.backup_scheduler_names((tmp_path,))
    assert result["status"] == "OBSERVED"
    assert result["matching_names"] == ["infra-assurance-backup.timer"]
    assert result["file_contents_inspected"] is False
    assert "DO_NOT_PROJECT_SUPERSECRET" not in repr(result)


def test_repository_only_module_absence_is_not_installed_runtime_drift(tmp_path: Path):
    module = load_module()
    repo_package = tmp_path / "repo/src/infra_assurance"
    installed = tmp_path / "installed"
    repo_package.mkdir(parents=True)
    installed.mkdir()
    for name in ("__init__.py", "entry.py", "dependency.py"):
        (repo_package / name).write_text(f"# {name}\n", encoding="utf-8")
        shutil.copyfile(repo_package / name, installed / name)
    (repo_package / "repository_only.py").write_text("VALUE = 1\n", encoding="utf-8")
    result = module.installed_code_match(
        tmp_path / "repo", installed, ["infra_assurance.entry"]
    )
    assert result["installed_runtime_matches_repository"] is True
    assert result["missing_entrypoint_modules"] == []
    assert result["repository_only_modules_are_not_runtime_drift"] is True


def _live_fixture(tmp_path: Path):
    units = tmp_path / "units"
    units.mkdir()
    service = units / "infra-assurance-kubernetes.service"
    timer = units / "infra-assurance-kubernetes.timer"
    shutil.copyfile(Path("systemd") / service.name, service)
    shutil.copyfile(Path("systemd") / timer.name, timer)
    installed = tmp_path / "installed"
    shutil.copytree(Path("src/infra_assurance"), installed)
    state = tmp_path / "state"
    for name in ("evidence", "history", "git", "declared"):
        target = state / name
        target.mkdir(parents=True)
        (target / "metadata-only.json").write_text("DO_NOT_PROJECT", encoding="utf-8")
    scheduler = tmp_path / "scheduler"
    scheduler.mkdir()
    return units, service, timer, installed, state, scheduler


def _runner(service_path: Path, timer_path: Path, *, sandbox: bool = True):
    commands: list[list[str]] = []
    service = f"""LoadState=loaded
ActiveState=inactive
SubState=dead
UnitFileState=static
Type=oneshot
User=infra-assurance
Group=infra-assurance
DynamicUser=no
NoNewPrivileges={'yes' if sandbox else 'no'}
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/infra-assurance/evidence /var/lib/infra-assurance/history /var/lib/infra-assurance/git /var/lib/infra-assurance/declared
ReadOnlyPaths=/etc/infra-assurance
FragmentPath={service_path}
DropInPaths=
TimeoutStartUSec=1min 30s
RuntimeMaxUSec=infinity
Restart=no
Result=success
ExecMainCode=exited
ExecMainStatus=0
NRestarts=0
FailureAction=none
OnFailure=
StandardOutput=journal
StandardError=inherit
ExecMainStartTimestampMonotonic=1000000
ExecMainExitTimestampMonotonic=3500000
"""
    timer = f"""LoadState=loaded
ActiveState=active
SubState=waiting
UnitFileState=enabled
Unit=infra-assurance-kubernetes.service
Persistent=yes
AccuracyUSec=15s
RandomizedDelayUSec=0
LastTriggerUSec=recorded
NextElapseUSecMonotonic=5000000
TimersMonotonic={{ OnBootUSec=1min ; next_elapse=1min }} {{ OnUnitActiveUSec=5min ; next_elapse=5min }}
FragmentPath={timer_path}
DropInPaths=
"""

    def run(command: list[str]):
        commands.append(command)
        if command[2] == "infra-assurance-kubernetes.service":
            return 0, service
        if command[2] == "infra-assurance-kubernetes.timer":
            return 0, timer
        return 1, ""

    return run, commands


def _collect_live(tmp_path: Path, monkeypatch, *, sandbox: bool = True):
    module = load_module()
    units, service, timer, installed, state, scheduler = _live_fixture(tmp_path)
    runner, commands = _runner(service, timer, sandbox=sandbox)
    monkeypatch.setattr(
        module, "_account", lambda _user: {"uid": 12345, "gid": 12345, "gids": {12345}}
    )

    def safe_metadata(root: Path, *_args, **_kwargs):
        return {
            "status": "OBSERVED",
            "coverage": "COMPLETE",
            "entries_inspected": 1,
            "metadata_failures": 0,
            "truncated": False,
            "symlink_count": 0,
            "world_writable_count": 0,
            "owner_mismatch_count": 0,
            "group_mismatch_count": 0,
            "runtime_writable_by_posix_mode_count": 0 if root == installed else 1,
            "runtime_writability_unknown_count": 0,
            "ownership_mode_groups": [],
            "artifact_contents_inspected": False,
            "artifact_names_projected": False,
        }

    monkeypatch.setattr(module, "metadata_summary", safe_metadata)
    result = module.collect(
        Path.cwd(),
        runner=runner,
        state_root=state,
        installed=installed,
        fragment_roots=(units,),
        scheduler_dirs=(scheduler,),
    )
    return module, result, commands


def test_complete_probe_separates_classes_and_selects_one_change(tmp_path: Path, monkeypatch):
    module, result, commands = _collect_live(tmp_path, monkeypatch)
    assert result["baseline_status"] == "COMPLETE"
    assert result["mutation_allowed"] is False
    assert tuple(result["findings"]) == module.CLASSES
    assert result["findings"]["FAILED_TO_OBSERVE"] == []
    assert len(result["findings"]["REQUIRES_CHANGE"]) == 1
    assert result["findings"]["REQUIRES_CHANGE"][0]["id"] == (
        "PIN_EXPLICIT_SERVICE_START_TIMEOUT"
    )
    observed = {item["id"]: item for item in result["findings"]["OBSERVED"]}
    assert observed["INSTALLED_SERVICE_STATE"]["evidence"]["last_duration_seconds"] == 2.5
    assert observed["INSTALLED_SERVICE_STATE"]["evidence"]["fragment_matches_repository"] is True
    assert observed["INSTALLED_TIMER_STATE"]["evidence"]["monotonic_triggers"] == {
        "OnBootUSec": "1min",
        "OnUnitActiveUSec": "5min",
    }
    assert all(command[:2] == ["systemctl", "show"] for command in commands)
    assert all("Environment" not in " ".join(command) for command in commands)
    assert all("ExecStart" not in " ".join(command) for command in commands)


def test_sandbox_drift_preempts_timeout_candidate(tmp_path: Path, monkeypatch):
    _module, result, _commands = _collect_live(tmp_path, monkeypatch, sandbox=False)
    change = result["findings"]["REQUIRES_CHANGE"][0]
    assert change["id"] == "ALIGN_EFFECTIVE_SYSTEMD_SANDBOX"
    assert change["evidence"]["observed_sandbox"]["no_new_privileges"] is False
    assert "declared_timeout" not in change["evidence"]


def test_state_ownership_drift_preempts_timeout_candidate():
    module = load_module()
    declared = module.declared_state(Path.cwd())
    live = {
        "service": {
            **declared["identity"],
            **declared["sandbox"],
            "fragment_matches_repository": True,
        },
        "timer": {"fragment_matches_repository": True},
    }
    storage = {
        "state": {
            "evidence": {
                "status": "OBSERVED",
                "world_writable_count": 0,
                "owner_mismatch_count": 1,
                "group_mismatch_count": 0,
            }
        },
        "code": {"runtime_writable_by_posix_mode_count": 0},
    }
    code = {"status": "OBSERVED", "installed_runtime_matches_repository": True}
    assert module.smallest_change(declared, live, storage, code)["id"] == (
        "ALIGN_STATE_ARTIFACT_OWNERSHIP_AND_MODES"
    )


def test_runtime_module_drift_recommendation_carries_module_evidence():
    module = load_module()
    declared = module.declared_state(Path.cwd())
    live = {
        "service": {
            **declared["identity"],
            **declared["sandbox"],
            "fragment_matches_repository": True,
        },
        "timer": {"fragment_matches_repository": True},
    }
    storage = {
        "state": {},
        "code": {"runtime_writable_by_posix_mode_count": 0},
    }
    code = {
        "status": "OBSERVED",
        "installed_runtime_matches_repository": False,
        "mismatched_modules": ["__init__.py"],
        "unexpected_modules": [],
        "missing_entrypoint_modules": [],
    }
    change = module.smallest_change(declared, live, storage, code)
    assert change["id"] == "RECONCILE_INSTALLED_RUNTIME_MODULES"
    assert change["evidence"] == {
        "implementation_status": "NOT_IMPLEMENTED",
        "installed_runtime_matches_repository": False,
        "mismatched_modules": ["__init__.py"],
        "unexpected_modules": [],
        "missing_entrypoint_modules": [],
    }


def test_failed_observation_remains_failure_and_backup_unknown(tmp_path: Path, monkeypatch):
    module = load_module()
    _units, _service, _timer, installed, state, scheduler = _live_fixture(tmp_path)
    monkeypatch.setattr(
        module, "_account", lambda _user: {"uid": 12345, "gid": 12345, "gids": {12345}}
    )
    result = module.collect(
        Path.cwd(),
        runner=lambda _command: (1, ""),
        state_root=state,
        installed=installed,
        scheduler_dirs=(scheduler,),
    )
    assert result["baseline_status"] == "INCOMPLETE"
    failed = {item["id"] for item in result["findings"]["FAILED_TO_OBSERVE"]}
    assert {"INSTALLED_SERVICE_STATE", "INSTALLED_TIMER_STATE"} <= failed
    backup = next(
        item
        for item in result["findings"]["UNKNOWN"]
        if item["id"] == "PLATFORM_EVIDENCE_HISTORY_BACKUP_STATUS"
    )
    assert backup["evidence"]["none_observed_is_not_unprotected"] is True


def test_source_contains_no_mutating_or_sensitive_observation_commands():
    text = SCRIPT.read_text(encoding="utf-8")
    forbidden = (
        "journalctl",
        "systemctl start",
        "systemctl restart",
        "systemctl enable",
        "systemctl daemon-reload",
        "sudo ",
        "chmod ",
        "chown ",
        "setfacl ",
        "kubectl ",
        "EnvironmentFile=",
    )
    for token in forbidden:
        assert token not in text
    for key in (
        "environment_file_contents_inspected",
        "artifact_contents_inspected",
        "journal_messages_inspected",
        "secret_values_inspected",
    ):
        assert f'"{key}": False' in text
    assert '"mutation_allowed": False' in text
