from __future__ import annotations

import argparse
import grp
import hashlib
import json
import os
import pwd
import re
import shlex
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


VERSION = "0.1"
SERVICE = "infra-assurance-kubernetes.service"
TIMER = "infra-assurance-kubernetes.timer"
RUNTIME_USER = "infra-assurance"
RUNTIME_GROUP = "infra-assurance"
CLASSES = (
    "DECLARED",
    "OBSERVED",
    "UNKNOWN",
    "FAILED_TO_OBSERVE",
    "INFERENCE",
    "REQUIRES_CHANGE",
)
WRITABLE_PATHS = (
    "/var/lib/infra-assurance/evidence",
    "/var/lib/infra-assurance/history",
    "/var/lib/infra-assurance/git",
    "/var/lib/infra-assurance/declared",
)
SERVICE_PROPERTIES = (
    "LoadState",
    "ActiveState",
    "SubState",
    "UnitFileState",
    "Type",
    "User",
    "Group",
    "DynamicUser",
    "NoNewPrivileges",
    "PrivateTmp",
    "ProtectSystem",
    "ProtectHome",
    "ReadWritePaths",
    "ReadOnlyPaths",
    "FragmentPath",
    "DropInPaths",
    "TimeoutStartUSec",
    "RuntimeMaxUSec",
    "Restart",
    "Result",
    "ExecMainCode",
    "ExecMainStatus",
    "NRestarts",
    "FailureAction",
    "OnFailure",
    "StandardOutput",
    "StandardError",
    "ExecMainStartTimestampMonotonic",
    "ExecMainExitTimestampMonotonic",
)
TIMER_PROPERTIES = (
    "LoadState",
    "ActiveState",
    "SubState",
    "UnitFileState",
    "Unit",
    "Persistent",
    "AccuracyUSec",
    "RandomizedDelayUSec",
    "LastTriggerUSec",
    "NextElapseUSecMonotonic",
    "TimersMonotonic",
    "FragmentPath",
    "DropInPaths",
)
FRAGMENT_ROOTS = (
    Path("/etc/systemd/system"),
    Path("/run/systemd/system"),
    Path("/usr/lib/systemd/system"),
    Path("/lib/systemd/system"),
)
SCHEDULER_DIRS = (
    *FRAGMENT_ROOTS,
    Path("/etc/cron.d"),
    Path("/etc/cron.daily"),
    Path("/etc/cron.weekly"),
    Path("/etc/cron.monthly"),
)
SAFE_NAME = re.compile(r"^[A-Za-z0-9_.:@+\-]{1,200}$")
BACKUP_NAME = re.compile(
    r"(?:infra[-_.]?assurance.*backup|backup.*infra[-_.]?assurance)", re.I
)
Runner = Callable[[list[str]], tuple[int, str]]


def _finding(finding_id: str, source: str, **evidence: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"id": finding_id, "source": source}
    if evidence:
        result["evidence"] = evidence
    return result


def _add(
    findings: dict[str, list[dict[str, Any]]],
    classification: str,
    finding_id: str,
    source: str,
    **evidence: Any,
) -> None:
    findings[classification].append(_finding(finding_id, source, **evidence))


def parse_unit(text: str) -> dict[str, dict[str, list[str]]]:
    """Retain repeated directives; do not open referenced files or command targets."""
    result: dict[str, dict[str, list[str]]] = {}
    section = ""
    pending = ""
    for raw in text.splitlines():
        line = pending + raw.strip()
        pending = ""
        if line.endswith("\\"):
            pending = line[:-1]
            continue
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            result.setdefault(section, {})
        elif section and "=" in line:
            key, value = line.split("=", 1)
            result[section].setdefault(key.strip(), []).append(value.strip())
    return result


def _values(unit: dict[str, dict[str, list[str]]], section: str, key: str) -> list[str]:
    return unit.get(section, {}).get(key, [])


