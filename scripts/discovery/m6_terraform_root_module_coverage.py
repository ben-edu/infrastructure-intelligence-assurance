from __future__ import annotations

import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

SOURCE_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TRACKED_TF_FILES = 2000

_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_-]{1,160}$")
_SENSITIVE_PATH_TOKEN = re.compile(
    r"(?:^|[-_.])(secret|secrets|credential|credentials|password|passwd|private[-_]?key|cert|certificate|token)(?:$|[-_.])",
    re.IGNORECASE,
)
_RESOURCE_RE = re.compile(r'\bresource\s+"([A-Za-z0-9_-]+)"\s+"[^"]+"\s*{')
_MODULE_HEADER_RE = re.compile(r'\bmodule\s+"[^"]+"\s*{')
_SOURCE_LITERAL_RE = re.compile(r'\bsource\s*=\s*"([^"]+)"')


def _run_git_ls_files(repo: Path) -> tuple[str, list[str]]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--", "*.tf"],
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
    if len(rows) > MAX_TRACKED_TF_FILES:
        return "FAILED_TO_OBSERVE", []
    return "COMPLETE", rows


def _safe_relative_tf_path(value: str) -> str | None:
    try:
        path = PurePosixPath(value)
    except Exception:
        return None
    if path.is_absolute() or ".." in path.parts or path.suffix != ".tf":
        return None
    lowered_parts = [part.lower() for part in path.parts]
    if ".terraform" in lowered_parts:
        return None
    if any(_SENSITIVE_PATH_TOKEN.search(part) for part in path.parts):
        return None
    return path.as_posix()


def _safe_directory_id(value: str) -> str | None:
    try:
        path = PurePosixPath(value)
    except Exception:
        return None
    if path.is_absolute() or ".." in path.parts:
        return None
    if any(_SENSITIVE_PATH_TOKEN.search(part) for part in path.parts):
        return None
    return "." if str(path) == "." else path.as_posix()


def _strip_hcl_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    in_string = False
    escaped = False
    in_line_comment = False
    in_block_comment = False

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                out.append("\n")
            else:
                out.append(" ")
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                out.extend((" ", " "))
                in_block_comment = False
                i += 2
            else:
                out.append("\n" if ch == "\n" else " ")
                i += 1
            continue

        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "#":
            in_line_comment = True
            out.append(" ")
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            out.extend((" ", " "))
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            out.extend((" ", " "))
            i += 2
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def _matching_brace(text: str, opening_index: int) -> int | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(opening_index, len(text)):
        ch = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _module_source_literals(text: str) -> list[str | None]:
    sanitized = _strip_hcl_comments(text)
    results: list[str | None] = []
    for match in _MODULE_HEADER_RE.finditer(sanitized):
        opening = sanitized.find("{", match.start(), match.end())
        if opening < 0:
            results.append(None)
            continue
        closing = _matching_brace(sanitized, opening)
        if closing is None:
            results.append(None)
            continue
        body = sanitized[opening + 1 : closing]
        source_match = _SOURCE_LITERAL_RE.search(body)
        results.append(source_match.group(1) if source_match else None)
    return results


def _resource_types(text: str) -> Counter[str]:
    sanitized = _strip_hcl_comments(text)
    counter: Counter[str] = Counter()
    for match in _RESOURCE_RE.finditer(sanitized):
        resource_type = match.group(1)
        if _SAFE_TOKEN.fullmatch(resource_type):
            counter[resource_type] += 1
    return counter


def _directory_classification(directory: str) -> str:
    parts = {part.lower() for part in PurePosixPath(directory).parts}
    return "MODULE_DIRECTORY" if "modules" in parts else "ROOT_CANDIDATE"


def _resolve_local_module_directory(
    repo: Path,
    root_directory: str,
    source_value: str | None,
    tracked_directories: set[str],
) -> tuple[str, str | None]:
    if not isinstance(source_value, str) or not source_value.strip():
        return "SOURCE_NOT_LITERAL", None
    source_value = source_value.strip()
    if not (source_value.startswith("./") or source_value.startswith("../")):
        return "NONLOCAL_SOURCE", None

    try:
        repo_resolved = repo.resolve()
        root_resolved = (repo_resolved / root_directory).resolve()
        target = (root_resolved / source_value).resolve()
        target.relative_to(repo_resolved)
    except (OSError, RuntimeError, ValueError):
        return "LOCAL_SOURCE_OUTSIDE_BOUNDED_REPO", None

    try:
        relative = target.relative_to(repo_resolved).as_posix()
    except ValueError:
        return "LOCAL_SOURCE_OUTSIDE_BOUNDED_REPO", None

    safe_relative = _safe_directory_id(relative)
    if safe_relative is None:
        return "LOCAL_SOURCE_UNSAFE_TARGET", None
    if safe_relative not in tracked_directories:
        return "LOCAL_SOURCE_TARGET_NOT_IN_TRACKED_TF_SCOPE", None
    return "RESOLVED_LOCAL_MODULE", safe_relative


