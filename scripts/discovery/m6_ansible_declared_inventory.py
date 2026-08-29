from __future__ import annotations

import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

SOURCE_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TRACKED_FILES = 10000

_SAFE_PATH = re.compile(r"^[A-Za-z0-9_./+@:-]{1,500}$")
_SENSITIVE_PATH_TOKEN = re.compile(
    r"(?:^|[-_.])(secret|secrets|credential|credentials|password|passwd|private[-_]?key|token|vault[-_]?pass)(?:$|[-_.])",
    re.IGNORECASE,
)
_SAFE_DIR_TOKEN = re.compile(r"^[A-Za-z0-9_.-]{1,160}$")
_YAML_SUFFIXES = {".yml", ".yaml"}
_INVENTORY_SUFFIXES = {".yml", ".yaml", ".ini", ""}

_PLAY_HOSTS_RE = re.compile(r"(?m)^\s*-?\s*hosts\s*:\s*[^#\n]+")
_PLAY_TASK_RE = re.compile(r"(?m)^\s*(tasks|roles|pre_tasks|post_tasks)\s*:\s*(?:#.*)?$")
_INI_GROUP_RE = re.compile(r"^\s*\[([^\]\n:]+)(?::(?:children|vars))?\]\s*(?:#.*)?$")
_YAML_GROUP_RE = re.compile(r"^(\s*)([A-Za-z0-9_.-]+)\s*:\s*(?:#.*)?$")
_YAML_HOSTS_KEY_RE = re.compile(r"^\s*hosts\s*:\s*(?:#.*)?$")
_YAML_CHILDREN_KEY_RE = re.compile(r"^\s*children\s*:\s*(?:#.*)?$")


def _run_git_ls_files(repo: Path) -> tuple[str, list[str]]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "ls-files"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except Exception:
        return "FAILED_TO_OBSERVE", []
    if proc.returncode != 0:
        return "FAILED_TO_OBSERVE", []
    rows = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if len(rows) > MAX_TRACKED_FILES:
        return "FAILED_TO_OBSERVE", []
    return "COMPLETE", rows


def _safe_path(value: str) -> str | None:
    if not _SAFE_PATH.fullmatch(value):
        return None
    try:
        path = PurePosixPath(value)
    except Exception:
        return None
    if path.is_absolute() or ".." in path.parts:
        return None
    if any(_SENSITIVE_PATH_TOKEN.search(part) for part in path.parts):
        return None
    return path.as_posix()


def _is_ansible_scope(path: PurePosixPath) -> bool:
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    return (
        "ansible" in parts
        or "inventories" in parts
        or "inventory" in parts
        or "playbooks" in parts
        or "roles" in parts
        or name in {"ansible.cfg", "hosts", "inventory", "inventory.ini", "inventory.yml", "inventory.yaml", "site.yml", "site.yaml"}
    )


def _is_sensitive_ansible_data_path(path: PurePosixPath) -> bool:
    lowered = {part.lower() for part in path.parts}
    return bool(lowered & {"group_vars", "host_vars", "vars"})


def _inventory_candidate(path: PurePosixPath) -> bool:
    if _is_sensitive_ansible_data_path(path):
        return False
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    suffix = path.suffix.lower()
    if suffix not in _INVENTORY_SUFFIXES:
        return False
    return (
        "inventories" in parts
        or "inventory" in parts
        or name in {"hosts", "inventory", "inventory.ini", "inventory.yml", "inventory.yaml", "hosts.ini", "hosts.yml", "hosts.yaml"}
    )


def _role_directory(path: PurePosixPath) -> str | None:
    parts = list(path.parts)
    lowered = [part.lower() for part in parts]
    if "roles" not in lowered:
        return None
    index = lowered.index("roles")
    if index + 1 >= len(parts):
        return None
    role = parts[index + 1]
    if not _SAFE_DIR_TOKEN.fullmatch(role):
        return None
    directory = PurePosixPath(*parts[: index + 2]).as_posix()
    return directory