def _last(
    unit: dict[str, dict[str, list[str]]], section: str, key: str, default: str = ""
) -> str:
    values = _values(unit, section, key)
    return values[-1] if values else default


def _words(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        try:
            result.extend(shlex.split(value))
        except ValueError:
            pass
    return sorted(set(result))


def _bool(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered in {"1", "yes", "true", "on"}:
        return True
    if lowered in {"0", "no", "false", "off"}:
        return False
    return None


def _module_entrypoints(service: dict[str, dict[str, list[str]]]) -> list[str]:
    result: list[str] = []
    for key in ("ExecStartPre", "ExecStart", "ExecStartPost"):
        for command in _values(service, "Service", key):
            result.extend(
                re.findall(r"(?:^|\s)-m\s+(infra_assurance\.[A-Za-z0-9_]+)", command)
            )
    return result


def _pythonpath(service: dict[str, dict[str, list[str]]]) -> str:
    for declaration in _values(service, "Service", "Environment"):
        for field in _words([declaration]):
            if field.startswith("PYTHONPATH="):
                return field.split("=", 1)[1]
    return "NOT_DECLARED"


def declared_state(repo: Path) -> dict[str, Any]:
    service_path = repo / "systemd" / SERVICE
    timer_path = repo / "systemd" / TIMER
    service = parse_unit(service_path.read_text(encoding="utf-8"))
    timer = parse_unit(timer_path.read_text(encoding="utf-8"))
    modules = _module_entrypoints(service)
    helper = (repo / "src/infra_assurance/io_utils.py").read_text(encoding="utf-8")
    history = (repo / "src/infra_assurance/history.py").read_text(encoding="utf-8")
    module_atomic_count = 0
    for module in modules:
        source = repo / "src" / Path(*module.split(".")).with_suffix(".py")
        if "atomic_write" in source.read_text(encoding="utf-8"):
            module_atomic_count += 1
    commands = [
        command
        for key in ("ExecStartPre", "ExecStart", "ExecStartPost")
        for command in _values(service, "Service", key)
    ]
    return {
        "identity": {
            "user": _last(service, "Service", "User") or "MANAGER_DEFAULT",
            "group": _last(service, "Service", "Group") or "MANAGER_DEFAULT",
        },
        "sandbox": {
            "no_new_privileges": _bool(_last(service, "Service", "NoNewPrivileges")),
            "private_tmp": _bool(_last(service, "Service", "PrivateTmp")),
            "protect_system": _last(service, "Service", "ProtectSystem") or "MANAGER_DEFAULT",
            "protect_home": _last(service, "Service", "ProtectHome") or "MANAGER_DEFAULT",
            "read_write_paths": _words(_values(service, "Service", "ReadWritePaths")),
            "read_only_paths": _words(_values(service, "Service", "ReadOnlyPaths")),
        },
        "schedule": {
            "on_boot_sec": _last(timer, "Timer", "OnBootSec") or "NOT_DECLARED",
            "on_unit_active_sec": _last(timer, "Timer", "OnUnitActiveSec")
            or "NOT_DECLARED",
            "persistent": _bool(_last(timer, "Timer", "Persistent")),
            "accuracy_sec": _last(timer, "Timer", "AccuracySec") or "MANAGER_DEFAULT",
            "target_unit": _last(timer, "Timer", "Unit") or "MANAGER_DEFAULT",
        },
        "failure": {
            "timeout_start_sec": _last(service, "Service", "TimeoutStartSec")
            or "MANAGER_DEFAULT",
            "runtime_max_sec": _last(service, "Service", "RuntimeMaxSec")
            or "MANAGER_DEFAULT",
            "restart": _last(service, "Service", "Restart") or "MANAGER_DEFAULT",
            "on_failure_declared": bool(_values(service, "Unit", "OnFailure")),
            "failure_action": _last(service, "Service", "FailureAction")
            or "MANAGER_DEFAULT",
        },
        "runtime": {
            "type": _last(service, "Service", "Type") or "MANAGER_DEFAULT",
            "pythonpath": _pythonpath(service),
            "command_steps": len(commands),
            "module_entrypoints": modules,
            "explicit_process_lock": any(
                re.search(r"(?:^|[\s/])flock(?:\s|$)", command) for command in commands
            ),
        },
        "atomic": {
            "same_directory_temporary": "dir=path.parent" in helper,
            "file_fsync": "os.fsync(stream.fileno())" in helper,
            "atomic_replace": "os.replace(temporary, path)" in helper,
            "directory_fsync": "os.fsync(directory_fd)" in helper,
            "entrypoints_total": len(modules),
            "entrypoints_using_atomic_helper": module_atomic_count,
            "history_index_atomic_replace": "atomic_write_json(self.index_path" in history,
            "explicit_history_lock": any(
                token in history for token in ("fcntl.flock", "FileLock(", "lockf(")
            ),
        },
        "_service_path": service_path,
        "_timer_path": timer_path,
    }


def _run(command: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return -1, ""
    return result.returncode, result.stdout


def _show(unit: str, properties: tuple[str, ...], runner: Runner) -> dict[str, str] | None:
    command = ["systemctl", "show", unit, "--no-pager"]
    command.extend(f"--property={name}" for name in properties)
    returncode, stdout = runner(command)
    if returncode != 0:
        return None
    allowed = set(properties)
    values = {
        key: value.strip()
        for line in stdout.splitlines()
        if "=" in line
        for key, value in [line.split("=", 1)]
        if key in allowed
    }
    return values if values.get("LoadState") == "loaded" else None


def _count_words(value: str) -> int:
    return len(_words([value])) if value else 0


def _timer_triggers(value: str) -> dict[str, str]:
    allowed = {
        "OnActiveUSec",
        "OnBootUSec",
        "OnStartupUSec",
        "OnUnitActiveUSec",
        "OnUnitInactiveUSec",
    }
    return {
        key: timer_value.strip()
        for key, timer_value in re.findall(r"\b(On[A-Za-z]+USec)=([^;}]*)", value)
        if key in allowed
    }


def _duration(properties: dict[str, str]) -> float | None:
    try:
        start = int(properties.get("ExecMainStartTimestampMonotonic", "0"))
        end = int(properties.get("ExecMainExitTimestampMonotonic", "0"))
    except ValueError:
        return None
    return round((end - start) / 1_000_000, 3) if start > 0 and end >= start else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fragment_match(
    repository_path: Path,
    installed_value: str,
    expected_name: str,
    roots: tuple[Path, ...],
) -> bool | None:
    candidate = Path(installed_value)
    if candidate.name != expected_name:
        return None
    try:
        resolved = candidate.resolve(strict=True)
        if not any(resolved.is_relative_to(root.resolve()) for root in roots):
            return None
        return _sha256(repository_path) == _sha256(resolved)
    except OSError:
        return None


def observed_systemd(
    declared: dict[str, Any], runner: Runner, roots: tuple[Path, ...]
) -> tuple[dict[str, Any], list[str]]:
    service_raw = _show(SERVICE, SERVICE_PROPERTIES, runner)
    timer_raw = _show(TIMER, TIMER_PROPERTIES, runner)
    failures: list[str] = []
    service: dict[str, Any] = {}
    timer: dict[str, Any] = {}
    if service_raw is None:
        failures.append("INSTALLED_SERVICE_STATE")
    else:
        service = {
            "active_state": service_raw.get("ActiveState", "UNKNOWN"),
            "sub_state": service_raw.get("SubState", "UNKNOWN"),
            "unit_file_state": service_raw.get("UnitFileState", "UNKNOWN"),
            "type": service_raw.get("Type", "UNKNOWN"),
            "user": service_raw.get("User") or "MANAGER_DEFAULT",
            "group": service_raw.get("Group") or "MANAGER_DEFAULT",
            "dynamic_user": _bool(service_raw.get("DynamicUser", "")),
            "no_new_privileges": _bool(service_raw.get("NoNewPrivileges", "")),
            "private_tmp": _bool(service_raw.get("PrivateTmp", "")),
            "protect_system": service_raw.get("ProtectSystem") or "UNKNOWN",
            "protect_home": service_raw.get("ProtectHome") or "UNKNOWN",
            "read_write_paths": _words([service_raw.get("ReadWritePaths", "")]),
            "read_only_paths": _words([service_raw.get("ReadOnlyPaths", "")]),
            "dropin_count": _count_words(service_raw.get("DropInPaths", "")),
            "timeout_start_usec": service_raw.get("TimeoutStartUSec") or "UNKNOWN",
            "runtime_max_usec": service_raw.get("RuntimeMaxUSec") or "UNKNOWN",
            "restart": service_raw.get("Restart") or "UNKNOWN",
            "on_failure_count": _count_words(service_raw.get("OnFailure", "")),
            "failure_action": service_raw.get("FailureAction") or "UNKNOWN",
            "standard_output": service_raw.get("StandardOutput") or "UNKNOWN",
            "standard_error": service_raw.get("StandardError") or "UNKNOWN",
            "last_result": service_raw.get("Result") or "UNKNOWN",
            "last_exec_code": service_raw.get("ExecMainCode") or "UNKNOWN",
            "last_exec_status": service_raw.get("ExecMainStatus") or "UNKNOWN",
            "restart_count": service_raw.get("NRestarts") or "UNKNOWN",
            "last_duration_seconds": _duration(service_raw),
            "fragment_matches_repository": _fragment_match(
                declared["_service_path"],
                service_raw.get("FragmentPath", ""),
                SERVICE,
                roots,
            ),
        }
        if service["fragment_matches_repository"] is None:
            failures.append("INSTALLED_SERVICE_FRAGMENT_MATCH")
    if timer_raw is None:
        failures.append("INSTALLED_TIMER_STATE")
    else:
        timer = {
            "active_state": timer_raw.get("ActiveState", "UNKNOWN"),
            "sub_state": timer_raw.get("SubState", "UNKNOWN"),
            "unit_file_state": timer_raw.get("UnitFileState", "UNKNOWN"),
            "target_unit": timer_raw.get("Unit") or "UNKNOWN",
            "persistent": _bool(timer_raw.get("Persistent", "")),
            "accuracy_usec": timer_raw.get("AccuracyUSec") or "UNKNOWN",
            "randomized_delay_usec": timer_raw.get("RandomizedDelayUSec") or "UNKNOWN",
            "last_trigger_recorded": bool(timer_raw.get("LastTriggerUSec")),
            "next_elapse_recorded": bool(timer_raw.get("NextElapseUSecMonotonic")),
            "monotonic_triggers": _timer_triggers(timer_raw.get("TimersMonotonic", "")),
            "dropin_count": _count_words(timer_raw.get("DropInPaths", "")),
            "fragment_matches_repository": _fragment_match(
                declared["_timer_path"],
                timer_raw.get("FragmentPath", ""),
                TIMER,
                roots,
            ),
        }
        if timer["fragment_matches_repository"] is None:
            failures.append("INSTALLED_TIMER_FRAGMENT_MATCH")
    return {"service": service, "timer": timer}, failures


def _account(user: str) -> dict[str, Any] | None:
    try:
        entry = pwd.getpwnam(user)
    except KeyError:
        return None
    gids = {entry.pw_gid}
    gids.update(group.gr_gid for group in grp.getgrall() if user in group.gr_mem)
    return {"uid": entry.pw_uid, "gid": entry.pw_gid, "gids": gids}


def _name(uid_or_gid: int, *, group: bool) -> str:
    try:
        return (
            grp.getgrgid(uid_or_gid).gr_name
            if group
            else pwd.getpwuid(uid_or_gid).pw_name
        )
    except KeyError:
        return f"{'gid' if group else 'uid'}:{uid_or_gid}"


def _runtime_writable(metadata: os.stat_result, account: dict[str, Any] | None) -> bool | None:
    if account is None:
        return None
    if account["uid"] == 0:
        return True
    mode = stat.S_IMODE(metadata.st_mode)
    if metadata.st_uid == account["uid"]:
        return bool(mode & stat.S_IWUSR)
    if metadata.st_gid in account["gids"]:
        return bool(mode & stat.S_IWGRP)
    return bool(mode & stat.S_IWOTH)


def metadata_summary(
    root: Path,
    account: dict[str, Any] | None,
    expected_uid: int | None,
    expected_gid: int | None,
    *,
    max_depth: int = 3,
    limit: int = 4096,
) -> dict[str, Any]:
    """Inspect owner/group/mode/type only; never open or project artifact names."""
    if not root.exists():
        return {"status": "FAILED_TO_OBSERVE"}
    stack = [(root, 0)]
    histogram: dict[tuple[int, int, int, str], int] = {}
    inspected = failures = symlinks = world_writable = 0
    owner_mismatch = group_mismatch = runtime_writable = writability_unknown = 0
    truncated = False
    while stack:
        path, depth = stack.pop()
        if inspected >= limit:
            truncated = True
            break
        try:
            metadata = path.lstat()
        except OSError:
            failures += 1
            continue
        inspected += 1
        kind = (
            "symlink"
            if stat.S_ISLNK(metadata.st_mode)
            else "directory"
            if stat.S_ISDIR(metadata.st_mode)
            else "file"
            if stat.S_ISREG(metadata.st_mode)
            else "other"
        )
        symlinks += kind == "symlink"
        mode = stat.S_IMODE(metadata.st_mode)
        world_writable += bool(mode & stat.S_IWOTH)
        owner_mismatch += expected_uid is not None and metadata.st_uid != expected_uid
        group_mismatch += expected_gid is not None and metadata.st_gid != expected_gid
        writable = _runtime_writable(metadata, account)
        runtime_writable += writable is True
        writability_unknown += writable is None
        key = (metadata.st_uid, metadata.st_gid, mode, kind)
        histogram[key] = histogram.get(key, 0) + 1
        if kind == "directory" and depth < max_depth:
            try:
                stack.extend((Path(item.path), depth + 1) for item in os.scandir(path))
            except OSError:
                failures += 1
    groups = [
        {
            "owner": _name(uid, group=False),
            "group": _name(gid, group=True),
            "mode": f"{mode:04o}",
            "kind": kind,
            "count": count,
        }
        for (uid, gid, mode, kind), count in sorted(
            histogram.items(), key=lambda item: (-item[1], item[0])
        )[:16]
    ]
    return {
        "status": "OBSERVED",
        "coverage": "PARTIAL" if failures or truncated else "COMPLETE",
        "entries_inspected": inspected,
        "metadata_failures": failures,
        "truncated": truncated,
        "symlink_count": symlinks,
        "world_writable_count": world_writable,
        "owner_mismatch_count": owner_mismatch,
        "group_mismatch_count": group_mismatch,
        "runtime_writable_by_posix_mode_count": runtime_writable,
        "runtime_writability_unknown_count": writability_unknown,
        "ownership_mode_groups": groups,
        "artifact_contents_inspected": False,
        "artifact_names_projected": False,
    }


def installed_code_match(repo: Path, installed: Path, entrypoints: list[str]) -> dict[str, Any]:
    repository = repo / "src/infra_assurance"
    if not repository.is_dir() or not installed.is_dir():
        return {"status": "FAILED_TO_OBSERVE"}
    repo_files = {path.name: path for path in repository.glob("*.py")}
    installed_files = {path.name: path for path in installed.glob("*.py")}
    mismatched: list[str] = []
    unexpected: list[str] = []
    unreadable: list[str] = []
    matching = 0
    for name, path in sorted(installed_files.items()):
        if name not in repo_files:
            unexpected.append(name)
            continue
        try:
            same = _sha256(repo_files[name]) == _sha256(path)
        except OSError:
            unreadable.append(name)
            continue
        matching += same
        if not same:
            mismatched.append(name)
    required = {f"{module.rsplit('.', 1)[-1]}.py" for module in entrypoints}
    missing_entrypoints = sorted(required - installed_files.keys())
    return {
        "status": "FAILED_TO_OBSERVE" if unreadable else "OBSERVED",
        "installed_modules": len(installed_files),
        "matching_modules": matching,
        "mismatched_modules": mismatched,
        "unexpected_modules": unexpected,
        "missing_entrypoint_modules": missing_entrypoints,
        "unreadable_modules": unreadable,
        "installed_runtime_matches_repository": not (
            mismatched or unexpected or missing_entrypoints or unreadable
        ),
        "repository_only_modules_are_not_runtime_drift": True,
        "source_contents_projected": False,
    }


def backup_scheduler_names(directories: tuple[Path, ...]) -> dict[str, Any]:
    names: list[str] = []
    observed = failures = 0
    for directory in directories:
        if not directory.exists():
            continue
        observed += 1
        try:
            entries = list(directory.iterdir())
        except OSError:
            failures += 1
            continue
        names.extend(
            entry.name
            for entry in entries
            if SAFE_NAME.fullmatch(entry.name) and BACKUP_NAME.search(entry.name)
        )
    return {
        "status": "OBSERVED" if observed and not failures else "FAILED_TO_OBSERVE",
        "directories_observed": observed,
        "metadata_failures": failures,
        "matching_names": sorted(set(names)),
        "matching_name_count": len(set(names)),
        "file_contents_inspected": False,
    }


def _sandbox_drift(declared: dict[str, Any], live: dict[str, Any]) -> bool:
    expected = declared["sandbox"]
    if not live:
        return False
    same = (
        live.get("no_new_privileges") == expected["no_new_privileges"]
        and live.get("private_tmp") == expected["private_tmp"]
        and live.get("protect_system") == expected["protect_system"]
        and _bool(str(live.get("protect_home", "")))
        == _bool(str(expected["protect_home"]))
    )
    live_paths = set(live.get("read_write_paths", []))
    return not same or (bool(live_paths) and live_paths != set(expected["read_write_paths"]))


def smallest_change(
    declared: dict[str, Any], live: dict[str, Any], storage: dict[str, Any], code: dict[str, Any]
) -> dict[str, Any]:
    service = live.get("service", {})
    timer = live.get("timer", {})
    if service and (
        service.get("user") != declared["identity"]["user"]
        or service.get("group") != declared["identity"]["group"]
    ):
        change = "ALIGN_EFFECTIVE_RUNTIME_IDENTITY"
    elif _sandbox_drift(declared, service):
        change = "ALIGN_EFFECTIVE_SYSTEMD_SANDBOX"
    elif service.get("fragment_matches_repository") is False:
        change = "RECONCILE_INSTALLED_SERVICE_FRAGMENT"
    elif timer.get("fragment_matches_repository") is False:
        change = "RECONCILE_INSTALLED_TIMER_FRAGMENT"
    elif any(
        summary.get("status") == "OBSERVED"
        and (
            summary.get("world_writable_count", 0)
            or summary.get("owner_mismatch_count", 0)
            or summary.get("group_mismatch_count", 0)
        )
        for summary in storage.get("state", {}).values()
    ):
        change = "ALIGN_STATE_ARTIFACT_OWNERSHIP_AND_MODES"
    elif storage.get("code", {}).get("runtime_writable_by_posix_mode_count", 0):
        change = "REMOVE_RUNTIME_WRITE_ACCESS_FROM_INSTALLED_CODE"
    elif code.get("status") == "OBSERVED" and not code.get(
        "installed_runtime_matches_repository", False
    ):
        change = "RECONCILE_INSTALLED_RUNTIME_MODULES"
    else:
        change = "PIN_EXPLICIT_SERVICE_START_TIMEOUT"
    return _finding(
        change,
        "declared+observed",
        implementation_status="NOT_IMPLEMENTED",
        declared_timeout=declared["failure"]["timeout_start_sec"],
        observed_effective_timeout_usec=service.get("timeout_start_usec", "UNKNOWN"),
    )


def collect(
    repo: Path,
    *,
    runner: Runner = _run,
    state_root: Path = Path("/var/lib/infra-assurance"),
    installed: Path = Path("/opt/infra-assurance/src/infra_assurance"),
    fragment_roots: tuple[Path, ...] = FRAGMENT_ROOTS,
    scheduler_dirs: tuple[Path, ...] = SCHEDULER_DIRS,
) -> dict[str, Any]:
    findings = {classification: [] for classification in CLASSES}
    try:
        declared = declared_state(repo)
    except OSError:
        declared = {}
        _add(findings, "FAILED_TO_OBSERVE", "REPOSITORY_RUNTIME_DECLARATIONS", "repository")
    if declared:
        for finding_id, key in (
            ("RUNTIME_IDENTITY", "identity"),
            ("SYSTEMD_SANDBOX", "sandbox"),
            ("TIMER_SCHEDULE", "schedule"),
            ("FAILURE_SEMANTICS", "failure"),
            ("RUNTIME_AND_OVERLAP_BOUNDARY", "runtime"),
            ("ATOMIC_WRITE_DECLARATION", "atomic"),
        ):
            _add(findings, "DECLARED", finding_id, "repository", **declared[key])
        live, systemd_failures = observed_systemd(declared, runner, fragment_roots)
        if live["service"]:
            _add(findings, "OBSERVED", "INSTALLED_SERVICE_STATE", "systemd:show", **live["service"])
        if live["timer"]:
            _add(findings, "OBSERVED", "INSTALLED_TIMER_STATE", "systemd:show", **live["timer"])
        for finding_id in systemd_failures:
            _add(findings, "FAILED_TO_OBSERVE", finding_id, "systemd:show-or-fragment-hash")
    else:
        live = {"service": {}, "timer": {}}

    account = _account(declared.get("identity", {}).get("user", RUNTIME_USER))
    if account is None:
        _add(findings, "FAILED_TO_OBSERVE", "RUNTIME_ACCOUNT_METADATA", "account-database")
        expected_uid = expected_gid = None
    else:
        expected_uid, expected_gid = account["uid"], account["gid"]
        _add(
            findings,
            "OBSERVED",
            "RUNTIME_ACCOUNT_METADATA",
            "account-database",
            user=declared.get("identity", {}).get("user", RUNTIME_USER),
            group=_name(expected_gid, group=True),
        )

    state: dict[str, Any] = {}
    for name in ("evidence", "history", "git", "declared"):
        summary = metadata_summary(
            state_root / name, account, expected_uid, expected_gid
        )
        state[name] = summary
        if summary["status"] != "OBSERVED":
            _add(findings, "FAILED_TO_OBSERVE", f"{name.upper()}_METADATA", "filesystem")
    observed_state = {name: value for name, value in state.items() if value["status"] == "OBSERVED"}
    if observed_state:
        _add(
            findings,
            "OBSERVED",
            "WRITABLE_STATE_AND_ARTIFACT_OWNERSHIP",
            "filesystem:metadata-only",
            **observed_state,
        )
    code_metadata = metadata_summary(installed, account, 0, 0, max_depth=2)
    if code_metadata["status"] == "OBSERVED":
        _add(
            findings,
            "OBSERVED",
            "INSTALLED_CODE_METADATA",
            "filesystem:metadata-only",
            **code_metadata,
        )
    else:
        _add(findings, "FAILED_TO_OBSERVE", "INSTALLED_CODE_METADATA", "filesystem")
    storage = {"state": state, "code": code_metadata}
    partial = [
        name
        for name, value in {**state, "code": code_metadata}.items()
        if value.get("coverage") == "PARTIAL"
    ]
    if partial:
        _add(findings, "UNKNOWN", "METADATA_BEYOND_BOUNDED_SCAN", "filesystem", sources=partial)

    code = installed_code_match(
        repo,
        installed,
        declared.get("runtime", {}).get("module_entrypoints", []),
    )
    if code["status"] == "OBSERVED":
        _add(
            findings,
            "OBSERVED",
            "INSTALLED_CODE_REPOSITORY_MATCH",
            "source-hash-comparison",
            **code,
        )
    else:
        _add(findings, "FAILED_TO_OBSERVE", "INSTALLED_CODE_REPOSITORY_MATCH", "source-hash-comparison")

    backup = backup_scheduler_names(scheduler_dirs)
    if backup["status"] == "OBSERVED":
        _add(
            findings,
            "OBSERVED",
            "BOUNDED_PLATFORM_BACKUP_SCHEDULER_NAMES",
            "scheduler-filenames-only",
            **backup,
        )
    else:
        _add(
            findings,
            "FAILED_TO_OBSERVE",
            "BOUNDED_PLATFORM_BACKUP_SCHEDULER_NAMES",
            "scheduler-filenames-only",
        )

    _add(
        findings,
        "UNKNOWN",
        "PLATFORM_EVIDENCE_HISTORY_BACKUP_STATUS",
        "bounded-scheduler-metadata",
        matching_name_count=backup.get("matching_name_count", 0),
        none_observed_is_not_unprotected=True,
    )
    for finding_id, source in (
        ("EXTERNAL_FAILURE_VISIBILITY", "repository+systemd-properties"),
        ("HISTORICAL_OVERLAP_AND_MISSED_ACTIVATIONS", "current-unit-metadata-only"),
        ("ACL_CAPABILITY_AND_MAC_WRITABILITY", "posix-owner-group-mode-only"),
    ):
        _add(findings, "UNKNOWN", finding_id, source)
    if declared.get("runtime", {}).get("type") == "oneshot" and declared.get(
        "schedule", {}
    ).get("target_unit") == SERVICE:
        _add(findings, "INFERENCE", "SAME_UNIT_ACTIVATION_SERIALIZATION", "oneshot+timer-target")
    if declared and not declared["runtime"]["explicit_process_lock"]:
        _add(findings, "INFERENCE", "OUT_OF_UNIT_CONCURRENCY_NOT_GUARDED", "unit+history-source")
    if declared and all(
        declared["atomic"].get(key)
        for key in (
            "same_directory_temporary",
            "file_fsync",
            "atomic_replace",
            "directory_fsync",
        )
    ):
        _add(findings, "INFERENCE", "ATOMIC_FILES_NOT_ATOMIC_ARTIFACT_SET", "sequential-chain")
    if declared:
        findings["REQUIRES_CHANGE"].append(
            smallest_change(declared, live, storage, code)
        )

    status = "INCOMPLETE" if findings["FAILED_TO_OBSERVE"] else "COMPLETE"
    return {
        "baseline_version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "INFRA_ASSURANCE_RUNTIME_HARDENING_BASELINE",
        "baseline_status": status,
        "mutation_allowed": False,
        "safety": {
            "systemd_mutation_performed": False,
            "permission_mutation_performed": False,
            "scheduler_mutation_performed": False,
            "backup_mutation_performed": False,
            "infrastructure_mutation_performed": False,
            "environment_file_contents_inspected": False,
            "artifact_contents_inspected": False,
            "journal_messages_inspected": False,
            "secret_values_inspected": False,
        },
        "finding_counts": {classification: len(findings[classification]) for classification in CLASSES},
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only M8 baseline for the infra-assurance collector runtime."
    )
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[2]
    )
    args = parser.parse_args()
    result = collect(args.repo_root.resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["baseline_status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
