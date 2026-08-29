from __future__ import annotations

import re
import subprocess
from collections import defaultdict
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
_SAFE_ROLE_TOKEN = re.compile(r"^[A-Za-z0-9_.-]{1,160}$")
_YAML_SUFFIXES = {".yml", ".yaml"}
_PLAY_HOSTS_RE = re.compile(r"(?m)^\s*-?\s*hosts\s*:\s*[^#\n]+")
_PLAY_TASK_RE = re.compile(r"(?m)^\s*(tasks|roles|pre_tasks|post_tasks)\s*:\s*(?:#.*)?$")
_ROLES_BLOCK_RE = re.compile(r"^(?P<indent>\s*)roles\s*:\s*(?:#.*)?$")
_ROLE_LIST_SCALAR_RE = re.compile(r"^\s*-\s*(?P<role>[A-Za-z0-9_.-]+)\s*(?:#.*)?$")
_ROLE_LIST_MAPPING_RE = re.compile(r"^\s*-\s*role\s*:\s*(?P<role>[A-Za-z0-9_.-]+)\s*(?:#.*)?$")
_ROLE_ACTION_RE = re.compile(
    r"^(?P<indent>\s*)-?\s*(?:(?:ansible\.builtin\.)?(?:include_role|import_role))\s*:\s*(?:#.*)?$"
)
_ROLE_ACTION_NAME_RE = re.compile(r"^\s*name\s*:\s*(?P<role>[A-Za-z0-9_.-]+)\s*(?:#.*)?$")


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


def _is_sensitive_ansible_data_path(path: PurePosixPath) -> bool:
    lowered = {part.lower() for part in path.parts}
    return bool(lowered & {"group_vars", "host_vars", "vars"})


def _role_directory(path: PurePosixPath) -> str | None:
    parts = list(path.parts)
    lowered = [part.lower() for part in parts]
    if "roles" not in lowered:
        return None
    index = lowered.index("roles")
    if index + 1 >= len(parts):
        return None
    role_name = parts[index + 1]
    if not _SAFE_ROLE_TOKEN.fullmatch(role_name):
        return None
    return PurePosixPath(*parts[: index + 2]).as_posix()


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


def _safe_role_token(value: str) -> str | None:
    value = value.strip()
    return value if _SAFE_ROLE_TOKEN.fullmatch(value) else None


def _extract_direct_role_reference_tokens(text: str) -> tuple[list[str], int]:
    """Extract bounded simple role tokens without returning play/host/task values.

    Supported structures:
    - roles: list with scalar role names
    - roles: list entries using `role: <name>`
    - include_role/import_role (including ansible.builtin FQCN) with a simple `name:`

    Dynamic/Jinja/complex role expressions are not resolved. Their presence is counted as
    unparsed role structure where structurally detectable, preserving UNKNOWN rather than
    guessing a local relationship.
    """
    tokens: list[str] = []
    unparsed_structures = 0
    lines = text.splitlines()

    roles_indent: int | None = None
    action_indent: int | None = None

    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))

        if roles_indent is not None and indent <= roles_indent:
            roles_indent = None
        if action_indent is not None and indent <= action_indent:
            action_indent = None

        roles_match = _ROLES_BLOCK_RE.match(raw)
        if roles_match:
            roles_indent = len(roles_match.group("indent"))
            continue

        action_match = _ROLE_ACTION_RE.match(raw)
        if action_match:
            action_indent = len(action_match.group("indent"))
            continue

        if roles_indent is not None and indent > roles_indent:
            scalar_match = _ROLE_LIST_SCALAR_RE.match(raw)
            mapping_match = _ROLE_LIST_MAPPING_RE.match(raw)
            match = mapping_match or scalar_match
            if match:
                token = _safe_role_token(match.group("role"))
                if token is not None:
                    tokens.append(token)
                else:
                    unparsed_structures += 1
                continue
            if stripped.startswith("-") and not stripped.startswith("- name:"):
                # A role-list entry exists but is not a simple literal form supported here.
                unparsed_structures += 1
                continue

        if action_indent is not None and indent > action_indent:
            name_match = _ROLE_ACTION_NAME_RE.match(raw)
            if name_match:
                token = _safe_role_token(name_match.group("role"))
                if token is not None:
                    tokens.append(token)
                else:
                    unparsed_structures += 1
                action_indent = None
                continue
            if stripped.startswith("name:"):
                unparsed_structures += 1
                action_indent = None

    return tokens, unparsed_structures


