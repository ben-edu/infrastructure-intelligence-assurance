from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

INFRA_REPO = Path("/home/ben/projects/afpa-infra-rebuild")
ROOTS = {
    "bm1": INFRA_REPO / "terraform" / "environments" / "bm1",
    "bm2": INFRA_REPO / "terraform" / "environments" / "bm2",
}
TIMEOUT_SECONDS = 90
ALLOWED_ACTIONS = {
    "create",
    "update",
    "delete",
    "replace",
    "read",
    "no-op",
    "noop",
    "move",
    "import",
    "forget",
}


def _command(mode: str) -> list[str]:
    base = [
        "terraform",
        "plan",
        "-input=false",
        "-lock=false",
        "-detailed-exitcode",
        "-json",
    ]
    if mode == "configuration_vs_state":
        return [*base, "-refresh=false"]
    if mode == "refresh_only":
        return [*base, "-refresh-only"]
    raise ValueError(f"unsupported mode: {mode}")


def _empty_mode(mode: str, status: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "observation_status": status,
        "terraform_exit_code": None,
        "json_lines": 0,
        "malformed_json_lines": 0,
        "planned_change_events": 0,
        "recognized_action_events": 0,
        "action_counts": {},
        "change_signal": "UNKNOWN",
    }


def _normalize_action(value: Any) -> str | None:
    if isinstance(value, str):
        action = value.strip().lower()
        return action if action in ALLOWED_ACTIONS else None
    if isinstance(value, list):
        normalized = [str(item).strip().lower() for item in value if isinstance(item, str)]
        values = set(normalized)
        if values == {"delete", "create"}:
            return "replace"
        if len(normalized) == 1 and normalized[0] in ALLOWED_ACTIONS:
            return normalized[0]
    return None


def _parse_json_stream(stdout: bytes) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    json_lines = 0
    malformed = 0
    planned_events = 0
    recognized_events = 0

    for raw_line in stdout.splitlines():
        if not raw_line.strip():
            continue
        try:
            line = raw_line.decode("utf-8")
            event = json.loads(line)
        except (UnicodeError, json.JSONDecodeError):
            malformed += 1
            continue
        if not isinstance(event, dict):
            malformed += 1
            continue
        json_lines += 1
        if event.get("type") != "planned_change":
            continue
        planned_events += 1
        change = event.get("change")
        if not isinstance(change, dict):
            continue
        action = _normalize_action(change.get("action"))
        if action is None:
            continue
        counts[action] += 1
        recognized_events += 1

    return {
        "json_lines": json_lines,
        "malformed_json_lines": malformed,
        "planned_change_events": planned_events,
        "recognized_action_events": recognized_events,
        "action_counts": dict(sorted(counts.items())),
    }