def _strip_full_line_comments(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(raw)
    return "\n".join(lines)


def _looks_like_playbook(path: PurePosixPath, text: str) -> bool:
    if path.suffix.lower() not in _YAML_SUFFIXES:
        return False
    lowered = {part.lower() for part in path.parts}
    if lowered & {"roles", "group_vars", "host_vars", "vars", "defaults", "handlers", "tasks", "meta"}:
        return False
    active = _strip_full_line_comments(text)
    if "playbooks" in lowered or path.name.lower() in {"site.yml", "site.yaml", "playbook.yml", "playbook.yaml"}:
        return bool(_PLAY_HOSTS_RE.search(active))
    return bool(_PLAY_HOSTS_RE.search(active) and _PLAY_TASK_RE.search(active))


def _count_inventory_identifiers(path: PurePosixPath, text: str) -> tuple[int, int]:
    """Return bounded group/host declaration counts without returning identifiers.

    Counts are lexical hints only. They are not host reachability or managed-host evidence.
    """
    group_count = 0
    host_count = 0

    if path.suffix.lower() == ".ini" or path.suffix == "":
        current_section: str | None = None
        for raw in text.splitlines():
            stripped = raw.strip()
            if not stripped or stripped.startswith(("#", ";")):
                continue
            match = _INI_GROUP_RE.match(raw)
            if match:
                current_section = match.group(1)
                group_count += 1
                continue
            if current_section and not stripped.startswith("["):
                host_count += 1
        return group_count, host_count

    # YAML inventory: count safe mapping keys under `children:` as groups and
    # mapping keys below a `hosts:` marker as host declarations. Values are never returned.
    lines = text.splitlines()
    hosts_indent: int | None = None
    children_indent: int | None = None
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if _YAML_HOSTS_KEY_RE.match(raw):
            hosts_indent = indent
            continue
        if _YAML_CHILDREN_KEY_RE.match(raw):
            children_indent = indent
            continue
        match = _YAML_GROUP_RE.match(raw)
        if not match:
            continue
        key = match.group(2)
        if key in {"all", "hosts", "children", "vars"}:
            continue
        if hosts_indent is not None and indent > hosts_indent:
            host_count += 1
            continue
        if children_indent is not None and indent > children_indent:
            group_count += 1

        if hosts_indent is not None and indent <= hosts_indent:
            hosts_indent = None
        if children_indent is not None and indent <= children_indent:
            children_indent = None

    return group_count, host_count


def discover(repo: Path = SOURCE_REPO) -> dict[str, Any]:
    source_status, tracked = _run_git_ls_files(repo)
    result: dict[str, Any] = {
        "source_status": source_status,
        "tracked_files_returned": len(tracked),
        "ansible_scope_files": 0,
        "files_read": 0,
        "excluded_sensitive_ansible_data_files": 0,
        "read_or_decode_skips": 0,
        "oversize_skips": 0,
        "inventory_files": [],
        "playbook_files": [],
        "role_directories": set(),
        "inventory_group_declarations": 0,
        "inventory_host_declarations": 0,
        "inventory_identifier_counts_by_file": [],
    }
    if source_status != "COMPLETE":
        return result

    for raw_path in tracked:
        safe = _safe_path(raw_path)
        if safe is None:
            continue
        rel = PurePosixPath(safe)
        if not _is_ansible_scope(rel):
            continue
        result["ansible_scope_files"] += 1

        role_dir = _role_directory(rel)
        if role_dir is not None:
            result["role_directories"].add(role_dir)

        if _is_sensitive_ansible_data_path(rel):
            result["excluded_sensitive_ansible_data_files"] += 1
            continue

        should_read = _inventory_candidate(rel) or rel.suffix.lower() in _YAML_SUFFIXES
        if not should_read:
            continue
        path = repo / safe
        try:
            size = path.stat().st_size
        except OSError:
            result["read_or_decode_skips"] += 1
            continue
        if size > MAX_FILE_BYTES:
            result["oversize_skips"] += 1
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            result["read_or_decode_skips"] += 1
            continue
        result["files_read"] += 1

        if _inventory_candidate(rel):
            groups, hosts = _count_inventory_identifiers(rel, text)
            result["inventory_files"].append(safe)
            result["inventory_group_declarations"] += groups
            result["inventory_host_declarations"] += hosts
            result["inventory_identifier_counts_by_file"].append({"path": safe, "groups": groups, "hosts": hosts})

        if _looks_like_playbook(rel, text):
            result["playbook_files"].append(safe)

    result["inventory_files"] = sorted(set(result["inventory_files"]))
    result["playbook_files"] = sorted(set(result["playbook_files"]))
    result["role_directories"] = sorted(result["role_directories"])
    result["inventory_identifier_counts_by_file"].sort(key=lambda row: row["path"])

    if result["read_or_decode_skips"] or result["oversize_skips"]:
        result["source_status"] = "INCOMPLETE"
    return result


def main() -> int:
    print("===== M6 ANSIBLE DECLARED-STATE INVENTORY =====")
    print()
    print("===== DECLARED-STATE SOURCE =====")
    print("repository_alias: afpa-infra-rebuild")
    print("source_mode: GIT_TRACKED_SAFE_ANSIBLE_SOURCE_ONLY")
    print("mutation_allowed: False")
    print("ansible_cli_invoked: False")
    print("ssh_connections_performed: False")
    print("ansible_vault_contents_inspected: False")
    print("runtime_facts_inspected: False")

    result = discover()
    print("source_status:", result["source_status"])
    print("tracked_files_returned:", result["tracked_files_returned"])
    print("ansible_scope_files:", result["ansible_scope_files"])
    print("files_read:", result["files_read"])
    print("excluded_sensitive_ansible_data_files:", result["excluded_sensitive_ansible_data_files"])
    print("read_or_decode_skips:", result["read_or_decode_skips"])
    print("oversize_skips:", result["oversize_skips"])

    if result["source_status"] != "COMPLETE":
        print("ansible_declared_inventory_status: FAILED_TO_OBSERVE")
        print("No declared Ansible coverage conclusion is allowed.")
        print("No mutation was performed.")
        return 2

    print()
    print("===== INVENTORY CANDIDATES =====")
    if not result["inventory_files"]:
        print("inventory_files: NONE_OBSERVED_IN_BOUNDED_SOURCE")
    for row in result["inventory_identifier_counts_by_file"]:
        print(f"path={row['path']} group_declaration_count={row['groups']} host_declaration_count={row['hosts']}")

    print()
    print("===== PLAYBOOK CANDIDATES =====")
    if not result["playbook_files"]:
        print("playbook_files: NONE_OBSERVED_IN_BOUNDED_SOURCE")
    for path in result["playbook_files"]:
        print(f"path={path}")

    print()
    print("===== ROLE DIRECTORIES =====")
    if not result["role_directories"]:
        print("role_directories: NONE_OBSERVED_IN_BOUNDED_SOURCE")
    for directory in result["role_directories"]:
        print(f"directory={directory}")

    print()
    print("===== SUMMARY =====")
    print("inventory_files_total:", len(result["inventory_files"]))
    print("playbook_files_total:", len(result["playbook_files"]))
    print("role_directories_total:", len(result["role_directories"]))
    print("inventory_group_declarations:", result["inventory_group_declarations"])
    print("inventory_host_declarations:", result["inventory_host_declarations"])
    print("managed_host_coverage_status: DECLARED_CONFIGURATION_ONLY")
    print("live_managed_host_coverage_status: UNKNOWN")
    print("execution_outcome_status: UNKNOWN")
    print("configuration_drift_status: UNKNOWN")
    print("execution_success_claims: 0")
    print("drift_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("Inventory, playbook, and role findings are Git-tracked declared configuration only; they are not evidence that hosts are reachable or currently managed.")
    print("Inventory host/group counts are bounded lexical declaration counts. Hostnames, addresses, variables, and values are not projected.")
    print("Role-directory presence does not establish that a role is invoked by an accepted playbook.")
    print("No Ansible execution result, host fact, configuration state, idempotence result, or drift result is inferred.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only bounded Git-tracked Ansible source structure was inspected.")
    print("group_vars, host_vars, and vars contents were excluded from reading in this slice.")
    print("Ansible Vault contents, vault passwords, host addresses, inventory variable values, ansible_password, become passwords, private keys, credentials, tokens, and connection strings were not printed or persisted.")
    print("Ansible CLI was not invoked and no SSH or managed-host connection was performed.")
    print("No repository or infrastructure mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
