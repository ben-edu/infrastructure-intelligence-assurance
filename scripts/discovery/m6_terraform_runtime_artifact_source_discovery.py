from __future__ import annotations

from pathlib import Path
from typing import Any

INFRA_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
ROOTS = {
    "bm1": INFRA_REPO / "terraform" / "environments" / "bm1",
    "bm2": INFRA_REPO / "terraform" / "environments" / "bm2",
}


def _safe_kind(path: Path) -> tuple[str, bool]:
    """Return metadata-only kind and whether observation failed.

    File contents are never opened. Symlinks are intentionally not followed.
    """
    try:
        if path.is_symlink():
            return "SYMLINK", False
        if path.is_dir():
            return "DIRECTORY", False
        if path.is_file():
            return "FILE", False
        if path.exists():
            return "OTHER", False
        return "MISSING", False
    except OSError:
        return "FAILED", True


def _count_workspace_entries(path: Path) -> tuple[int, int, int]:
    """Count immediate workspace directories without exposing names.

    Returns (workspace_directories, symlink_entries, metadata_failures).
    """
    workspace_directories = 0
    symlink_entries = 0
    failures = 0
    try:
        entries = list(path.iterdir())
    except OSError:
        return 0, 0, 1

    for entry in entries:
        try:
            if entry.is_symlink():
                symlink_entries += 1
            elif entry.is_dir():
                workspace_directories += 1
        except OSError:
            failures += 1
    return workspace_directories, symlink_entries, failures


def _count_saved_plan_candidates(root: Path) -> tuple[int, int, int]:
    """Count narrowly named top-level saved-plan candidates by metadata only."""
    count = 0
    symlink_entries = 0
    failures = 0
    try:
        entries = list(root.iterdir())
    except OSError:
        return 0, 0, 1

    for entry in entries:
        lowered = entry.name.lower()
        if not (lowered == "tfplan" or lowered.endswith(".tfplan")):
            continue
        try:
            if entry.is_symlink():
                symlink_entries += 1
            elif entry.is_file():
                count += 1
        except OSError:
            failures += 1
    return count, symlink_entries, failures


def inspect_root(alias: str, root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "alias": alias,
        "root_status": "UNKNOWN",
        "working_directory_observed": False,
        "top_level_state_artifact_observed": False,
        "top_level_state_backup_artifact_observed": False,
        "workspace_state_directory_observed": False,
        "workspace_directories_observed": 0,
        "backend_metadata_candidate_observed": False,
        "workspace_selection_metadata_candidate_observed": False,
        "saved_plan_artifact_candidates_observed": 0,
        "symlink_entries_skipped": 0,
        "metadata_failures": 0,
    }

    root_kind, failed = _safe_kind(root)
    if failed:
        result["root_status"] = "FAILED_TO_OBSERVE"
        result["metadata_failures"] += 1
        return result
    if root_kind != "DIRECTORY":
        result["root_status"] = "MISSING_OR_UNSAFE"
        if root_kind == "SYMLINK":
            result["symlink_entries_skipped"] += 1
        return result
    result["root_status"] = "OBSERVED"

    generic_targets = {
        "working_directory_observed": root / ".terraform",
        "top_level_state_artifact_observed": root / "terraform.tfstate",
        "top_level_state_backup_artifact_observed": root / "terraform.tfstate.backup",
        "workspace_state_directory_observed": root / "terraform.tfstate.d",
        "backend_metadata_candidate_observed": root / ".terraform" / "terraform.tfstate",
        "workspace_selection_metadata_candidate_observed": root / ".terraform" / "environment",
    }

    expected_kind = {
        "working_directory_observed": "DIRECTORY",
        "top_level_state_artifact_observed": "FILE",
        "top_level_state_backup_artifact_observed": "FILE",
        "workspace_state_directory_observed": "DIRECTORY",
        "backend_metadata_candidate_observed": "FILE",
        "workspace_selection_metadata_candidate_observed": "FILE",
    }

    for key, path in generic_targets.items():
        kind, target_failed = _safe_kind(path)
        if target_failed:
            result["metadata_failures"] += 1
            continue
        if kind == "SYMLINK":
            result["symlink_entries_skipped"] += 1
            continue
        result[key] = kind == expected_kind[key]

    workspace_dir = root / "terraform.tfstate.d"
    if result["workspace_state_directory_observed"]:
        directories, symlinks, failures = _count_workspace_entries(workspace_dir)
        result["workspace_directories_observed"] = directories
        result["symlink_entries_skipped"] += symlinks
        result["metadata_failures"] += failures

    plans, symlinks, failures = _count_saved_plan_candidates(root)
    result["saved_plan_artifact_candidates_observed"] = plans
    result["symlink_entries_skipped"] += symlinks
    result["metadata_failures"] += failures
    return result


