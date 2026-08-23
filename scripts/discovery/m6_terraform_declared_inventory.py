from __future__ import annotations

import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Iterable

SOURCE_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TRACKED_TF_FILES = 2000

_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_-]{1,160}$")
_SENSITIVE_PATH_TOKEN = re.compile(
    r"(?:^|[-_.])(secret|secrets|credential|credentials|password|passwd|private[-_]?key|cert|certificate|token)(?:$|[-_.])",
    re.IGNORECASE,
)

_RESOURCE_RE = re.compile(r'\bresource\s+"([A-Za-z0-9_-]+)"\s+"[^"]+"\s*{')
_DATA_RE = re.compile(r'\bdata\s+"([A-Za-z0-9_-]+)"\s+"[^"]+"\s*{')
_PROVIDER_RE = re.compile(r'\bprovider\s+"([A-Za-z0-9_-]+)"\s*{')
_BACKEND_RE = re.compile(r'\bbackend\s+"([A-Za-z0-9_-]+)"\s*{')
_MODULE_RE = re.compile(r'\bmodule\s+"[^"]+"\s*{')
_VARIABLE_RE = re.compile(r'\bvariable\s+"[^"]+"\s*{')
_OUTPUT_RE = re.compile(r'\boutput\s+"[^"]+"\s*{')
_CLOUD_RE = re.compile(r'\bcloud\s*{')
_WORKSPACES_RE = re.compile(r'\bworkspaces\s*{')


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


def _strip_hcl_comments(text: str) -> str:
    """Remove HCL comments while preserving quoted-string contents.

    The sanitized text is used only for structural block-header matching. It is never printed.
    """
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


def _safe_tokens(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if _SAFE_TOKEN.fullmatch(value)})


def _parse_structure(text: str) -> dict[str, object]:
    sanitized = _strip_hcl_comments(text)
    resources = _safe_tokens(match.group(1) for match in _RESOURCE_RE.finditer(sanitized))
    data_sources = _safe_tokens(match.group(1) for match in _DATA_RE.finditer(sanitized))
    providers = _safe_tokens(match.group(1) for match in _PROVIDER_RE.finditer(sanitized))
    backends = _safe_tokens(match.group(1) for match in _BACKEND_RE.finditer(sanitized))
    return {
        "resource_types": resources,
        "resource_blocks": len(list(_RESOURCE_RE.finditer(sanitized))),
        "data_source_types": data_sources,
        "data_blocks": len(list(_DATA_RE.finditer(sanitized))),
        "provider_types": providers,
        "provider_blocks": len(list(_PROVIDER_RE.finditer(sanitized))),
        "backend_types": backends,
        "backend_blocks": len(list(_BACKEND_RE.finditer(sanitized))),
        "module_blocks": len(list(_MODULE_RE.finditer(sanitized))),
        "variable_blocks": len(list(_VARIABLE_RE.finditer(sanitized))),
        "output_blocks": len(list(_OUTPUT_RE.finditer(sanitized))),
        "cloud_blocks": len(list(_CLOUD_RE.finditer(sanitized))),
        "workspaces_blocks": len(list(_WORKSPACES_RE.finditer(sanitized))),
    }


def _directory_classification(relative_path: str) -> tuple[str, str]:
    parent = PurePosixPath(relative_path).parent
    directory = "." if str(parent) == "." else parent.as_posix()
    parts = {part.lower() for part in parent.parts}
    classification = "MODULE_DIRECTORY" if "modules" in parts else "ROOT_CANDIDATE"
    return directory, classification


