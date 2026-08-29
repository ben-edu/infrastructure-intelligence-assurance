from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

INFRA_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
ROOTS = {
    "bm1": INFRA_REPO / "terraform" / "environments" / "bm1",
    "bm2": INFRA_REPO / "terraform" / "environments" / "bm2",
}
STATE_BASENAME = "terraform.tfstate"
MAX_STATE_BYTES = 16 * 1024 * 1024
SAFE_TYPE_RE = re.compile(r"^[A-Za-z0-9_]{1,128}$")
SENSITIVE_TYPE_TOKENS = ("secret", "credential", "password", "token", "private", "certificate")


def _project_type(value: Any) -> str:
    if not isinstance(value, str) or not SAFE_TYPE_RE.fullmatch(value):
        return "UNCLASSIFIED_TYPE"
    lowered = value.lower()
    if any(token in lowered for token in SENSITIVE_TYPE_TOKENS):
        return "REDACTED_TYPE_CATEGORY"
    return value


def _empty_root(root_name: str, status: str) -> dict[str, Any]:
    return {
        "root": root_name,
        "parse_status": status,
        "managed_resource_blocks": 0,
        "data_resource_blocks": 0,
        "other_resource_blocks": 0,
        "managed_instances": 0,
        "data_instances": 0,
        "other_instances": 0,
        "managed_resource_type_counts": {},
    }


def _parse_state(root_name: str, state_path: Path) -> dict[str, Any]:
    try:
        if state_path.is_symlink():
            return _empty_root(root_name, "SYMLINK_REJECTED")
        stat = state_path.stat()
    except FileNotFoundError:
        return _empty_root(root_name, "STATE_NOT_FOUND")
    except OSError:
        return _empty_root(root_name, "METADATA_FAILED")

    if not state_path.is_file():
        return _empty_root(root_name, "NOT_REGULAR_FILE")
    if stat.st_size > MAX_STATE_BYTES:
        return _empty_root(root_name, "STATE_TOO_LARGE")

    try:
        with state_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except UnicodeError:
        return _empty_root(root_name, "DECODE_FAILED")
    except json.JSONDecodeError:
        return _empty_root(root_name, "INVALID_JSON")
    except OSError:
        return _empty_root(root_name, "READ_FAILED")

    if not isinstance(payload, dict):
        return _empty_root(root_name, "INVALID_TOP_LEVEL_SHAPE")
    resources = payload.get("resources")
    if not isinstance(resources, list):
        return _empty_root(root_name, "UNSUPPORTED_STATE_SHAPE")

    result = _empty_root(root_name, "COMPLETE")
    managed_types: Counter[str] = Counter()

    for resource in resources:
        if not isinstance(resource, dict):
            return _empty_root(root_name, "INVALID_RESOURCE_SHAPE")
        mode = resource.get("mode")
        instances = resource.get("instances", [])
        if not isinstance(instances, list):
            return _empty_root(root_name, "INVALID_INSTANCE_SHAPE")
        instance_count = len(instances)

        if mode == "managed":
            result["managed_resource_blocks"] += 1
            result["managed_instances"] += instance_count
            managed_types[_project_type(resource.get("type"))] += 1
        elif mode == "data":
            result["data_resource_blocks"] += 1
            result["data_instances"] += instance_count
        else:
            result["other_resource_blocks"] += 1
            result["other_instances"] += instance_count

    result["managed_resource_type_counts"] = dict(sorted(managed_types.items()))
    return result