def discover(roots: dict[str, Path] = ROOTS) -> dict[str, Any]:
    root_results = [inspect_root(alias, path) for alias, path in roots.items()]

    roots_observed = sum(item["root_status"] == "OBSERVED" for item in root_results)
    metadata_failures = sum(item["metadata_failures"] for item in root_results)
    symlink_entries_skipped = sum(item["symlink_entries_skipped"] for item in root_results)
    incomplete = (
        roots_observed != len(root_results)
        or metadata_failures > 0
        or symlink_entries_skipped > 0
    )

    totals = {
        "working_directories_observed": sum(item["working_directory_observed"] for item in root_results),
        "top_level_state_artifacts_observed": sum(item["top_level_state_artifact_observed"] for item in root_results),
        "top_level_state_backup_artifacts_observed": sum(item["top_level_state_backup_artifact_observed"] for item in root_results),
        "workspace_state_directories_observed": sum(item["workspace_state_directory_observed"] for item in root_results),
        "workspace_directories_observed": sum(item["workspace_directories_observed"] for item in root_results),
        "backend_metadata_candidates_observed": sum(item["backend_metadata_candidate_observed"] for item in root_results),
        "workspace_selection_metadata_candidates_observed": sum(item["workspace_selection_metadata_candidate_observed"] for item in root_results),
        "saved_plan_artifact_candidates_observed": sum(item["saved_plan_artifact_candidates_observed"] for item in root_results),
    }
    artifact_count = sum(totals.values())

    if incomplete:
        source_status = "INCOMPLETE"
        runtime_artifact_source_status = "SOURCE_INCOMPLETE"
    elif artifact_count:
        source_status = "COMPLETE"
        runtime_artifact_source_status = "RUNTIME_ARTIFACT_METADATA_OBSERVED"
    else:
        source_status = "COMPLETE"
        runtime_artifact_source_status = "NONE_OBSERVED_IN_BOUNDED_ROOTS"

    return {
        "source_mode": "BOUNDED_TERRAFORM_ROOT_FILESYSTEM_METADATA_ONLY",
        "source_status": source_status,
        "runtime_artifact_source_status": runtime_artifact_source_status,
        "root_directories_expected": len(root_results),
        "root_directories_observed": roots_observed,
        "metadata_failures": metadata_failures,
        "symlink_entries_skipped": symlink_entries_skipped,
        "roots": root_results,
        **totals,
        "terraform_cli_invoked": False,
        "terraform_state_contents_inspected": False,
        "terraform_plan_contents_inspected": False,
        "terraform_tfvars_contents_inspected": False,
        "provider_api_invoked": False,
        "state_backed_coverage_status": "UNKNOWN",
        "live_resource_coverage_status": "UNKNOWN",
        "plan_result_status": "UNKNOWN",
        "apply_result_status": "UNKNOWN",
        "drift_status": "UNKNOWN",
        "destructive_change_status": "UNKNOWN",
        "state_backed_coverage_claims": 0,
        "drift_claims": 0,
        "destructive_change_claims": 0,
    }