def discover(repo: Path = SOURCE_REPO) -> dict[str, Any]:
    source_status, raw_paths = _run_git_ls_files(repo)
    result: dict[str, Any] = {
        "source_status": source_status,
        "tracked_tf_files_returned": len(raw_paths),
        "tracked_tf_files_scanned": 0,
        "excluded_or_unsafe_paths": 0,
        "read_or_decode_skips": 0,
        "oversize_skips": 0,
        "roots": [],
        "relationships_resolved": 0,
        "module_blocks_total": 0,
        "module_sources_nonlocal": 0,
        "module_sources_not_literal": 0,
        "module_sources_outside_or_unsafe": 0,
        "module_sources_target_not_in_scope": 0,
        "roots_with_resolved_local_module": 0,
        "roots_with_declared_resource_path": 0,
    }
    if source_status != "COMPLETE":
        return result

    texts_by_path: dict[str, str] = {}
    files_by_directory: dict[str, list[str]] = defaultdict(list)

    for raw_path in raw_paths:
        safe_path = _safe_relative_tf_path(raw_path)
        if safe_path is None:
            result["excluded_or_unsafe_paths"] += 1
            continue
        path = repo / safe_path
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

        texts_by_path[safe_path] = text
        parent = PurePosixPath(safe_path).parent
        directory = "." if str(parent) == "." else parent.as_posix()
        files_by_directory[directory].append(safe_path)
        result["tracked_tf_files_scanned"] += 1

    tracked_directories = set(files_by_directory)
    resources_by_directory: dict[str, Counter[str]] = {}
    for directory, files in files_by_directory.items():
        counter: Counter[str] = Counter()
        for file_path in files:
            counter.update(_resource_types(texts_by_path[file_path]))
        resources_by_directory[directory] = counter

    root_directories = sorted(
        directory
        for directory in tracked_directories
        if _directory_classification(directory) == "ROOT_CANDIDATE"
    )

    for root_directory in root_directories:
        module_sources: list[str | None] = []
        for file_path in files_by_directory[root_directory]:
            module_sources.extend(_module_source_literals(texts_by_path[file_path]))

        resolved_directories: list[str] = []
        reachable_types: Counter[str] = Counter()
        nonlocal_count = 0
        not_literal_count = 0
        outside_or_unsafe_count = 0
        target_not_in_scope_count = 0

        for source_value in module_sources:
            status, resolved = _resolve_local_module_directory(
                repo,
                root_directory,
                source_value,
                tracked_directories,
            )
            if status == "RESOLVED_LOCAL_MODULE" and resolved is not None:
                resolved_directories.append(resolved)
                reachable_types.update(resources_by_directory.get(resolved, Counter()))
                result["relationships_resolved"] += 1
            elif status == "NONLOCAL_SOURCE":
                nonlocal_count += 1
                result["module_sources_nonlocal"] += 1
            elif status == "SOURCE_NOT_LITERAL":
                not_literal_count += 1
                result["module_sources_not_literal"] += 1
            elif status == "LOCAL_SOURCE_TARGET_NOT_IN_TRACKED_TF_SCOPE":
                target_not_in_scope_count += 1
                result["module_sources_target_not_in_scope"] += 1
            else:
                outside_or_unsafe_count += 1
                result["module_sources_outside_or_unsafe"] += 1

        result["module_blocks_total"] += len(module_sources)
        unique_resolved = sorted(set(resolved_directories))

        if unique_resolved:
            result["roots_with_resolved_local_module"] += 1
        if reachable_types:
            path_status = "RESOLVED_LOCAL_MODULE_TO_DECLARED_RESOURCE"
            result["roots_with_declared_resource_path"] += 1
        elif unique_resolved:
            path_status = "RESOLVED_LOCAL_MODULE_WITHOUT_DECLARED_RESOURCE"
        elif module_sources:
            path_status = "NO_RESOLVED_LOCAL_MODULE"
        else:
            path_status = "NO_MODULE_BLOCK_OBSERVED"

        result["roots"].append(
            {
                "root_directory": root_directory,
                "module_blocks": len(module_sources),
                "resolved_local_module_relationships": len(resolved_directories),
                "resolved_module_directories": unique_resolved,
                "reachable_resource_types": dict(sorted(reachable_types.items())),
                "nonlocal_module_sources": nonlocal_count,
                "nonliteral_module_sources": not_literal_count,
                "outside_or_unsafe_local_sources": outside_or_unsafe_count,
                "local_targets_not_in_tracked_scope": target_not_in_scope_count,
                "structural_declared_resource_path_status": path_status,
            }
        )

    if result["read_or_decode_skips"] or result["oversize_skips"]:
        result["source_status"] = "INCOMPLETE"
    return result


