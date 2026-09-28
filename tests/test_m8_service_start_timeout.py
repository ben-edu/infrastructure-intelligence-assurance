from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reconcile-service-start-timeout.py"
SERVICE_UNIT = ROOT / "systemd" / "infra-assurance-kubernetes.service"
TIMER_UNIT = ROOT / "systemd" / "infra-assurance-kubernetes.timer"


def load_module():
    spec = importlib.util.spec_from_file_location("m8_service_start_timeout", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path):
    source = tmp_path / "repository" / "infra-assurance-kubernetes.service"
    target = tmp_path / "installed" / "infra-assurance-kubernetes.service"
    backup = tmp_path / "backups"
    source.parent.mkdir()
    target.parent.mkdir()
    predecessor = """[Unit]
Description=Test

[Service]
Type=oneshot
ExecStart=/bin/true
"""
    hardened = predecessor.replace(
        "Type=oneshot\n", "Type=oneshot\nTimeoutStartSec=4min\n"
    )
    source.write_text(hardened, encoding="utf-8")
    target.write_text(predecessor, encoding="utf-8")
    source.chmod(0o644)
    target.chmod(0o644)
    return source, target, backup, _sha256(target)


def _runner(target: Path, *, active: bool = False, hold_first_reload: bool = False):
    commands: list[list[str]] = []
    state = {
        "effective": "infinity",
        "reloads": 0,
    }

    def run(command: list[str]):
        commands.append(command)
        if command[:2] == ["systemctl", "show"]:
            return 0, f"""LoadState=loaded
ActiveState={'active' if active else 'inactive'}
SubState={'running' if active else 'dead'}
FragmentPath={target}
DropInPaths=
TimeoutStartUSec={state['effective']}
"""
        if command == ["systemctl", "daemon-reload"]:
            state["reloads"] += 1
            if not (hold_first_reload and state["reloads"] == 1):
                payload = target.read_text(encoding="utf-8")
                state["effective"] = (
                    "4min" if "TimeoutStartSec=4min" in payload else "infinity"
                )
            return 0, ""
        return 1, ""

    return run, commands, state


def test_repository_unit_pins_timeout_below_timer_cadence():
    service = SERVICE_UNIT.read_text(encoding="utf-8")
    timer = TIMER_UNIT.read_text(encoding="utf-8")
    assert service.count("TimeoutStartSec=4min") == 1
    assert "OnUnitActiveSec=5min" in timer


def test_plan_is_read_only_and_accepts_only_known_predecessor(tmp_path: Path):
    module = load_module()
    source, target, backup, predecessor = _fixture(tmp_path)
    runner, commands, _state = _runner(target)
    before = target.read_bytes()
    inode = target.stat().st_ino

    result = module.observe(
        source,
        target,
        runner=runner,
        accepted_predecessor_sha256=predecessor,
        expected_repository_sha256=_sha256(source),
    )

    assert result["status"] == "CHANGE_REQUIRED"
    assert result["mutation_allowed"] is False
    assert result["mutation_performed"] is False
    assert result["declared_timeout_start_sec"] == "4min"
    assert result["effective_timeout_start_usec"] == "infinity"
    assert result["source_contents_projected"] is False
    assert result["installed_contents_projected"] is False
    assert target.read_bytes() == before
    assert target.stat().st_ino == inode
    assert not backup.exists()
    assert commands and all(command[:2] == ["systemctl", "show"] for command in commands)


def test_apply_is_bounded_atomic_backed_up_and_idempotent(tmp_path: Path):
    module = load_module()
    source, target, backup, predecessor = _fixture(tmp_path)
    runner, commands, state = _runner(target)
    uid, gid = os.getuid(), os.getgid()
    original_inode = target.stat().st_ino

    result = module.apply_reconciliation(
        source,
        target,
        backup,
        runner=runner,
        uid=uid,
        gid=gid,
        accepted_predecessor_sha256=predecessor,
        expected_repository_sha256=_sha256(source),
    )

    assert result["status"] == "RECONCILED"
    assert result["mutation_allowed"] is True
    assert result["mutation_performed"] is True
    assert result["rollback_token"] == predecessor
    assert result["systemd_unit_mutation_performed"] is True
    assert result["daemon_reload_performed"] is True
    assert result["service_start_performed"] is False
    assert result["service_restart_performed"] is False
    assert result["timer_mutation_performed"] is False
    assert result["infrastructure_mutation_performed"] is False
    assert _sha256(target) == _sha256(source)
    assert target.stat().st_ino != original_inode
    assert target.stat().st_mode & 0o777 == 0o644
    rollback = backup / f"{module.SERVICE}.{predecessor}.bak"
    assert rollback.is_file()
    assert rollback.stat().st_mode & 0o777 == 0o600
    assert state["effective"] == "4min"
    assert ["systemctl", "daemon-reload"] in commands
    assert all(
        command[:2] not in (["systemctl", "start"], ["systemctl", "restart"])
        for command in commands
    )

    repeat = module.apply_reconciliation(
        source,
        target,
        backup,
        runner=runner,
        uid=uid,
        gid=gid,
        accepted_predecessor_sha256=predecessor,
        expected_repository_sha256=_sha256(source),
    )
    assert repeat["status"] == "ALREADY_RECONCILED"
    assert repeat["mutation_performed"] is False


def test_apply_restores_predecessor_when_post_reload_verification_fails(
    tmp_path: Path,
):
    module = load_module()
    source, target, backup, predecessor = _fixture(tmp_path)
    original = target.read_bytes()
    runner, _commands, state = _runner(target, hold_first_reload=True)
    uid, gid = os.getuid(), os.getgid()

    with pytest.raises(
        module.ReconciliationError, match="POST_RELOAD_VERIFICATION_FAILED"
    ):
        module.apply_reconciliation(
            source,
            target,
            backup,
            runner=runner,
            uid=uid,
            gid=gid,
            accepted_predecessor_sha256=predecessor,
            expected_repository_sha256=_sha256(source),
        )

    assert target.read_bytes() == original
    assert state["effective"] == "infinity"