def _bool_status(value: bool) -> str:
    return "OBSERVED" if value else "NONE_OBSERVED"


def main() -> int:
    result = discover()

    print("===== M6 TERRAFORM RUNTIME-ARTIFACT SOURCE DISCOVERY =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("terraform_cli_invoked: False")
    print("terraform_state_contents_inspected: False")
    print("terraform_plan_contents_inspected: False")
    print("terraform_tfvars_contents_inspected: False")
    print("provider_api_invoked: False")

    print()
    print("===== BOUNDED ROOT METADATA =====")
    print("source_mode:", result["source_mode"])
    print("source_status:", result["source_status"])
    print("root_directories_expected:", result["root_directories_expected"])
    print("root_directories_observed:", result["root_directories_observed"])
    print("metadata_failures:", result["metadata_failures"])
    print("symlink_entries_skipped:", result["symlink_entries_skipped"])
    for item in result["roots"]:
        print(
            "root=" + item["alias"],
            "root_status=" + item["root_status"],
            "working_directory=" + _bool_status(item["working_directory_observed"]),
            "state_artifact=" + _bool_status(item["top_level_state_artifact_observed"]),
            "state_backup_artifact=" + _bool_status(item["top_level_state_backup_artifact_observed"]),
            "workspace_state_directory=" + _bool_status(item["workspace_state_directory_observed"]),
            "workspace_directories=" + str(item["workspace_directories_observed"]),
            "backend_metadata_candidate=" + _bool_status(item["backend_metadata_candidate_observed"]),
            "workspace_selection_metadata_candidate=" + _bool_status(item["workspace_selection_metadata_candidate_observed"]),
            "saved_plan_candidates=" + str(item["saved_plan_artifact_candidates_observed"]),
        )

    print()
    print("===== AGGREGATE RUNTIME-ARTIFACT METADATA =====")
    for key in (
        "working_directories_observed",
        "top_level_state_artifacts_observed",
        "top_level_state_backup_artifacts_observed",
        "workspace_state_directories_observed",
        "workspace_directories_observed",
        "backend_metadata_candidates_observed",
        "workspace_selection_metadata_candidates_observed",
        "saved_plan_artifact_candidates_observed",
        "runtime_artifact_source_status",
    ):
        print(f"{key}: {result[key]}")

    print()
    print("===== TRUST / OUTCOME BOUNDARY =====")
    print("state_backed_coverage_status: UNKNOWN")
    print("live_resource_coverage_status: UNKNOWN")
    print("plan_result_status: UNKNOWN")
    print("apply_result_status: UNKNOWN")
    print("drift_status: UNKNOWN")
    print("destructive_change_status: UNKNOWN")
    print("state_backed_coverage_claims: 0")
    print("drift_claims: 0")
    print("destructive_change_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("Filesystem artifact metadata is source-capability evidence only; it is not Terraform state-backed coverage, current state, plan/apply outcome, drift, or destructive-change evidence.")
    print("A detected state-like or backend-metadata artifact is not read and does not prove that the state is current, complete, authoritative, or safe to use.")
    print("A missing artifact in a COMPLETE bounded root scan is bounded metadata absence only; it does not rule out remote state, another checkout, CI artifacts, or external execution sources.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only filesystem metadata for two previously accepted Terraform root candidates and generic Terraform runtime-artifact names was inspected.")
    print("Terraform state, state backups, backend metadata, workspace metadata, saved plans, tfvars, credentials, provider configuration values, and resource addresses were not opened or projected.")
    print("Artifact-specific filenames beyond generic Terraform conventions, workspace names, endpoint values, credentials, commands, and sensitive connection strings were not printed or persisted.")
    print("No Terraform CLI, provider API, SSH connection, repository mutation, or infrastructure mutation was performed.")

    if result["source_status"] != "COMPLETE":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
