from __future__ import annotations

import importlib.util
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath

SCRIPT = Path(__file__).resolve().with_name("m6_terraform_root_module_coverage.py")
SPEC = importlib.util.spec_from_file_location("m6_root_module_coverage", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load bounded root-module discovery module")
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

SOURCE_REPO = BASE.SOURCE_REPO


def discover_resource_locations(repo: Path = SOURCE_REPO) -> dict[str, object]:
    source_status, raw_paths = BASE._run_git_ls_files(repo)
    result: dict[str, object] = {
        "source_status": source_status,
        "tracked_tf_files_returned": len(raw_paths),
        "tracked_tf_files_scanned": 0,
        "read_or_decode_skips": 0,
        "oversize_skips": 0,
        "directories": {},
    }
    if source_status != "COMPLETE":
        return result

    resources_by_directory: dict[str, Counter[str]] = defaultdict(Counter)
    files_by_directory: dict[str, int] = defaultdict(int)

    for raw_path in raw_paths:
        safe_path = BASE._safe_relative_tf_path(raw_path)
        if safe_path is None:
            continue
        path = repo / safe_path
        try:
            size = path.stat().st_size
        except OSError:
            result["read_or_decode_skips"] = int(result["read_or_decode_skips"]) + 1
            continue
        if size > BASE.MAX_FILE_BYTES:
            result["oversize_skips"] = int(result["oversize_skips"]) + 1
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            result["read_or_decode_skips"] = int(result["read_or_decode_skips"]) + 1
            continue

        parent = PurePosixPath(safe_path).parent
        directory = "." if str(parent) == "." else parent.as_posix()
        files_by_directory[directory] += 1
        resources_by_directory[directory].update(BASE._resource_types(text))
        result["tracked_tf_files_scanned"] = int(result["tracked_tf_files_scanned"]) + 1

    if result["read_or_decode_skips"] or result["oversize_skips"]:
        result["source_status"] = "INCOMPLETE"

    result["directories"] = {
        directory: {
            "classification": BASE._directory_classification(directory),
            "tf_file_count": files_by_directory[directory],
            "resource_types": dict(sorted(resources_by_directory[directory].items())),
        }
        for directory in sorted(files_by_directory)
    }
    return result


def _format_types(values: dict[str, int]) -> str:
    if not values:
        return "NONE_OBSERVED"
    return ",".join(f"{key}={values[key]}" for key in sorted(values))


def main() -> int:
    print("===== M6 TERRAFORM DECLARED RESOURCE LOCATION PROBE =====")
    print()
    print("===== DECLARED-STATE SOURCE =====")
    print("repository_alias: afpa-infra-rebuild")
    print("source_mode: GIT_TRACKED_TF_ONLY")
    print("mutation_allowed: False")
    print("terraform_state_inspected: False")
    print("terraform_tfvars_inspected: False")
    print("terraform_cli_invoked: False")
    print("provider_live_verification_performed: False")

    result = discover_resource_locations()
    print("source_status:", result["source_status"])
    print("tracked_tf_files_returned:", result["tracked_tf_files_returned"])
    print("tracked_tf_files_scanned:", result["tracked_tf_files_scanned"])
    print("read_or_decode_skips:", result["read_or_decode_skips"])
    print("oversize_skips:", result["oversize_skips"])

    if result["source_status"] != "COMPLETE":
        print("resource_location_status: FAILED_TO_OBSERVE")
        print("No declared-resource location conclusion is allowed.")
        print("No mutation was performed.")
        return 2

    print()
    print("===== RESOURCE TYPES BY TERRAFORM DIRECTORY =====")
    total_resource_blocks = 0
    directories_with_resources = 0
    for directory, row in result["directories"].items():
        resource_types = row["resource_types"]
        block_count = sum(resource_types.values())
        total_resource_blocks += block_count
        if block_count:
            directories_with_resources += 1
        print(
            f"directory={directory}"
            f" classification={row['classification']}"
            f" tf_files={row['tf_file_count']}"
            f" declared_resource_types={_format_types(resource_types)}"
        )

    print()
    print("===== SUMMARY =====")
    print("terraform_directories_total:", len(result["directories"]))
    print("directories_with_declared_resources:", directories_with_resources)
    print("declared_resource_blocks_total:", total_resource_blocks)
    print("live_resource_coverage_status: UNKNOWN")
    print("state_backed_coverage_status: UNKNOWN")
    print("drift_claims: 0")
    print("destructive_change_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("This probe only locates declared resource types by Git-tracked Terraform directory.")
    print("A resource block in a root directory is direct declared configuration; a resource block in a module directory is module-declared configuration.")
    print("Neither establishes Terraform state membership, live infrastructure existence, runtime instance count, provider reachability, or drift status.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only Git-tracked .tf files from the bounded infrastructure repository were read.")
    print("Raw HCL lines, resource instance names, module names/source values, variable values, provider/backend values, and sensitive connection strings were not printed.")
    print("Terraform state/state backups, real tfvars, .env files, secrets, credentials, private keys, certificates, and provider tokens/passwords were not read or printed.")
    print("Terraform CLI and provider live APIs were not invoked. No infrastructure or repository mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