def _run_plan(root: Path, mode: str) -> dict[str, Any]:
    result = _empty_mode(mode, "NOT_ATTEMPTED")
    if shutil.which("terraform") is None:
        result["observation_status"] = "TERRAFORM_CLI_UNAVAILABLE"
        return result
    try:
        if root.is_symlink() or not root.is_dir():
            result["observation_status"] = "ROOT_UNAVAILABLE"
            return result
    except OSError:
        result["observation_status"] = "ROOT_METADATA_FAILED"
        return result

    env = os.environ.copy()
    env["TF_IN_AUTOMATION"] = "1"
    env["CHECKPOINT_DISABLE"] = "1"

    try:
        completed = subprocess.run(
            _command(mode),
            cwd=root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        result["observation_status"] = "TIMEOUT"
        return result
    except OSError:
        result["observation_status"] = "EXECUTION_FAILED"
        return result

    parsed = _parse_json_stream(completed.stdout)
    result.update(parsed)
    result["terraform_exit_code"] = completed.returncode

    if parsed["malformed_json_lines"]:
        result["observation_status"] = "INVALID_JSON_STREAM"
        return result

    if completed.returncode == 0:
        result["observation_status"] = "COMPLETE_NO_CHANGES"
        result["change_signal"] = "NONE_OBSERVED"
        return result

    if completed.returncode == 2:
        if parsed["recognized_action_events"]:
            result["observation_status"] = "COMPLETE_CHANGES_OBSERVED"
        else:
            result["observation_status"] = "COMPLETE_CHANGES_UNCLASSIFIED"
        result["change_signal"] = "CHANGES_OBSERVED"
        return result

    result["observation_status"] = "FAILED_TO_OBSERVE"
    return result


def _destructive_status(mode_result: dict[str, Any]) -> str:
    status = mode_result["observation_status"]
    if status == "COMPLETE_NO_CHANGES":
        return "NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN"
    if status != "COMPLETE_CHANGES_OBSERVED":
        return "UNKNOWN"
    counts = mode_result["action_counts"]
    destructive = int(counts.get("delete", 0)) + int(counts.get("replace", 0))
    return (
        "DESTRUCTIVE_ACTIONS_OBSERVED"
        if destructive
        else "NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN"
    )


def _drift_signal_status(mode_result: dict[str, Any]) -> str:
    status = mode_result["observation_status"]
    if status == "COMPLETE_NO_CHANGES":
        return "NONE_OBSERVED_IN_COMPLETE_REFRESH_ONLY_PLAN"
    if status in {"COMPLETE_CHANGES_OBSERVED", "COMPLETE_CHANGES_UNCLASSIFIED"}:
        return "STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED"
    return "UNKNOWN"


def discover(roots: dict[str, Path] = ROOTS) -> dict[str, Any]:
    root_results: list[dict[str, Any]] = []
    aggregate_configuration: Counter[str] = Counter()
    aggregate_refresh: Counter[str] = Counter()

    for root_name, root_path in roots.items():
        configuration = _run_plan(root_path, "configuration_vs_state")
        refresh_only = _run_plan(root_path, "refresh_only")
        aggregate_configuration.update(configuration["action_counts"])
        aggregate_refresh.update(refresh_only["action_counts"])
        root_results.append(
            {
                "root": root_name,
                "configuration_vs_state": configuration,
                "refresh_only": refresh_only,
                "destructive_change_status": _destructive_status(configuration),
                "state_tracked_drift_signal_status": _drift_signal_status(refresh_only),
            }
        )

    complete_statuses = {
        "COMPLETE_NO_CHANGES",
        "COMPLETE_CHANGES_OBSERVED",
        "COMPLETE_CHANGES_UNCLASSIFIED",
    }
    all_configuration_complete = all(
        row["configuration_vs_state"]["observation_status"] in complete_statuses
        for row in root_results
    )
    all_refresh_complete = all(
        row["refresh_only"]["observation_status"] in complete_statuses
        for row in root_results
    )

    destructive_statuses = {row["destructive_change_status"] for row in root_results}
    if "DESTRUCTIVE_ACTIONS_OBSERVED" in destructive_statuses:
        aggregate_destructive = "DESTRUCTIVE_ACTIONS_OBSERVED"
    elif all_configuration_complete and destructive_statuses == {"NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN"}:
        aggregate_destructive = "NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN"
    else:
        aggregate_destructive = "UNKNOWN"

    drift_statuses = {row["state_tracked_drift_signal_status"] for row in root_results}
    if "STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED" in drift_statuses:
        aggregate_drift = "STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED"
    elif all_refresh_complete and drift_statuses == {"NONE_OBSERVED_IN_COMPLETE_REFRESH_ONLY_PLAN"}:
        aggregate_drift = "NONE_OBSERVED_IN_COMPLETE_REFRESH_ONLY_PLAN"
    else:
        aggregate_drift = "UNKNOWN"

    return {
        "source_mode": "TERRAFORM_READONLY_CONFIGURATION_AND_REFRESH_ONLY_PLAN_JSON",
        "source_status": "COMPLETE" if all_configuration_complete and all_refresh_complete else "INCOMPLETE",
        "roots_expected": len(roots),
        "roots_configuration_plan_complete": sum(
            row["configuration_vs_state"]["observation_status"] in complete_statuses
            for row in root_results
        ),
        "roots_refresh_only_plan_complete": sum(
            row["refresh_only"]["observation_status"] in complete_statuses
            for row in root_results
        ),
        "root_results": root_results,
        "configuration_action_counts": dict(sorted(aggregate_configuration.items())),
        "refresh_only_action_counts": dict(sorted(aggregate_refresh.items())),
        "configuration_plan_status": (
            "COMPLETE" if all_configuration_complete else "INCOMPLETE"
        ),
        "state_tracked_refresh_drift_status": aggregate_drift,
        "destructive_change_status": aggregate_destructive,
        "apply_result_status": "UNKNOWN",
        "live_resource_coverage_status": "UNKNOWN",
        "state_backed_coverage_status": "UNKNOWN",
    }


def _format_counts(values: dict[str, int]) -> str:
    if not values:
        return "NONE_OBSERVED"
    return ",".join(f"{key}={values[key]}" for key in sorted(values))


def main() -> int:
    result = discover()

    print("===== M6 TERRAFORM READ-ONLY PLAN EVIDENCE =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("terraform_apply_invoked: False")
    print("terraform_state_locking_allowed: False")
    print("saved_plan_written: False")
    print("raw_plan_output_projected: False")
    print("raw_diagnostics_projected: False")
    print("resource_addresses_projected: False")
    print("resource_names_projected: False")
    print("state_values_projected: False")
    print("tfvars_values_projected: False")
    print("provider_read_observation_allowed: True")

    print()
    print("===== PLAN SOURCE =====")
    print("source_mode:", result["source_mode"])
    print("source_status:", result["source_status"])
    print("roots_expected:", result["roots_expected"])
    print("roots_configuration_plan_complete:", result["roots_configuration_plan_complete"])
    print("roots_refresh_only_plan_complete:", result["roots_refresh_only_plan_complete"])

    for row in result["root_results"]:
        configuration = row["configuration_vs_state"]
        refresh_only = row["refresh_only"]
        print(
            f"root={row['root']} "
            f"configuration_plan={configuration['observation_status']} "
            f"configuration_exit_code={configuration['terraform_exit_code']} "
            f"configuration_actions={_format_counts(configuration['action_counts'])} "
            f"refresh_only_plan={refresh_only['observation_status']} "
            f"refresh_only_exit_code={refresh_only['terraform_exit_code']} "
            f"refresh_only_actions={_format_counts(refresh_only['action_counts'])} "
            f"destructive_change_status={row['destructive_change_status']} "
            f"state_tracked_drift_signal_status={row['state_tracked_drift_signal_status']}"
        )

    print()
    print("===== AGGREGATE READ-ONLY GOVERNANCE EVIDENCE =====")
    print("configuration_action_counts:", _format_counts(result["configuration_action_counts"]))
    print("refresh_only_action_counts:", _format_counts(result["refresh_only_action_counts"]))
    print("configuration_plan_status:", result["configuration_plan_status"])
    print("state_tracked_refresh_drift_status:", result["state_tracked_refresh_drift_status"])
    print("destructive_change_status:", result["destructive_change_status"])

    print()
    print("===== PRESERVED BOUNDARIES =====")
    print("apply_result_status: UNKNOWN")
    print("live_resource_coverage_status: UNKNOWN")
    print("state_backed_coverage_status: UNKNOWN")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("The configuration plan uses refresh=false and compares declared configuration with the bounded local state; it is not a live drift check.")
    print("The refresh-only plan may read the provider and can signal differences between state-tracked resources and live provider observations within the bounded roots.")
    print("A complete refresh-only no-change result is bounded state-tracked alignment evidence, not proof that all live resources are Terraform-managed.")
    print("A destructive action is classified only from recognized configuration-plan action events. Unclassified plan changes preserve destructive-change status as UNKNOWN.")
    print("No apply result, full live-resource coverage, or universal drift claim is inferred.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Terraform stdout/stderr remain process-local and are not printed or persisted; only allowlisted aggregate action categories and statuses are projected.")
    print("No saved plan is written. State locking is disabled. Terraform apply/import/state mutation commands are not invoked.")
    print("Resource addresses/names, instance identities, raw diagnostics, state/tfvars values, provider configuration values, endpoints, credentials, and sensitive connection strings are not projected.")
    print("Provider reads during refresh-only planning are observation-only; no infrastructure mutation is performed.")

    return 0 if result["source_status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
