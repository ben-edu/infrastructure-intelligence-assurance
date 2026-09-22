#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any


VERSION = "0.1"
MODULE = "__init__.py"
REPOSITORY_MODULE = (
    Path(__file__).resolve().parents[1] / "src" / "infra_assurance" / MODULE
)
INSTALLED_MODULE = Path("/opt/infra-assurance/src/infra_assurance") / MODULE
BACKUP_ROOT = Path("/var/lib/infra-assurance/runtime-reconciliation")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReconciliationError(RuntimeError):
    pass


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


def _metadata(metadata: os.stat_result) -> dict[str, Any]:
    return {
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        "kind": "file",
    }


def _directory(path: Path, label: str) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise ReconciliationError(f"{label}_UNAVAILABLE") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise ReconciliationError(f"{label}_NOT_DIRECTORY")
    return metadata


def observe(source: Path, target: Path) -> dict[str, Any]:
    source_metadata = _regular_file(source, "REPOSITORY_MODULE")
    target_metadata = _regular_file(target, "INSTALLED_MODULE")
    source_hash = _sha256(source)
    target_hash = _sha256(target)
    return {
        "reconciliation_version": VERSION,
        "scope": "INFRA_ASSURANCE_INSTALLED_RUNTIME_SINGLE_MODULE",
        "module": MODULE,
        "status": "ALREADY_RECONCILED" if source_hash == target_hash else "CHANGE_REQUIRED",
        "mutation_allowed": False,
        "mutation_performed": False,
        "repository_sha256": source_hash,
        "installed_sha256": target_hash,
        "repository_metadata": _metadata(source_metadata),
        "installed_metadata": _metadata(target_metadata),
        "source_contents_projected": False,
        "installed_contents_projected": False,
        "systemd_mutation_performed": False,
        "service_start_performed": False,
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


def _backup(
    target: Path,
    backup_root: Path,
    target_hash: str,
    *,
    uid: int,
    gid: int,
) -> Path:
    _ensure_backup_root(backup_root, uid=uid, gid=gid)
    backup = backup_root / f"{MODULE}.{target_hash}.bak"
    if backup.exists() or backup.is_symlink():
        _regular_file(backup, "ROLLBACK_BACKUP")
        if _sha256(backup) != target_hash:
            raise ReconciliationError("ROLLBACK_BACKUP_HASH_MISMATCH")
        os.chown(backup, uid, gid)
        os.chmod(backup, 0o600)
        return backup
    _atomic_install(
        backup,
        target.read_bytes(),
        uid=uid,
        gid=gid,
        mode=0o600,
    )
    if _sha256(backup) != target_hash:
        raise ReconciliationError("ROLLBACK_BACKUP_VERIFICATION_FAILED")
    return backup


def _validate_installed(
    target: Path,
    expected_hash: str,
    *,
    uid: int,
    gid: int,
) -> os.stat_result:
    metadata = _regular_file(target, "INSTALLED_MODULE")
    if _sha256(target) != expected_hash:
        raise ReconciliationError("INSTALLED_HASH_VERIFICATION_FAILED")
    if metadata.st_uid != uid or metadata.st_gid != gid:
        raise ReconciliationError("INSTALLED_OWNERSHIP_VERIFICATION_FAILED")
    if stat.S_IMODE(metadata.st_mode) != 0o644:
        raise ReconciliationError("INSTALLED_MODE_VERIFICATION_FAILED")
    return metadata


def apply_reconciliation(
    source: Path,
    target: Path,
    backup_root: Path,
    *,
    uid: int = 0,
    gid: int = 0,
) -> dict[str, Any]:
    observation = observe(source, target)
    if observation["status"] == "ALREADY_RECONCILED":
        return {
            **observation,
            "mutation_allowed": True,
            "status": "ALREADY_RECONCILED",
        }

    source_payload = source.read_bytes()
    try:
        compile(source_payload, str(source), "exec")
    except (SyntaxError, ValueError) as error:
        raise ReconciliationError("REPOSITORY_MODULE_COMPILE_FAILED") from error

    before_hash = observation["installed_sha256"]
    backup = _backup(target, backup_root, before_hash, uid=uid, gid=gid)
    before_payload = target.read_bytes()
    try:
        _atomic_install(target, source_payload, uid=uid, gid=gid, mode=0o644)
        metadata = _validate_installed(
            target, observation["repository_sha256"], uid=uid, gid=gid
        )
    except Exception:
        try:
            if _sha256(target) != before_hash:
                _atomic_install(
                    target, before_payload, uid=uid, gid=gid, mode=0o644
                )
                _validate_installed(target, before_hash, uid=uid, gid=gid)
        except Exception as rollback_error:
            raise ReconciliationError("AUTOMATIC_ROLLBACK_FAILED") from rollback_error
        raise

    return {
        "reconciliation_version": VERSION,
        "scope": "INFRA_ASSURANCE_INSTALLED_RUNTIME_SINGLE_MODULE",
        "module": MODULE,
        "status": "RECONCILED",
        "mutation_allowed": True,
        "mutation_performed": True,
        "before_sha256": before_hash,
        "after_sha256": observation["repository_sha256"],
        "rollback_token": before_hash,
        "rollback_backup": str(backup),
        "installed_metadata": _metadata(metadata),
        "source_contents_projected": False,
        "installed_contents_projected": False,
        "systemd_mutation_performed": False,
        "service_start_performed": False,
        "infrastructure_mutation_performed": False,
    }


def rollback_reconciliation(
    target: Path,
    backup_root: Path,
    token: str,
    *,
    uid: int = 0,
    gid: int = 0,
) -> dict[str, Any]:
    if not SHA256.fullmatch(token):
        raise ReconciliationError("ROLLBACK_TOKEN_INVALID")
    _regular_file(target, "INSTALLED_MODULE")
    backup_root_metadata = _directory(backup_root, "BACKUP_ROOT")
    if (
        backup_root_metadata.st_uid != uid
        or backup_root_metadata.st_gid != gid
        or stat.S_IMODE(backup_root_metadata.st_mode) != 0o700
    ):
        raise ReconciliationError("BACKUP_ROOT_METADATA_INVALID")
    backup = backup_root / f"{MODULE}.{token}.bak"
    _regular_file(backup, "ROLLBACK_BACKUP")
    if _sha256(backup) != token:
        raise ReconciliationError("ROLLBACK_BACKUP_HASH_MISMATCH")
    try:
        compile(backup.read_bytes(), str(backup), "exec")
    except (SyntaxError, ValueError) as error:
        raise ReconciliationError("ROLLBACK_BACKUP_COMPILE_FAILED") from error

    current_hash = _sha256(target)
    if current_hash == token:
        metadata = _validate_installed(target, token, uid=uid, gid=gid)
        return {
            "reconciliation_version": VERSION,
            "scope": "INFRA_ASSURANCE_INSTALLED_RUNTIME_SINGLE_MODULE",
            "module": MODULE,
            "status": "ALREADY_ROLLED_BACK",
            "mutation_allowed": True,
            "mutation_performed": False,
            "installed_sha256": token,
            "installed_metadata": _metadata(metadata),
        }

    _backup(target, backup_root, current_hash, uid=uid, gid=gid)
    current_payload = target.read_bytes()
    try:
        _atomic_install(target, backup.read_bytes(), uid=uid, gid=gid, mode=0o644)
        metadata = _validate_installed(target, token, uid=uid, gid=gid)
    except Exception:
        try:
            if _sha256(target) != current_hash:
                _atomic_install(
                    target, current_payload, uid=uid, gid=gid, mode=0o644
                )
                _validate_installed(target, current_hash, uid=uid, gid=gid)
        except Exception as restore_error:
            raise ReconciliationError("ROLLBACK_RECOVERY_FAILED") from restore_error
        raise
    return {
        "reconciliation_version": VERSION,
        "scope": "INFRA_ASSURANCE_INSTALLED_RUNTIME_SINGLE_MODULE",
        "module": MODULE,
        "status": "ROLLED_BACK",
        "mutation_allowed": True,
        "mutation_performed": True,
        "before_sha256": current_hash,
        "after_sha256": token,
        "installed_metadata": _metadata(metadata),
        "source_contents_projected": False,
        "installed_contents_projected": False,
        "systemd_mutation_performed": False,
        "service_start_performed": False,
        "infrastructure_mutation_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan, apply, or roll back the bounded installed __init__.py reconciliation."
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
            result = apply_reconciliation(
                REPOSITORY_MODULE, INSTALLED_MODULE, BACKUP_ROOT
            )
        elif arguments.rollback:
            result = rollback_reconciliation(
                INSTALLED_MODULE, BACKUP_ROOT, arguments.rollback
            )
        else:
            result = observe(REPOSITORY_MODULE, INSTALLED_MODULE)
    except (OSError, ReconciliationError) as error:
        result = {
            "reconciliation_version": VERSION,
            "scope": "INFRA_ASSURANCE_INSTALLED_RUNTIME_SINGLE_MODULE",
            "module": MODULE,
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