def _format_types(values: dict[str, int]) -> str:
    if not values:
        return "NONE_OBSERVED"
    return ",".join(f"{key}={values[key]}" for key in sorted(values))


def main() -> int:
    print("===== M6 TERRAFORM ROOT-TO-MODULE DECLARED COVERAGE =====")
    print()
    print("===== DECLARED-STATE SOURCE =====")
    print("repository_alias: afpa-infra-rebuild")
    print("source_mode: GIT_TRACKED_TF_ONLY")
    print("mutation_allowed: False")
    print("terraform_state_inspected: False")
    print("terraform_tfvars_inspected: False")
    print("terraform_cli_invoked: False")
    print("provider_live_verification_performed: False")

    result = discover()
    print("source_status:", result["source_status"])
    print("tracked_tf_files_returned:", result["tracked_tf_files_returned"])
    print("tracked_tf_files_scanned:", result["tracked_tf_files_scanned"])
    print("excluded_or_unsafe_paths:", result["excluded_or_unsafe_paths"])
    print("read_or_decode_skips:", result["read_or_decode_skips"])
    print("oversize_skips:", result["oversize_skips"])

    if result["source_status"] != "COMPLETE":
        print("declared_coverage_relationship_status: FAILED_TO_OBSERVE")
        print("No root-to-module coverage conclusion is allowed.")
        print("No mutation was performed.")
        return 2

    print()
    print("===== ROOT-TO-MODULE RELATIONSHIPS =====")
    if not result["roots"]:
        print("root_candidates: NONE_OBSERVED_IN_BOUNDED_GIT_TRACKED_SOURCE")
    for row in result["roots"]:
        resolved_dirs = ",".join(row["resolved_module_directories"]) or "NONE_OBSERVED"
        print(
            f"root={row['root_directory']}"
            f" module_blocks={row['module_blocks']}"
            f" resolved_local_module_relationships={row['resolved_local_module_relationships']}"
            f" resolved_module_directories={resolved_dirs}"
            f" reachable_resource_types={_format_types(row['reachable_resource_types'])}"
            f" structural_declared_resource_path_status={row['structural_declared_resource_path_status']}"
        )

    print()
    print("===== SUMMARY =====")
    print("root_candidates_total:", len(result["roots"]))
    print("module_blocks_total:", result["module_blocks_total"])
    print("relationships_resolved:", result["relationships_resolved"])
    print("roots_with_resolved_local_module:", result["roots_with_resolved_local_module"])
    print("roots_with_declared_resource_path:", result["roots_with_declared_resource_path"])
    print("module_sources_nonlocal:", result["module_sources_nonlocal"])
    print("module_sources_not_literal:", result["module_sources_not_literal"])
    print("module_sources_outside_or_unsafe:", result["module_sources_outside_or_unsafe"])
    print("module_sources_target_not_in_scope:", result["module_sources_target_not_in_scope"])
    print("declared_resource_path_coverage_status: STRUCTURAL_CONFIGURATION_ONLY")
    print("live_resource_coverage_status: UNKNOWN")
    print("state_backed_coverage_status: UNKNOWN")
    print("drift_claims: 0")
    print("destructive_change_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("A resolved local module relationship is declared configuration structure only; it is not evidence of Terraform state membership or live infrastructure existence.")
    print("Reachable resource types describe resource blocks in the resolved local module directory only; they do not establish resource instance count at runtime.")
    print("Nonlocal module sources are counted but not followed. Module source values and module block names are never printed.")
    print("No state-backed coverage, provider reachability, plan/apply result, drift, or destructive-change result is inferred.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only Git-tracked .tf files from the bounded infrastructure repository were read.")
    print("Relative local module source values were used in memory only for bounded path resolution and were not printed or persisted.")
    print("Raw HCL lines, module block names, module source values, resource instance names, variable values, provider/backend values, and sensitive connection strings were not printed.")
    print("Terraform state/state backups, real tfvars, .env files, secrets, credentials, private keys, certificates, and provider tokens/passwords were not read or printed.")
    print("Terraform CLI and provider live APIs were not invoked. No infrastructure or repository mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