def discover(repo: Path = SOURCE_REPO) -> dict[str, object]:
    source_status, tracked = _run_git_ls_files(repo)
    result: dict[str, object] = {
        "source_status": source_status,
        "tracked_tf_files_returned": len(tracked),
        "tracked_tf_files_scanned": 0,
        "excluded_or_unsafe_paths": 0,
        "read_or_decode_skips": 0,
        "oversize_skips": 0,
        "directories": {},
        "resource_type_counts": Counter(),
        "data_source_type_counts": Counter(),
        "provider_type_counts": Counter(),
        "backend_type_counts": Counter(),
        "resource_blocks": 0,
        "data_blocks": 0,
        "provider_blocks": 0,
        "backend_blocks": 0,
        "module_blocks": 0,
        "variable_blocks": 0,
        "output_blocks": 0,
        "cloud_blocks": 0,
        "workspaces_blocks": 0,
    }
    if source_status != "COMPLETE":
        return result

    directory_files: dict[str, int] = defaultdict(int)
    directory_classes: dict[str, str] = {}

    for raw_path in tracked:
        relative_path = _safe_relative_tf_path(raw_path)
        if relative_path is None:
            result["excluded_or_unsafe_paths"] = int(result["excluded_or_unsafe_paths"]) + 1
            continue
        path = repo / relative_path
        try:
            size = path.stat().st_size
        except OSError:
            result["read_or_decode_skips"] = int(result["read_or_decode_skips"]) + 1
            continue
        if size > MAX_FILE_BYTES:
            result["oversize_skips"] = int(result["oversize_skips"]) + 1
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            result["read_or_decode_skips"] = int(result["read_or_decode_skips"]) + 1
            continue

        parsed = _parse_structure(text)
        result["tracked_tf_files_scanned"] = int(result["tracked_tf_files_scanned"]) + 1
        directory, classification = _directory_classification(relative_path)
        directory_files[directory] += 1
        directory_classes[directory] = classification

        for resource_type in parsed["resource_types"]:
            result["resource_type_counts"][resource_type] += 1
        for data_type in parsed["data_source_types"]:
            result["data_source_type_counts"][data_type] += 1
        for provider_type in parsed["provider_types"]:
            result["provider_type_counts"][provider_type] += 1
        for backend_type in parsed["backend_types"]:
            result["backend_type_counts"][backend_type] += 1

        for key in (
            "resource_blocks",
            "data_blocks",
            "provider_blocks",
            "backend_blocks",
            "module_blocks",
            "variable_blocks",
            "output_blocks",
            "cloud_blocks",
            "workspaces_blocks",
        ):
            result[key] = int(result[key]) + int(parsed[key])

    result["directories"] = {
        directory: {
            "classification": directory_classes[directory],
            "tf_file_count": directory_files[directory],
        }
        for directory in sorted(directory_files)
    }
    return result


def _format_counter(counter: Counter[str]) -> str:
    if not counter:
        return "NONE_OBSERVED"
    return ",".join(f"{key}={counter[key]}" for key in sorted(counter))


def main() -> int:
    print("===== M6 TERRAFORM DECLARED-STATE INVENTORY =====")
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
        print("declared_inventory_status: FAILED_TO_OBSERVE")
        print("No declared-resource coverage conclusion is allowed.")
        print("No mutation was performed.")
        return 2

    print()
    print("===== TERRAFORM DIRECTORY INVENTORY =====")
    directories = result["directories"]
    if not directories:
        print("terraform_directories: NONE_OBSERVED_IN_BOUNDED_GIT_TRACKED_SOURCE")
    for directory, metadata in directories.items():
        print(
            f"directory={directory} classification={metadata['classification']} "
            f"tf_files={metadata['tf_file_count']}"
        )

    root_candidates = sum(row["classification"] == "ROOT_CANDIDATE" for row in directories.values())
    module_directories = sum(row["classification"] == "MODULE_DIRECTORY" for row in directories.values())

    print()
    print("===== SAFE DECLARATION PROJECTION =====")
    print("backend_types:", _format_counter(result["backend_type_counts"]))
    print("provider_types:", _format_counter(result["provider_type_counts"]))
    print("resource_types:", _format_counter(result["resource_type_counts"]))
    print("data_source_types:", _format_counter(result["data_source_type_counts"]))

    print()
    print("===== SUMMARY =====")
    print("terraform_directories_total:", len(directories))
    print("root_candidates_heuristic:", root_candidates)
    print("module_directories_heuristic:", module_directories)
    print("backend_blocks:", result["backend_blocks"])
    print("provider_blocks:", result["provider_blocks"])
    print("resource_blocks:", result["resource_blocks"])
    print("data_blocks:", result["data_blocks"])
    print("module_blocks:", result["module_blocks"])
    print("variable_blocks:", result["variable_blocks"])
    print("output_blocks:", result["output_blocks"])
    print("cloud_blocks:", result["cloud_blocks"])
    print("workspaces_blocks:", result["workspaces_blocks"])
    print("managed_resource_coverage_status: DECLARED_CONFIGURATION_ONLY")
    print("live_resource_coverage_status: UNKNOWN")
    print("drift_claims: 0")
    print("destructive_change_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("ROOT_CANDIDATE and MODULE_DIRECTORY are structural heuristics, not authoritative Terraform stack/workspace identities.")
    print("Resource/provider/backend types are declared configuration evidence only; they do not establish live managed resources or provider connectivity.")
    print("Backend type does not establish backend reachability, workspace contents, state existence, or state freshness.")
    print("No Terraform state, real tfvars, plan, apply metadata, drift result, or destructive-change result is inferred.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only Git-tracked .tf files from the bounded infrastructure repository were read.")
    print("Raw HCL lines, resource instance names, variable names/defaults, output names/values, provider configuration values, backend values, and module source values were not printed.")
    print("Terraform state/state backups, real tfvars, .env files, secrets, credentials, private keys, certificates, and sensitive connection strings were not read or printed.")
    print("The Terraform CLI was not invoked. No init, plan, show, state, import, apply, destroy, refresh, or provider live call was performed.")
    print("No repository or infrastructure mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
