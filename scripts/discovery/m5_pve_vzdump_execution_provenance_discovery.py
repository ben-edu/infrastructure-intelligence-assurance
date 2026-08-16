from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from infra_assurance.proxmox_ve_backup_evidence import build_getter_from_env

ENV_FILE = Path(
    "/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env"
)
TASK_SOURCE = Path("/tmp/proxmox-ve-backup-task-results.json")
EXPECTED_TASK_HASH = (
    "18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de"
)
TASK_LIMIT = 500

# Only these field names are considered possible explicit provenance signals.
# Their raw values are never printed or persisted by this discovery.
PROVENANCE_KEYS = {
    "schedule",
    "scheduler",
    "jobid",
    "job-id",
    "job_id",
    "trigger",
    "triggered-by",
    "triggered_by",
    "origin",
    "source",
    "source_type",
    "automation",
}

TRIGGER_KEYS = {
    "trigger",
    "triggered-by",
    "triggered_by",
    "origin",
    "source",
    "source_type",
}

SCHEDULE_KEYS = {"schedule", "scheduler"}
JOB_KEYS = {"jobid", "job-id", "job_id"}


def _epoch_to_rfc3339(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return (
            datetime.fromtimestamp(float(value), tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except (OSError, OverflowError, ValueError):
        return None


def _safe_vmid(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _task_result_id(
    source_id: str,
    node: str,
    vmid: int,
    start: str | None,
    end: str | None,
) -> str:
    material = f"{source_id}|{node}|{vmid}|{start or '-'}|{end or '-'}|vzdump"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"pve-backup-task:{digest}"


def _load_accepted_task_source() -> dict[str, Any] | None:
    print("===== ACCEPTED TASK SOURCE VERIFICATION =====")

    if not TASK_SOURCE.exists():
        print(f"{TASK_SOURCE}: NOT_FOUND")
        return None

    try:
        raw = TASK_SOURCE.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"{TASK_SOURCE}: FAILED_TO_READ {type(exc).__name__}")
        return None

    print(f"{TASK_SOURCE}: hash_match={digest == EXPECTED_TASK_HASH}")

    if digest != EXPECTED_TASK_HASH or not isinstance(payload, dict):
        return None

    if payload.get("pve_backup_task_results_version") != "0.1":
        print("accepted_task_source_version: UNSUPPORTED")
        return None

    if payload.get("mutation_allowed") is not False:
        print("accepted_task_source_read_only_contract: FAILED")
        return None

    return payload


def _strict_task_ids(payload: dict[str, Any]) -> set[str]:
    strict_ids: set[str] = set()

    for item in payload.get("recovery_point_correlations", []):
        if not isinstance(item, dict):
            continue
        if item.get("status") != "STRICT_SUCCESS_TASK_MATCH":
            continue
        task_id = item.get("task_result_id")
        if isinstance(task_id, str) and task_id:
            strict_ids.add(task_id)

    return strict_ids


def _raw_task_index(
    data: Any,
    *,
    source_id: str,
    node: str,
    strict_ids: set[str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    if not isinstance(data, list):
        return result

    for item in data:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").lower() != "vzdump":
            continue

        vmid = _safe_vmid(item.get("id"))
        if vmid is None:
            continue

        start = _epoch_to_rfc3339(item.get("starttime"))
        end = _epoch_to_rfc3339(item.get("endtime"))
        task_id = _task_result_id(source_id, node, vmid, start, end)

        if task_id in strict_ids:
            result[task_id] = item

    return result


def _present_provenance_keys(payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(payload, dict):
        return []
    return sorted(key for key in PROVENANCE_KEYS if key in payload)


def _normalized_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().lower()
    return token or None


def _classify_explicit_provenance(
    task_item: dict[str, Any],
    detail: dict[str, Any] | None,
) -> str:
    sources = [task_item]
    if isinstance(detail, dict):
        sources.append(detail)

    # An explicit schedule/scheduler field or job identifier is accepted only as
    # scheduler/job provenance. Presence is not inferred from timestamp patterns.
    for source in sources:
        for key in SCHEDULE_KEYS:
            if key in source and source.get(key) not in (None, "", False):
                return "SCHEDULED_PROVENANCE_OBSERVED"
        for key in JOB_KEYS:
            if key in source and source.get(key) not in (None, "", False):
                return "SCHEDULED_PROVENANCE_OBSERVED"

    for source in sources:
        for key in TRIGGER_KEYS:
            token = _normalized_token(source.get(key))
            if token in {"manual", "interactive"}:
                return "MANUAL_PROVENANCE_OBSERVED"
            if token in {"scheduled", "schedule", "scheduler", "cron"}:
                return "SCHEDULED_PROVENANCE_OBSERVED"
            if token in {
                "external",
                "external-orchestration",
                "orchestrator",
                "automation",
            }:
                return "EXTERNAL_ORCHESTRATION_PROVENANCE_OBSERVED"

    return "PROVENANCE_NOT_EXPLICITLY_RETURNED"


def main() -> int:
    print("===== PVE VZDUMP EXECUTION PROVENANCE DISCOVERY =====")
    print()

    accepted = _load_accepted_task_source()
    if accepted is None:
        print("discovery_status: FAILED_TO_OBSERVE_ACCEPTED_SOURCE")
        print("No mutation was performed.")
        return 2

    source = accepted.get("source", {})
    source_id = source.get("source_id")
    node = source.get("node")

    if not isinstance(source_id, str) or not source_id:
        print("accepted_source_id: INVALID")
        return 2
    if not isinstance(node, str) or not node:
        print("accepted_node: INVALID")
        return 2

    strict_ids = _strict_task_ids(accepted)

    print()
    print("===== ACCEPTED STRICT TASK SCOPE =====")
    print("source_id:", source_id)
    print("node:", node)
    print("strict_success_task_ids:", len(strict_ids))

    try:
        getter, trust = build_getter_from_env(
            ENV_FILE,
            allow_discovery_credential=True,
            allow_insecure_tls_discovery=True,
        )
    except Exception as exc:
        print("credential_context: FAILED_TO_OBSERVE")
        print("error_class:", type(exc).__name__)
        print("No mutation was performed.")
        return 0

    print()
    print("===== BOUNDED PVE TASK LIST =====")

    status, data, error = getter(
        f"/api2/json/nodes/{node}/tasks",
        {"typefilter": "vzdump", "limit": str(TASK_LIMIT)},
    )
    request_mode = "SERVER_FILTERED_VZDUMP"

    if status == 400:
        status, data, error = getter(
            f"/api2/json/nodes/{node}/tasks",
            {"limit": str(TASK_LIMIT)},
        )
        request_mode = "BOUNDED_LOCAL_TYPE_FILTER"

    print("operation: GET bounded task metadata")
    print("http_status:", status if status is not None else "NONE")
    print("request_mode:", request_mode)
    print("runtime_credential_approved:", trust["runtime_credential_approved"])

    if status != 200 or not isinstance(data, list):
        print("task_metadata_source_status: FAILED_TO_OBSERVE")
        print("error_class:", error or "UNKNOWN")
        print("No mutation was performed.")
        return 0

    raw_index = _raw_task_index(
        data,
        source_id=source_id,
        node=node,
        strict_ids=strict_ids,
    )

    print("task_metadata_source_status: COMPLETE")
    print("strict_tasks_matched_in_returned_history:", len(raw_index))
    print("strict_tasks_not_matched_in_returned_history:", len(strict_ids - set(raw_index)))

    counters: Counter[str] = Counter()
    detail_complete = 0
    detail_failed = 0

    print()
    print("===== STRICT TASK PROVENANCE =====")

    accepted_task_rows = {
        item.get("task_result_id"): item
        for item in accepted.get("task_results", [])
        if isinstance(item, dict)
        and isinstance(item.get("task_result_id"), str)
    }

    for task_id in sorted(strict_ids):
        accepted_row = accepted_task_rows.get(task_id, {})
        vmid = _safe_vmid(accepted_row.get("vmid"))
        start_time = accepted_row.get("start_time")
        task_item = raw_index.get(task_id)

        if not isinstance(task_item, dict):
            classification = "FAILED_TO_OBSERVE"
            counters[classification] += 1
            print(
                f"task={task_id} vmid={vmid if vmid is not None else 'UNKNOWN'} "
                f"start={start_time or 'UNKNOWN'} "
                "task_list_match=False detail_status=NOT_ATTEMPTED "
                f"provenance={classification} explicit_fields=NONE"
            )
            continue

        list_fields = _present_provenance_keys(task_item)
        detail: dict[str, Any] | None = None
        detail_status: int | None = None

        # UPID is used only in memory to address the authoritative task-status API.
        # It is never printed or persisted.
        upid = task_item.get("upid")
        if isinstance(upid, str) and upid:
            detail_status, detail_data, _detail_error = getter(
                f"/api2/json/nodes/{node}/tasks/{quote(upid, safe='')}/status",
                None,
            )
            if detail_status == 200 and isinstance(detail_data, dict):
                detail = detail_data
                detail_complete += 1
            else:
                detail_failed += 1
        else:
            detail_failed += 1

        detail_fields = _present_provenance_keys(detail)
        fields = sorted(set(list_fields) | set(detail_fields))

        if detail is None:
            classification = "FAILED_TO_OBSERVE"
        else:
            classification = _classify_explicit_provenance(task_item, detail)

        counters[classification] += 1

        print(
            f"task={task_id} vmid={vmid if vmid is not None else 'UNKNOWN'} "
            f"start={start_time or 'UNKNOWN'} "
            "task_list_match=True "
            f"detail_status={detail_status if detail_status is not None else 'NOT_AVAILABLE'} "
            f"provenance={classification} "
            f"explicit_fields={','.join(fields) if fields else 'NONE'}"
        )

    print()
    print("===== SUMMARY =====")
    print("strict_success_tasks_total:", len(strict_ids))
    print("task_list_matches:", len(raw_index))
    print("task_detail_complete:", detail_complete)
    print("task_detail_failed_to_observe:", detail_failed)
    print(
        "scheduled_provenance_observed:",
        counters["SCHEDULED_PROVENANCE_OBSERVED"],
    )
    print(
        "manual_provenance_observed:",
        counters["MANUAL_PROVENANCE_OBSERVED"],
    )
    print(
        "external_orchestration_provenance_observed:",
        counters["EXTERNAL_ORCHESTRATION_PROVENANCE_OBSERVED"],
    )
    print(
        "provenance_not_explicitly_returned:",
        counters["PROVENANCE_NOT_EXPLICITLY_RETURNED"],
    )
    print("failed_to_observe:", counters["FAILED_TO_OBSERVE"])

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print(
        "Only explicit provenance fields/values from authoritative task metadata may "
        "classify scheduled, manual, or external provenance."
    )
    print(
        "User identity, timestamp patterns, successful task status, and current backup-job "
        "absence are not provenance evidence."
    )
    print(
        "PROVENANCE_NOT_EXPLICITLY_RETURNED means the inspected authoritative task-list "
        "and task-status metadata did not explicitly identify execution origin."
    )
    print(
        "Historical successful VZDUMP evidence remains valid execution evidence regardless "
        "of provenance classification."
    )

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only GET/read-only PVE API calls were used.")
    print("Raw UPIDs were used only in memory for task-status lookup and were not printed.")
    print("Raw task logs were not read.")
    print("Raw user values, commands, hooks, notes, notification targets, credentials, and backup contents were not printed.")
    print("No backup job, task, storage, retention, schedule, or infrastructure state was changed.")
    print("No mutation was performed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