def discover(repo: Path = SOURCE_REPO) -> dict[str, Any]:
    source_status, tracked = _run_git_ls_files(repo)
    result: dict[str, Any] = {
        "source_status": source_status,
        "tracked_files_returned": len(tracked),
        "playbook_files_scanned": 0,
        "read_or_decode_skips": 0,
        "oversize_skips": 0,
        "role_directories": [],
        "playbooks": [],
        "playbooks_with_resolved_local_role": 0,
        "playbooks_with_no_role_reference": 0,
        "playbooks_with_unknown_role_reference": 0,
        "resolved_role_reference_signals": 0,
        "unresolved_role_reference_signals": 0,
        "unparsed_role_structures": 0,
        "referenced_role_directories": set(),
    }
    if source_status != "COMPLETE":
        return result

    safe_tracked: list[str] = []
    role_directories: set[str] = set()
    for raw_path in tracked:
        safe = _safe_path(raw_path)
        if safe is None:
            continue
        rel = PurePosixPath(safe)
        safe_tracked.append(safe)
        role_dir = _role_directory(rel)
        if role_dir is not None:
            role_directories.add(role_dir)

    result["role_directories"] = sorted(role_directories)
    role_dirs_by_name: dict[str, list[str]] = defaultdict(list)
    for directory in result["role_directories"]:
        role_dirs_by_name[PurePosixPath(directory).name].append(directory)

    for safe in safe_tracked:
        rel = PurePosixPath(safe)
        if rel.suffix.lower() not in _YAML_SUFFIXES or _is_sensitive_ansible_data_path(rel):
            continue
        lowered = {part.lower() for part in rel.parts}
        if lowered & {"roles", "group_vars", "host_vars", "vars", "defaults", "handlers", "tasks", "meta"}:
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

        if not _looks_like_playbook(rel, text):
            continue
        result["playbook_files_scanned"] += 1

        tokens, unparsed = _extract_direct_role_reference_tokens(text)
        resolved: set[str] = set()
        unresolved_count = 0
        for token in tokens:
            candidates = role_dirs_by_name.get(token, [])
            if len(candidates) == 1:
                resolved.add(candidates[0])
                result["resolved_role_reference_signals"] += 1
            else:
                unresolved_count += 1
                result["unresolved_role_reference_signals"] += 1

        result["unparsed_role_structures"] += unparsed
        result["referenced_role_directories"].update(resolved)

        if resolved:
            relationship_status = "RESOLVED_LOCAL_ROLE"
            result["playbooks_with_resolved_local_role"] += 1
        elif tokens or unparsed:
            relationship_status = "UNKNOWN"
            result["playbooks_with_unknown_role_reference"] += 1
        else:
            relationship_status = "NONE_OBSERVED"
            result["playbooks_with_no_role_reference"] += 1

        result["playbooks"].append(
            {
                "path": safe,
                "role_reference_signals": len(tokens) + unparsed,
                "resolved_local_role_directories": sorted(resolved),
                "unresolved_role_reference_count": unresolved_count,
                "unparsed_role_structure_count": unparsed,
                "relationship_status": relationship_status,
            }
        )

    result["playbooks"].sort(key=lambda row: row["path"])
    result["referenced_role_directories"] = sorted(result["referenced_role_directories"])
    result["unreferenced_role_directories"] = sorted(
        set(result["role_directories"]) - set(result["referenced_role_directories"])
    )

    if result["read_or_decode_skips"] or result["oversize_skips"]:
        result["source_status"] = "INCOMPLETE"
    return result


def _csv(values: list[str]) -> str:
    return ",".join(values) if values else "NONE_OBSERVED"