def test_apply_completes_interrupted_daemon_reload_with_original_rollback_token(
    tmp_path: Path,
):
    module = load_module()
    source, target, backup, predecessor = _fixture(tmp_path)
    runner, _commands, state = _runner(target)
    uid, gid = os.getuid(), os.getgid()
    first = module.apply_reconciliation(
        source,
        target,
        backup,
        runner=runner,
        uid=uid,
        gid=gid,
        accepted_predecessor_sha256=predecessor,
        expected_repository_sha256=_sha256(source),
    )
    assert first["rollback_token"] == predecessor

    state["effective"] = "infinity"
    recovered = module.apply_reconciliation(
        source,
        target,
        backup,
        runner=runner,
        uid=uid,
        gid=gid,
        accepted_predecessor_sha256=predecessor,
        expected_repository_sha256=_sha256(source),
    )

    assert recovered["status"] == "RECONCILED"
    assert recovered["rollback_token"] == predecessor
    assert recovered["systemd_unit_mutation_performed"] is False
    assert recovered["daemon_reload_performed"] is True
    assert state["effective"] == "4min"


def test_apply_rejects_active_service_without_mutation(tmp_path: Path):
    module = load_module()
    source, target, backup, predecessor = _fixture(tmp_path)
    original = target.read_bytes()
    runner, commands, _state = _runner(target, active=True)

    with pytest.raises(module.ReconciliationError, match="SERVICE_NOT_INACTIVE"):
        module.apply_reconciliation(
            source,
            target,
            backup,
            runner=runner,
            uid=os.getuid(),
            gid=os.getgid(),
            accepted_predecessor_sha256=predecessor,
            expected_repository_sha256=_sha256(source),
        )

    assert target.read_bytes() == original
    assert not backup.exists()
    assert ["systemctl", "daemon-reload"] not in commands


def test_apply_rejects_unexpected_installed_unit(tmp_path: Path):
    module = load_module()
    source, target, backup, predecessor = _fixture(tmp_path)
    target.write_text("[Service]\nExecStart=/bin/false\n", encoding="utf-8")
    runner, _commands, _state = _runner(target)

    result = module.observe(
        source,
        target,
        runner=runner,
        accepted_predecessor_sha256=predecessor,
        expected_repository_sha256=_sha256(source),
    )
    assert result["status"] == "UNEXPECTED_INSTALLED_UNIT"
    with pytest.raises(
        module.ReconciliationError, match="APPLY_BLOCKED_UNEXPECTED_INSTALLED_UNIT"
    ):
        module.apply_reconciliation(
            source,
            target,
            backup,
            runner=runner,
            uid=os.getuid(),
            gid=os.getgid(),
            accepted_predecessor_sha256=predecessor,
            expected_repository_sha256=_sha256(source),
        )
    assert not backup.exists()


def test_plan_rejects_repository_unit_outside_exact_reviewed_hash(tmp_path: Path):
    module = load_module()
    source, target, _backup, predecessor = _fixture(tmp_path)
    reviewed_hash = _sha256(source)
    source.write_text(
        source.read_text(encoding="utf-8") + "Restart=on-failure\n",
        encoding="utf-8",
    )
    runner, _commands, _state = _runner(target)

    with pytest.raises(
        module.ReconciliationError, match="REPOSITORY_UNIT_HASH_UNEXPECTED"
    ):
        module.observe(
            source,
            target,
            runner=runner,
            accepted_predecessor_sha256=predecessor,
            expected_repository_sha256=reviewed_hash,
        )


def test_rollback_restores_exact_predecessor_and_reloads_only(tmp_path: Path):
    module = load_module()
    source, target, backup, predecessor = _fixture(tmp_path)
    original = target.read_bytes()
    runner, commands, state = _runner(target)
    uid, gid = os.getuid(), os.getgid()
    applied = module.apply_reconciliation(
        source,
        target,
        backup,
        runner=runner,
        uid=uid,
        gid=gid,
        accepted_predecessor_sha256=predecessor,
        expected_repository_sha256=_sha256(source),
    )
    reconciled_hash = _sha256(target)

    result = module.rollback_reconciliation(
        source,
        target,
        backup,
        applied["rollback_token"],
        runner=runner,
        uid=uid,
        gid=gid,
    )

    assert result["status"] == "ROLLED_BACK"
    assert result["before_sha256"] == reconciled_hash
    assert result["after_sha256"] == predecessor
    assert target.read_bytes() == original
    assert state["effective"] == "infinity"
    assert (backup / f"{module.SERVICE}.{reconciled_hash}.bak").is_file()
    assert all(
        command[:2] not in (["systemctl", "start"], ["systemctl", "restart"])
        for command in commands
    )


def test_helper_scope_excludes_service_start_timer_and_infrastructure_mutation():
    helper = SCRIPT.read_text(encoding="utf-8")
    for forbidden in (
        "systemctl start",
        "systemctl restart",
        "systemctl stop",
        "systemctl enable",
        "kubectl",
        "ansible-playbook",
        "terraform apply",
    ):
        assert forbidden not in helper
    assert 'SERVICE = "infra-assurance-kubernetes.service"' in helper
    assert 'EXPECTED_TIMEOUT = "4min"' in helper
    assert '"service_start_performed": False' in helper
    assert '"service_restart_performed": False' in helper
    assert '"timer_mutation_performed": False' in helper
    assert '"infrastructure_mutation_performed": False' in helper
