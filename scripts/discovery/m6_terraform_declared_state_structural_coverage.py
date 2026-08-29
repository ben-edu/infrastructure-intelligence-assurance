from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def _load_module(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DECLARED = _load_module(
    "m6_terraform_declared_resource_location_probe.py",
    "m6_terraform_declared_resource_location_probe",
)
STATE = _load_module(
    "m6_terraform_local_state_structure.py",
    "m6_terraform_local_state_structure",
)

ROOT_DIRECTORIES = {
    "bm1": "terraform/environments/bm1",
    "bm2": "terraform/environments/bm2",
}


def _safe_type_counts(values: Any) -> dict[str, int] | None:
    if not isinstance(values, dict):
        return None
    safe: dict[str, int] = {}
    for raw_type, raw_count in values.items():
        if not isinstance(raw_count, int) or isinstance(raw_count, bool) or raw_count < 0:
            return None
        projected = STATE._project_type(raw_type)
        safe[projected] = safe.get(projected, 0) + raw_count
    return dict(sorted(safe.items()))


def _state_root_map(state_result: dict[str, Any]) -> dict[str, dict[str, Any]] | None:
    raw = state_result.get("root_results")
    if not isinstance(raw, list):
        return None
    mapped: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            return None
        name = item.get("root")
        if not isinstance(name, str) or name not in ROOT_DIRECTORIES or name in mapped:
            return None
        mapped[name] = item
    return mapped


def _empty_root(root_name: str, status: str) -> dict[str, Any]:
    return {
        "root": root_name,
        "comparison_status": status,
        "declared_resource_blocks": 0,
        "state_managed_resource_blocks": 0,
        "declared_resource_type_counts": {},
        "state_managed_resource_type_counts": {},
        "matched_resource_type_block_count": 0,
    }


def discover(repo: Path = DECLARED.SOURCE_REPO) -> dict[str, Any]:
    declared_result = DECLARED.discover_resource_locations(repo)
    state_roots = {
        name: repo / "terraform" / "environments" / name
        for name in ROOT_DIRECTORIES
    }
    state_result = STATE.discover(state_roots)

    result: dict[str, Any] = {
        "source_mode": "DECLARED_GIT_TF_TO_LOCAL_STATE_SAFE_TYPE_COUNT_RELATIONSHIP",
        "source_status": "INCOMPLETE",
        "declared_source_status": declared_result.get("source_status", "FAILED_TO_OBSERVE"),
        "state_source_status": state_result.get("source_status", "FAILED_TO_OBSERVE"),
        "roots_expected": len(ROOT_DIRECTORIES),
        "roots_compared_complete": 0,
        "root_results": [],
        "declared_resource_blocks": 0,
        "state_managed_resource_blocks": 0,
        "matched_resource_type_block_count": 0,
        "declared_to_local_state_structural_coverage_status": "SOURCE_INCOMPLETE",
        "state_backed_coverage_status": "UNKNOWN",
        "live_resource_coverage_status": "UNKNOWN",
        "plan_result_status": "UNKNOWN",
        "apply_result_status": "UNKNOWN",
        "drift_status": "UNKNOWN",
        "destructive_change_status": "UNKNOWN",
        "drift_claims": 0,
        "destructive_change_claims": 0,
    }

    if declared_result.get("source_status") != "COMPLETE":
        return result
    if state_result.get("source_status") != "COMPLETE":
        return result

    directories = declared_result.get("directories")
    state_map = _state_root_map(state_result)
    if not isinstance(directories, dict) or state_map is None:
        return result

    root_rows: list[dict[str, Any]] = []
    for root_name, directory in ROOT_DIRECTORIES.items():
        declared_row = directories.get(directory)
        state_row = state_map.get(root_name)
        if not isinstance(declared_row, dict) or not isinstance(state_row, dict):
            root_rows.append(_empty_root(root_name, "SOURCE_INCOMPLETE"))
            continue
        if state_row.get("parse_status") != "COMPLETE":
            root_rows.append(_empty_root(root_name, "SOURCE_INCOMPLETE"))
            continue

        declared_counts = _safe_type_counts(declared_row.get("resource_types"))
        state_counts = _safe_type_counts(state_row.get("managed_resource_type_counts"))
        if declared_counts is None or state_counts is None:
            root_rows.append(_empty_root(root_name, "SOURCE_INCOMPLETE"))
            continue

        declared_blocks = sum(declared_counts.values())
        state_blocks = sum(state_counts.values())
        matched_blocks = sum(
            min(declared_counts.get(resource_type, 0), state_counts.get(resource_type, 0))
            for resource_type in set(declared_counts) | set(state_counts)
        )
        comparison = (
            "DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH"
            if declared_counts == state_counts
            else "DECLARED_TO_LOCAL_STATE_STRUCTURAL_MISMATCH"
        )
        root_rows.append(
            {
                "root": root_name,
                "comparison_status": comparison,
                "declared_resource_blocks": declared_blocks,
                "state_managed_resource_blocks": state_blocks,
                "declared_resource_type_counts": declared_counts,
                "state_managed_resource_type_counts": state_counts,
                "matched_resource_type_block_count": matched_blocks,
            }
        )

    result["root_results"] = root_rows
    complete_rows = [row for row in root_rows if row["comparison_status"] != "SOURCE_INCOMPLETE"]
    result["roots_compared_complete"] = len(complete_rows)
    if len(complete_rows) != len(ROOT_DIRECTORIES):
        return result

    result["source_status"] = "COMPLETE"
    result["declared_resource_blocks"] = sum(row["declared_resource_blocks"] for row in root_rows)
    result["state_managed_resource_blocks"] = sum(row["state_managed_resource_blocks"] for row in root_rows)
    result["matched_resource_type_block_count"] = sum(
        row["matched_resource_type_block_count"] for row in root_rows
    )
    if all(
        row["comparison_status"] == "DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH"
        for row in root_rows
    ):
        result["declared_to_local_state_structural_coverage_status"] = (
            "DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH"
        )
    else:
        result["declared_to_local_state_structural_coverage_status"] = (
            "DECLARED_TO_LOCAL_STATE_STRUCTURAL_MISMATCH"
        )
    return result


def _format_counts(values: dict[str, int]) -> str:
    if not values:
        return "NONE_OBSERVED"
    return ",".join(f"{key}={values[key]}" for key in sorted(values))


def main() -> int:
    result = discover()

    print("===== M6 TERRAFORM DECLARED-TO-LOCAL-STATE STRUCTURAL COVERAGE =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("terraform_cli_invoked: False")
    print("provider_api_invoked: False")
    print("raw_hcl_projected: False")
    print("raw_state_projected: False")
    print("resource_names_or_addresses_projected: False")
    print("instance_identity_projected: False")
    print("state_values_projected: False")
    print("tfvars_inspected: False")

    print()
    print("===== RELATIONSHIP SOURCE =====")
    print("source_mode:", result["source_mode"])
    print("source_status:", result["source_status"])
    print("declared_source_status:", result["declared_source_status"])
    print("state_source_status:", result["state_source_status"])
    print("roots_expected:", result["roots_expected"])
    print("roots_compared_complete:", result["roots_compared_complete"])
    for row in result["root_results"]:
        print(
            f"root={row['root']} comparison_status={row['comparison_status']} "
            f"declared_resource_blocks={row['declared_resource_blocks']} "
            f"state_managed_resource_blocks={row['state_managed_resource_blocks']} "
            f"declared_resource_type_counts={_format_counts(row['declared_resource_type_counts'])} "
            f"state_managed_resource_type_counts={_format_counts(row['state_managed_resource_type_counts'])} "
            f"matched_resource_type_block_count={row['matched_resource_type_block_count']}"
        )

    print()
    print("===== AGGREGATE STRUCTURAL RELATIONSHIP =====")
    print("declared_resource_blocks:", result["declared_resource_blocks"])
    print("state_managed_resource_blocks:", result["state_managed_resource_blocks"])
    print("matched_resource_type_block_count:", result["matched_resource_type_block_count"])
    print(
        "declared_to_local_state_structural_coverage_status:",
        result["declared_to_local_state_structural_coverage_status"],
    )

    print()
    print("===== COVERAGE / OUTCOME BOUNDARY =====")
    print("state_backed_coverage_status: UNKNOWN")
    print("live_resource_coverage_status: UNKNOWN")
    print("plan_result_status: UNKNOWN")
    print("apply_result_status: UNKNOWN")
    print("drift_status: UNKNOWN")
    print("destructive_change_status: UNKNOWN")
    print("drift_claims: 0")
    print("destructive_change_claims: 0")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("This relationship compares declared resource-type block counts with local-state managed resource-type block counts only.")
    print("A structural match is limited declared-to-local-state evidence; it does not prove state freshness, authoritative ownership, instance identity, or live resource existence.")
    print("A structural mismatch is not a drift finding; drift requires separate authoritative live/runtime verification.")
    print("Managed state instance counts are intentionally not compared with declared resource-block counts.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only aggregate declared resource-type block counts and aggregate local-state managed resource-type block counts are projected.")
    print("Raw HCL/state, resource names/addresses, instance keys, state values, outputs, serial/lineage, provider configuration, tfvars, endpoints, credentials, and sensitive connection strings are not printed or persisted.")
    print("No Terraform CLI, provider API, SSH connection, repository mutation, or infrastructure mutation was performed.")

    return 0 if result["source_status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