def discover(roots: dict[str, Path] = ROOTS) -> dict[str, Any]:
    root_results = [_parse_state(name, root / STATE_BASENAME) for name, root in roots.items()]
    complete = all(item["parse_status"] == "COMPLETE" for item in root_results)

    managed_types: Counter[str] = Counter()
    for item in root_results:
        managed_types.update(item["managed_resource_type_counts"])

    result: dict[str, Any] = {
        "source_mode": "LOCAL_TERRAFORM_STATE_PROCESS_LOCAL_SAFE_STRUCTURE_ONLY",
        "source_status": "COMPLETE" if complete else "INCOMPLETE",
        "roots_expected": len(roots),
        "roots_parsed_complete": sum(item["parse_status"] == "COMPLETE" for item in root_results),
        "root_results": root_results,
        "managed_resource_blocks": sum(item["managed_resource_blocks"] for item in root_results),
        "data_resource_blocks": sum(item["data_resource_blocks"] for item in root_results),
        "other_resource_blocks": sum(item["other_resource_blocks"] for item in root_results),
        "managed_instances": sum(item["managed_instances"] for item in root_results),
        "data_instances": sum(item["data_instances"] for item in root_results),
        "other_instances": sum(item["other_instances"] for item in root_results),
        "managed_resource_type_counts": dict(sorted(managed_types.items())),
        "state_structure_status": (
            "STRUCTURAL_AGGREGATE_OBSERVED"
            if complete
            else "STATE_STRUCTURE_INCOMPLETE"
        ),
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
    return result


def _format_counts(values: dict[str, int]) -> str:
    if not values:
        return "NONE_OBSERVED"
    return ",".join(f"{key}={values[key]}" for key in sorted(values))


def main() -> int:
    result = discover()

    print("===== M6 TERRAFORM LOCAL-STATE SAFE STRUCTURAL AGGREGATION =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("terraform_cli_invoked: False")
    print("provider_api_invoked: False")
    print("raw_state_projected: False")
    print("state_values_projected: False")
    print("resource_addresses_projected: False")
    print("resource_names_projected: False")
    print("instance_keys_projected: False")
    print("outputs_projected: False")
    print("serial_or_lineage_projected: False")
    print("provider_configuration_projected: False")

    print()
    print("===== LOCAL STATE STRUCTURE =====")
    print("source_mode:", result["source_mode"])
    print("source_status:", result["source_status"])
    print("roots_expected:", result["roots_expected"])
    print("roots_parsed_complete:", result["roots_parsed_complete"])
    for item in result["root_results"]:
        print(
            f"root={item['root']} parse_status={item['parse_status']} "
            f"managed_resource_blocks={item['managed_resource_blocks']} "
            f"data_resource_blocks={item['data_resource_blocks']} "
            f"managed_instances={item['managed_instances']} "
            f"data_instances={item['data_instances']}"
        )

    print()
    print("===== AGGREGATE SAFE STRUCTURE =====")
    print("managed_resource_blocks:", result["managed_resource_blocks"])
    print("data_resource_blocks:", result["data_resource_blocks"])
    print("other_resource_blocks:", result["other_resource_blocks"])
    print("managed_instances:", result["managed_instances"])
    print("data_instances:", result["data_instances"])
    print("other_instances:", result["other_instances"])
    print("managed_resource_type_counts:", _format_counts(result["managed_resource_type_counts"]))
    print("state_structure_status:", result["state_structure_status"])

    print()
    print("===== COVERAGE / OUTCOME BOUNDARY =====")
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
    print("A successfully parsed local state structure is local state evidence only; it is not proof that state is current, authoritative, complete, or aligned with live infrastructure.")
    print("Managed resource and instance counts are structural aggregates only and must not be promoted to declared-to-state coverage or live-resource coverage without a separate relationship check.")
    print("No plan/apply success, drift, destructive-change, or provider reachability result is inferred from local state structure.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Terraform state is parsed only inside the local process to compute explicitly allowlisted aggregate structure.")
    print("Resource attribute values, resource names/addresses, instance keys, outputs, serial/lineage identifiers, provider configuration strings, endpoints, credentials, and raw state are never printed or persisted.")
    print("Sensitive-looking resource-type categories are redacted before projection.")
    print("No Terraform CLI, provider API, SSH connection, repository mutation, or infrastructure mutation was performed.")

    return 0 if result["source_status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
