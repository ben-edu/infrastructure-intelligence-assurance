#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable


VERSION = "0.1"
SCOPE = "INFRA_ASSURANCE_SERVICE_START_TIMEOUT"
SERVICE = "infra-assurance-kubernetes.service"
EXPECTED_TIMEOUT = "4min"
PREDECESSOR_EFFECTIVE_TIMEOUT = "infinity"
ACCEPTED_PREDECESSOR_SHA256 = (
    "5bb777fdef10a3a38756924042ad9408134cbf01df034f6542ae053d55f90e0c"
)
EXPECTED_REPOSITORY_SHA256 = (
    "a2f0c9a489d87d99c5edcf4de097ab45580a41f8877fd6a9afc53a73e64e8558"
)
REPOSITORY_UNIT = Path(__file__).resolve().parents[1] / "systemd" / SERVICE
INSTALLED_UNIT = Path("/etc/systemd/system") / SERVICE
BACKUP_ROOT = Path("/var/lib/infra-assurance/runtime-reconciliation")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
Runner = Callable[[list[str]], tuple[int, str]]


class ReconciliationError(RuntimeError):
    pass


def _run(command: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return -1, ""
    return result.returncode, result.stdout


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_file(path: Path, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ReconciliationError(f"{label}_UNAVAILABLE") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise ReconciliationError(f"{label}_NOT_REGULAR_FILE")
    return metadata


def _directory(path: Path, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ReconciliationError(f"{label}_UNAVAILABLE") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ReconciliationError(f"{label}_NOT_DIRECTORY")
    return metadata


def _metadata(metadata: os.stat_result) -> dict[str, Any]:
    return {
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        "kind": "file",
    }


def _validate_repository_unit(path: Path) -> None:
    _regular_file(path, "REPOSITORY_UNIT")
    section = ""
    timeouts: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if section == "Service" and line.startswith("TimeoutStartSec="):
            timeouts.append(line.split("=", 1)[1].strip())
    if timeouts != [EXPECTED_TIMEOUT]:
        raise ReconciliationError("REPOSITORY_TIMEOUT_CONTRACT_INVALID")


def _parse_show(stdout: str) -> dict[str, str]:
    allowed = {
        "LoadState",
        "ActiveState",
        "SubState",
        "FragmentPath",
        "DropInPaths",
        "TimeoutStartUSec",
    }
    return {
        key: value.strip()
        for line in stdout.splitlines()
        if "=" in line
        for key, value in [line.split("=", 1)]
        if key in allowed
    }


def _systemd_state(runner: Runner) -> dict[str, Any]:
    command = [
        "systemctl",
        "show",
        SERVICE,
        "--no-pager",
        "--property=LoadState",
        "--property=ActiveState",
        "--property=SubState",
        "--property=FragmentPath",
        "--property=DropInPaths",
        "--property=TimeoutStartUSec",
    ]
    returncode, stdout = runner(command)
    values = _parse_show(stdout)
    if returncode != 0 or values.get("LoadState") != "loaded":
        raise ReconciliationError("INSTALLED_SERVICE_STATE_UNAVAILABLE")
    return {
        "active_state": values.get("ActiveState", "UNKNOWN"),
        "sub_state": values.get("SubState", "UNKNOWN"),
        "fragment_path": values.get("FragmentPath", "UNKNOWN"),
        "dropin_count": len(shlex.split(values.get("DropInPaths", ""))),
        "effective_timeout_start_usec": values.get("TimeoutStartUSec", "UNKNOWN"),
    }


def observe(
    source: Path,
    target: Path,
    *,
    runner: Runner = _run,
    accepted_predecessor_sha256: str = ACCEPTED_PREDECESSOR_SHA256,
    expected_repository_sha256: str = EXPECTED_REPOSITORY_SHA256,
) -> dict[str, Any]:
    _validate_repository_unit(source)
    source_metadata = _regular_file(source, "REPOSITORY_UNIT")
    target_metadata = _regular_file(target, "INSTALLED_UNIT")
    repository_hash = _sha256(source)
    if repository_hash != expected_repository_sha256:
        raise ReconciliationError("REPOSITORY_UNIT_HASH_UNEXPECTED")
    installed_hash = _sha256(target)
    systemd = _systemd_state(runner)

    if systemd["dropin_count"]:
        status = "UNEXPECTED_DROPINS"
    elif systemd["fragment_path"] != str(target):
        status = "UNEXPECTED_FRAGMENT_PATH"
    elif installed_hash == repository_hash:
        if systemd["effective_timeout_start_usec"] == EXPECTED_TIMEOUT:
            status = "ALREADY_RECONCILED"
        elif (
            systemd["effective_timeout_start_usec"]
            == PREDECESSOR_EFFECTIVE_TIMEOUT
        ):
            status = "DAEMON_RELOAD_REQUIRED"
        else:
            status = "UNEXPECTED_EFFECTIVE_TIMEOUT"
    elif installed_hash == accepted_predecessor_sha256:
        status = (
            "CHANGE_REQUIRED"
            if systemd["effective_timeout_start_usec"]
            == PREDECESSOR_EFFECTIVE_TIMEOUT
            else "UNEXPECTED_EFFECTIVE_TIMEOUT"
        )
    else:
        status = "UNEXPECTED_INSTALLED_UNIT"

    return {
        "reconciliation_version": VERSION,
        "scope": SCOPE,
        "service": SERVICE,
        "status": status,
        "mutation_allowed": False,
        "mutation_performed": False,
        "repository_sha256": repository_hash,
        "installed_sha256": installed_hash,
        "accepted_predecessor_sha256": accepted_predecessor_sha256,
        "repository_metadata": _metadata(source_metadata),
        "installed_metadata": _metadata(target_metadata),
        "declared_timeout_start_sec": EXPECTED_TIMEOUT,
        **systemd,
        "source_contents_projected": False,
        "installed_contents_projected": False,
        "systemd_unit_mutation_performed": False,
        "daemon_reload_performed": False,
        "service_start_performed": False,
        "service_restart_performed": False,
        "timer_mutation_performed": False,
        "infrastructure_mutation_performed": False,
    }


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_install(
    target: Path,
    payload: bytes,
    *,
    uid: int,
    gid: int,
    mode: int,
) -> None:
    _directory(target.parent, "TARGET_PARENT")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    descriptor_open = True
    try:
        os.fchmod(descriptor, mode)
        os.fchown(descriptor, uid, gid)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor_open = False
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        _fsync_directory(target.parent)
    except Exception:
        if descriptor_open:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
        raise


def _ensure_backup_root(path: Path, *, uid: int, gid: int) -> None:
    _directory(path.parent, "BACKUP_PARENT")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        path.mkdir(mode=0o700)
        metadata = path.lstat()
    except OSError as error:
        raise ReconciliationError("BACKUP_ROOT_UNAVAILABLE") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ReconciliationError("BACKUP_ROOT_NOT_DIRECTORY")
    os.chown(path, uid, gid)
    os.chmod(path, 0o700)


def _backup_path(backup_root: Path, token: str) -> Path:
    return backup_root / f"{SERVICE}.{token}.bak"


def _backup(
    target: Path,
    backup_root: Path,
    target_hash: str,
    *,
    uid: int,
    gid: int,
) -> Path:
    _ensure_backup_root(backup_root, uid=uid, gid=gid)
    backup = _backup_path(backup_root, target_hash)
    if backup.exists() or backup.is_symlink():
        _regular_file(backup, "ROLLBACK_BACKUP")
        if _sha256(backup) != target_hash:
            raise ReconciliationError("ROLLBACK_BACKUP_HASH_MISMATCH")
        os.chown(backup, uid, gid)
        os.chmod(backup, 0o600)
        return backup
    _atomic_install(backup, target.read_bytes(), uid=uid, gid=gid, mode=0o600)
    if _sha256(backup) != target_hash:
        raise ReconciliationError("ROLLBACK_BACKUP_VERIFICATION_FAILED")
    return backup


def _existing_backup(
    backup_root: Path,
    token: str,
    *,
    uid: int,
    gid: int,
) -> Path:
    root_metadata = _directory(backup_root, "BACKUP_ROOT")
    if (
        root_metadata.st_uid != uid
        or root_metadata.st_gid != gid
        or stat.S_IMODE(root_metadata.st_mode) != 0o700
    ):
        raise ReconciliationError("BACKUP_ROOT_METADATA_INVALID")
    backup = _backup_path(backup_root, token)
    metadata = _regular_file(backup, "ROLLBACK_BACKUP")
    if (
        metadata.st_uid != uid
        or metadata.st_gid != gid
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise ReconciliationError("ROLLBACK_BACKUP_METADATA_INVALID")
    if _sha256(backup) != token:
        raise ReconciliationError("ROLLBACK_BACKUP_HASH_MISMATCH")
    return backup


def _validate_installed(
    target: Path,
    expected_hash: str,
    *,
    uid: int,
    gid: int,
) -> os.stat_result:
    metadata = _regular_file(target, "INSTALLED_UNIT")
    if _sha256(target) != expected_hash:
        raise ReconciliationError("INSTALLED_HASH_VERIFICATION_FAILED")
    if metadata.st_uid != uid or metadata.st_gid != gid:
        raise ReconciliationError("INSTALLED_OWNERSHIP_VERIFICATION_FAILED")
    if stat.S_IMODE(metadata.st_mode) != 0o644:
        raise ReconciliationError("INSTALLED_MODE_VERIFICATION_FAILED")
    return metadata


def _require_inactive(observation: dict[str, Any]) -> None:
    if observation["active_state"] != "inactive" or observation["sub_state"] != "dead":
        raise ReconciliationError("SERVICE_NOT_INACTIVE")


def _daemon_reload(runner: Runner) -> None:
    returncode, _stdout = runner(["systemctl", "daemon-reload"])
    if returncode != 0:
        raise ReconciliationError("DAEMON_RELOAD_FAILED")


def apply_reconciliation(
    source: Path,
    target: Path,
    backup_root: Path,
    *,
    runner: Runner = _run,
    uid: int = 0,
    gid: int = 0,
    accepted_predecessor_sha256: str = ACCEPTED_PREDECESSOR_SHA256,
    expected_repository_sha256: str = EXPECTED_REPOSITORY_SHA256,
) -> dict[str, Any]:
    observation = observe(
        source,
        target,
        runner=runner,
        accepted_predecessor_sha256=accepted_predecessor_sha256,
        expected_repository_sha256=expected_repository_sha256,
    )
    if observation["status"] == "ALREADY_RECONCILED":
        _validate_installed(
            target, observation["repository_sha256"], uid=uid, gid=gid
        )
        return {
            **observation,
            "mutation_allowed": True,
            "status": "ALREADY_RECONCILED",
        }
    if observation["status"] not in {"CHANGE_REQUIRED", "DAEMON_RELOAD_REQUIRED"}:
        raise ReconciliationError(f"APPLY_BLOCKED_{observation['status']}")
    _require_inactive(observation)

    before_hash = observation["installed_sha256"]
    before_payload = target.read_bytes()
    _validate_installed(target, before_hash, uid=uid, gid=gid)
    unit_replaced = observation["status"] == "CHANGE_REQUIRED"
    if unit_replaced:
        backup = _backup(target, backup_root, before_hash, uid=uid, gid=gid)
        rollback_token = before_hash
        restore_payload = before_payload
        restore_hash = before_hash
    else:
        backup = _existing_backup(
            backup_root,
            accepted_predecessor_sha256,
            uid=uid,
            gid=gid,
        )
        rollback_token = accepted_predecessor_sha256
        restore_payload = backup.read_bytes()
        restore_hash = rollback_token
    try:
        if unit_replaced:
            _atomic_install(target, source.read_bytes(), uid=uid, gid=gid, mode=0o644)
        _daemon_reload(runner)
        verified = observe(
            source,
            target,
            runner=runner,
            accepted_predecessor_sha256=accepted_predecessor_sha256,
            expected_repository_sha256=expected_repository_sha256,
        )
        if verified["status"] != "ALREADY_RECONCILED":
            raise ReconciliationError("POST_RELOAD_VERIFICATION_FAILED")
        metadata = _validate_installed(
            target, observation["repository_sha256"], uid=uid, gid=gid
        )
    except Exception:
        try:
            _atomic_install(target, restore_payload, uid=uid, gid=gid, mode=0o644)
            _daemon_reload(runner)
            _validate_installed(target, restore_hash, uid=uid, gid=gid)
        except Exception as rollback_error:
            raise ReconciliationError("AUTOMATIC_ROLLBACK_FAILED") from rollback_error
        raise

    return {
        "reconciliation_version": VERSION,
        "scope": SCOPE,
        "service": SERVICE,
        "status": "RECONCILED",
        "mutation_allowed": True,
        "mutation_performed": True,
        "before_sha256": before_hash,
        "after_sha256": observation["repository_sha256"],
        "rollback_token": rollback_token,
        "rollback_backup": str(backup),
        "installed_metadata": _metadata(metadata),
        "declared_timeout_start_sec": EXPECTED_TIMEOUT,
        "effective_timeout_start_usec": verified["effective_timeout_start_usec"],
        "source_contents_projected": False,
        "installed_contents_projected": False,
        "systemd_unit_mutation_performed": unit_replaced,
        "daemon_reload_performed": True,
        "service_start_performed": False,
        "service_restart_performed": False,
        "timer_mutation_performed": False,
        "infrastructure_mutation_performed": False,
    }


def rollback_reconciliation(
    source: Path,
    target: Path,
    backup_root: Path,
    token: str,
    *,
    runner: Runner = _run,
    uid: int = 0,
    gid: int = 0,
) -> dict[str, Any]:
    if not SHA256.fullmatch(token):
        raise ReconciliationError("ROLLBACK_TOKEN_INVALID")
    _validate_repository_unit(source)
    _regular_file(target, "INSTALLED_UNIT")
    state = _systemd_state(runner)
    _require_inactive(state)
    if state["dropin_count"] or state["fragment_path"] != str(target):
        raise ReconciliationError("ROLLBACK_SYSTEMD_BOUNDARY_INVALID")

    backup = _existing_backup(backup_root, token, uid=uid, gid=gid)

    current_hash = _sha256(target)
    current_payload = target.read_bytes()
    _validate_installed(target, current_hash, uid=uid, gid=gid)
    if (
        current_hash == token
        and state["effective_timeout_start_usec"] == PREDECESSOR_EFFECTIVE_TIMEOUT
    ):
        metadata = _validate_installed(target, token, uid=uid, gid=gid)
        return {
            "reconciliation_version": VERSION,
            "scope": SCOPE,
            "service": SERVICE,
            "status": "ALREADY_ROLLED_BACK",
            "mutation_allowed": True,
            "mutation_performed": False,
            "installed_sha256": token,
            "installed_metadata": _metadata(metadata),
            "effective_timeout_start_usec": state["effective_timeout_start_usec"],
        }

    _backup(target, backup_root, current_hash, uid=uid, gid=gid)
    try:
        _atomic_install(target, backup.read_bytes(), uid=uid, gid=gid, mode=0o644)
        _daemon_reload(runner)
        metadata = _validate_installed(target, token, uid=uid, gid=gid)
        restored = _systemd_state(runner)
        if restored["effective_timeout_start_usec"] != PREDECESSOR_EFFECTIVE_TIMEOUT:
            raise ReconciliationError("ROLLBACK_EFFECTIVE_TIMEOUT_VERIFICATION_FAILED")
    except Exception:
        try:
            _atomic_install(target, current_payload, uid=uid, gid=gid, mode=0o644)
            _daemon_reload(runner)
            _validate_installed(target, current_hash, uid=uid, gid=gid)
        except Exception as restore_error:
            raise ReconciliationError("ROLLBACK_RECOVERY_FAILED") from restore_error
        raise

    return {
        "reconciliation_version": VERSION,
        "scope": SCOPE,
        "service": SERVICE,
        "status": "ROLLED_BACK",
        "mutation_allowed": True,
        "mutation_performed": True,
        "before_sha256": current_hash,
        "after_sha256": token,
        "installed_metadata": _metadata(metadata),
        "effective_timeout_start_usec": restored["effective_timeout_start_usec"],
        "source_contents_projected": False,
        "installed_contents_projected": False,
        "systemd_unit_mutation_performed": True,
        "daemon_reload_performed": True,
        "service_start_performed": False,
        "service_restart_performed": False,
        "timer_mutation_performed": False,
        "infrastructure_mutation_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan, apply, or roll back the bounded service start-timeout reconciliation."
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true")
    action.add_argument("--rollback", metavar="SHA256")
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    try:
        if arguments.apply or arguments.rollback:
            if os.geteuid() != 0:
                raise ReconciliationError("ROOT_REQUIRED_FOR_MUTATION")
        if arguments.apply:
            result = apply_reconciliation(REPOSITORY_UNIT, INSTALLED_UNIT, BACKUP_ROOT)
        elif arguments.rollback:
            result = rollback_reconciliation(
                REPOSITORY_UNIT,
                INSTALLED_UNIT,
                BACKUP_ROOT,
                arguments.rollback,
            )
        else:
            result = observe(REPOSITORY_UNIT, INSTALLED_UNIT)
    except (OSError, ReconciliationError) as error:
        result = {
            "reconciliation_version": VERSION,
            "scope": SCOPE,
            "service": SERVICE,
            "status": "FAILED",
            "mutation_allowed": bool(arguments.apply or arguments.rollback),
            "mutation_performed": False,
            "error_code": str(error) or "UNEXPECTED_OS_ERROR",
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