def main() -> int:
    print("===== M6 ANSIBLE PLAYBOOK-TO-ROLE DECLARED COVERAGE =====")
    print()
    print("===== DECLARED-STATE SOURCE =====")
    print("repository_alias: afpa-infra-rebuild")
    print("source_mode: GIT_TRACKED_SAFE_ANSIBLE_PLAYBOOK_STRUCTURE_ONLY")
    print("mutation_allowed: False")
    print("ansible_cli_invoked: False")
    print("ssh_connections_performed: False")
    print("runtime_facts_inspected: False")
    print("ansible_vault_contents_inspected: False")

    result = discover()
    print("source_status:", result["source_status"])
    print("tracked_files_returned:", result["tracked_files_returned"])
    print("playbook_files_scanned:", result["playbook_files_scanned"])
    print("read_or_decode_skips:", result["read_or_decode_skips"])
    print("oversize_skips:", result["oversize_skips"])

    if result["source_status"] != "COMPLETE":
        print("playbook_role_coverage_status: FAILED_TO_OBSERVE")
        print("No playbook-to-role relationship conclusion is allowed.")
        print("No mutation was performed.")
        return 2

    print()
    print("===== PLAYBOOK-TO-ROLE RELATIONSHIPS =====")
    if not result["playbooks"]:
        print("playbook_candidates: NONE_OBSERVED_IN_BOUNDED_SOURCE")
    for row in result["playbooks"]:
        print(
            f"playbook={row['path']}"
            f" role_reference_signals={row['role_reference_signals']}"
            f" resolved_local_role_directories={_csv(row['resolved_local_role_directories'])}"
            f" unresolved_role_reference_count={row['unresolved_role_reference_count']}"
            f" unparsed_role_structure_count={row['unparsed_role_structure_count']}"
            f" relationship_status={row['relationship_status']}"
        )

    print()
    print("===== ROLE COVERAGE SUMMARY =====")
    print("declared_role_directories_total:", len(result["role_directories"]))
    print("referenced_role_directories_total:", len(result["referenced_role_directories"]))
    print("unreferenced_in_direct_playbook_scope_total:", len(result["unreferenced_role_directories"]))
    print("referenced_role_directories:", _csv(result["referenced_role_directories"]))
    print("unreferenced_in_direct_playbook_scope:", _csv(result["unreferenced_role_directories"]))
    print("playbooks_with_resolved_local_role:", result["playbooks_with_resolved_local_role"])
    print("playbooks_with_no_role_reference:", result["playbooks_with_no_role_reference"])
    print("playbooks_with_unknown_role_reference:", result["playbooks_with_unknown_role_reference"])
    print("resolved_role_reference_signals:", result["resolved_role_reference_signals"])
    print("unresolved_role_reference_signals:", result["unresolved_role_reference_signals"])
    print("unparsed_role_structures:", result["unparsed_role_structures"])
    print("declared_role_coverage_status: STRUCTURAL_CONFIGURATION_ONLY")
    print("live_managed_host_coverage_status: UNKNOWN")
    print("execution_outcome_status: UNKNOWN")
    print("idempotence_status: UNKNOWN")
    print("configuration_drift_status: UNKNOWN")
    print("execution_success_claims: 0")
    print("drift_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("A resolved local role relationship is Git-tracked declared playbook structure only; it is not evidence that the role executed or changed any host.")
    print("NONE_OBSERVED means no supported direct role-reference structure was observed in that playbook; it does not prove the playbook cannot reach roles indirectly.")
    print("A role directory unreferenced in this direct playbook scope is not automatically unused; role dependencies, nested includes, dynamic expressions, or other entry points may exist outside this slice.")
    print("UNKNOWN is preserved for detected role-reference structure that cannot be safely resolved to exactly one accepted local role directory.")
    print("No host reachability, execution result, idempotence result, runtime fact, or drift result is inferred.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only bounded Git-tracked playbook/role structure was inspected.")
    print("Play names, hosts/target patterns, hostnames, IP addresses, inventory values, group_vars/host_vars/vars contents, role/task argument values, handler contents, and Vault contents were not projected or persisted.")
    print("Only simple safe role tokens needed for local role-directory resolution were retained in memory; unresolved role token values were not printed.")
    print("Ansible CLI was not invoked and no SSH or managed-host connection was performed.")
    print("No repository or infrastructure mutation was performed by the discovery.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
