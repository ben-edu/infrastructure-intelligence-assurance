from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_json, atomic_write_text
from .proxmox_ve_backup_evidence import build_getter_from_env

PVE_BACKUP_TASK_RESULTS_VERSION = "0.1"
DEFAULT_TASK_LIMIT = 500
STRICT_START_DELTA_SECONDS = 2


def _now_rfc3339(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _epoch_to_rfc3339(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (OSError, OverflowError, ValueError):
        return None


def _rfc3339_to_epoch(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _safe_vmid(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _task_result_id(source_id: str, node: str, vmid: int, start: str | None, end: str | None) -> str:
    material = f"{source_id}|{node}|{vmid}|{start or '-'}|{end or '-'}|vzdump"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    return f"pve-backup-task:{digest}"


def _normalize_result(item: dict[str, Any]) -> str:
    endtime = item.get("endtime")
    status = item.get("status")
    if not isinstance(endtime, (int, float)) or isinstance(endtime, bool):
        return "RUNNING_OR_INCOMPLETE"
    if status == "OK":
        return "SUCCESS"
    if status in (None, ""):
        return "UNKNOWN"
    return "FAILURE"


def _normalize_tasks(
    data: Any,
    *,
    source_id: str,
    node: str,
    accepted_vmids: set[int],
) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").lower() != "vzdump":
            continue
        vmid = _safe_vmid(item.get("id"))
        if vmid is None or vmid not in accepted_vmids:
            continue
        start = _epoch_to_rfc3339(item.get("starttime"))
        end = _epoch_to_rfc3339(item.get("endtime"))
        rows.append(
            {
                "task_result_id": _task_result_id(source_id, node, vmid, start, end),
                "task_type": "VZDUMP",
                "node": node,
                "vmid": vmid,
                "start_time": start,
                "end_time": end,
                "result": _normalize_result(item),
            }
        )
    return sorted(rows, key=lambda item: (item["start_time"] or "", item["vmid"]), reverse=True)


def _correlate_recovery_points(
    source_artifact: dict[str, Any],
    task_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    success_by_vmid: dict[int, list[dict[str, Any]]] = {}
    for task in task_results:
        if task["result"] == "SUCCESS":
            success_by_vmid.setdefault(task["vmid"], []).append(task)

    correlations: list[dict[str, Any]] = []
    for point in source_artifact.get("recovery_points", []):
        if not isinstance(point, dict):
            continue
        recovery_point_id = point.get("recovery_point_id")
        vmid = _safe_vmid(point.get("vmid"))
        point_epoch = _rfc3339_to_epoch(point.get("created_at"))
        if not isinstance(recovery_point_id, str) or vmid is None or point_epoch is None:
            continue

        matches: list[tuple[float, dict[str, Any]]] = []
        for task in success_by_vmid.get(vmid, []):
            start_epoch = _rfc3339_to_epoch(task.get("start_time"))
            if start_epoch is None:
                continue
            delta = abs(point_epoch - start_epoch)
            if delta <= STRICT_START_DELTA_SECONDS:
                matches.append((delta, task))

        if not matches:
            correlations.append(
                {
                    "recovery_point_id": recovery_point_id,
                    "vmid": vmid,
                    "status": "NO_STRICT_MATCH_IN_RETURNED_HISTORY",
                    "task_result_id": None,
                    "start_delta_seconds": None,
                    "basis": ["VMID", "RECOVERY_POINT_CREATED_AT", "VZDUMP_START_TIME"],
                }
            )
            continue

        matches.sort(key=lambda value: (value[0], value[1]["task_result_id"]))
        delta, task = matches[0]
        correlations.append(
            {
                "recovery_point_id": recovery_point_id,
                "vmid": vmid,
                "status": "STRICT_SUCCESS_TASK_MATCH",
                "task_result_id": task["task_result_id"],
                "start_delta_seconds": int(delta),
                "basis": ["VMID", "RECOVERY_POINT_CREATED_AT", "VZDUMP_START_TIME"],
            }
        )

    return sorted(correlations, key=lambda item: (item["vmid"], item["recovery_point_id"]))


def collect_pve_backup_task_results(
    source_artifact: dict[str, Any],
    get_json,
    *,
    source_id: str,
    node: str,
    credential_context: dict[str, Any],
    task_limit: int = DEFAULT_TASK_LIMIT,
    now: datetime | None = None,
) -> dict[str, Any]:
    if source_artifact.get("proxmox_ve_backup_evidence_version") != "0.1":
        raise ValueError("unsupported Proxmox VE backup source artifact version")
    if source_artifact.get("mutation_allowed") is not False:
        raise ValueError("source artifact must be read-only evidence")
    source = source_artifact.get("source", {})
    if source.get("source_id") != source_id or source.get("node") != node:
        raise ValueError("source artifact identity must match requested PVE source and node")

    accepted_vmids = {
        vmid
        for item in source_artifact.get("guests", [])
        if isinstance(item, dict)
        for vmid in [_safe_vmid(item.get("vmid"))]
        if vmid is not None
    }

    status_code, data, error_class = get_json(
        f"/api2/json/nodes/{node}/tasks",
        {"typefilter": "vzdump", "limit": str(task_limit)},
    )
    request_mode = "SERVER_FILTERED_VZDUMP"
    if status_code == 400:
        status_code, data, error_class = get_json(
            f"/api2/json/nodes/{node}/tasks",
            {"limit": str(task_limit)},
        )
        request_mode = "BOUNDED_LOCAL_TYPE_FILTER"

    observation_status = "COMPLETE" if status_code == 200 and isinstance(data, list) else "FAILED_TO_OBSERVE"
    raw_rows_returned = len(data) if isinstance(data, list) else 0
    limit_saturated = bool(observation_status == "COMPLETE" and raw_rows_returned >= task_limit)
    task_results = (
        _normalize_tasks(data, source_id=source_id, node=node, accepted_vmids=accepted_vmids)
        if observation_status == "COMPLETE"
        else []
    )
    correlations = (
        _correlate_recovery_points(source_artifact, task_results)
        if observation_status == "COMPLETE"
        else []
    )

    unknowns: list[dict[str, Any]] = [
        {
            "code": "TASK_HISTORY_COMPLETENESS_NOT_ESTABLISHED",
            "statement": (
                "The bounded PVE task-list observation does not establish historical task retention completeness. "
                "Missing historical tasks must not be interpreted as failed or absent backups."
            ),
        }
    ]
    if limit_saturated:
        unknowns.append(
            {
                "code": "TASK_RESULT_LIMIT_SATURATED",
                "statement": "The bounded task-list response reached its configured limit; additional returned-history records may exist.",
            }
        )
    if observation_status != "COMPLETE":
        unknowns.append(
            {
                "code": "TASK_HISTORY_FAILED_TO_OBSERVE",
                "statement": "Current PVE backup task history could not be observed; no task absence conclusion is allowed.",
            }
        )

    return {
        "pve_backup_task_results_version": PVE_BACKUP_TASK_RESULTS_VERSION,
        "generated_at": _now_rfc3339(now),
        "mutation_allowed": False,
        "source": {
            "type": "proxmox_ve_api",
            "source_id": source_id,
            "node": node,
            "operation": "GET_BOUNDED_VZDUMP_TASK_RESULTS",
            "status": observation_status,
            "request_mode": request_mode,
            "task_limit": task_limit,
            "limit_saturated": limit_saturated,
            "historical_completeness": "NOT_ESTABLISHED",
            "credential_file_mode_secure": bool(credential_context.get("credential_file_mode_secure", False)),
            "tls_verification": bool(credential_context.get("tls_verification", False)),
            "runtime_credential_approved": False,
            "discovery_override_used": bool(credential_context.get("discovery_override_used", False)),
        },
        "observation": {
            "operation": "GET_VZDUMP_TASK_RESULTS",
            "status": observation_status,
            "http_status": status_code,
            "error_class": error_class,
            "rows_returned": raw_rows_returned,
        },
        "task_results": task_results,
        "recovery_point_correlations": correlations,
        "summary": {
            "accepted_current_vmids": len(accepted_vmids),
            "task_results_projected": len(task_results),
            "successful_task_results": sum(item["result"] == "SUCCESS" for item in task_results),
            "strict_recovery_point_task_matches": sum(
                item["status"] == "STRICT_SUCCESS_TASK_MATCH" for item in correlations
            ),
            "recovery_points_without_strict_match_in_returned_history": sum(
                item["status"] == "NO_STRICT_MATCH_IN_RETURNED_HISTORY" for item in correlations
            ),
        },
        "unknowns": unknowns,
        "caveats": [
            "A PVE task result with status SUCCESS is authoritative evidence that the returned vzdump task record completed with status OK; it is not restore verification.",
            "A strict VMID/start-time recovery-point correlation is evidence of a tightly aligned task/archive relationship, but raw task logs and UPIDs are intentionally excluded.",
            "No strict match in returned history is not evidence of backup failure or universal backup absence because historical task retention completeness is not established.",
            "This artifact does not establish integrity verification, restore verification, RPO compliance, RTO compliance, or runtime credential approval.",
        ],
    }


def render_markdown(artifact: dict[str, Any]) -> str:
    source = artifact["source"]
    summary = artifact["summary"]
    lines = [
        "# Proxmox VE Backup Task Results",
        "",
        f"Generated: `{artifact['generated_at']}`",
        f"Source: `{source['source_id']}`",
        f"Node: `{source['node']}`",
        f"Source status: `{source['status']}`",
        "Mutation allowed: `false`",
        "Runtime credential approved: `false`",
        f"Historical completeness: `{source['historical_completeness']}`",
        "",
        "## Summary",
        "",
        f"- task_results_projected: {summary['task_results_projected']}",
        f"- successful_task_results: {summary['successful_task_results']}",
        f"- strict_recovery_point_task_matches: {summary['strict_recovery_point_task_matches']}",
        f"- recovery_points_without_strict_match_in_returned_history: {summary['recovery_points_without_strict_match_in_returned_history']}",
        "",
        "## Strict recovery-point correlations",
        "",
    ]
    for item in artifact["recovery_point_correlations"]:
        delta = item["start_delta_seconds"] if item["start_delta_seconds"] is not None else "unknown"
        lines.append(
            f"- VMID {item['vmid']} recovery_point={item['recovery_point_id']} status={item['status']} delta_seconds={delta}"
        )
    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "Successful PVE vzdump task results may support last-successful-backup evidence in a later derived slice. They do not establish restore or integrity verification.",
            "Task-history completeness is not established; missing historical task records are not backup-failure evidence.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect bounded Proxmox VE vzdump task-result evidence.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--credential-env-file", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--summary-out", required=True, type=Path)
    parser.add_argument("--task-limit", type=int, default=DEFAULT_TASK_LIMIT)
    parser.add_argument("--allow-discovery-credential", action="store_true")
    parser.add_argument("--allow-insecure-tls-discovery", action="store_true")
    args = parser.parse_args()

    if args.task_limit < 1 or args.task_limit > 5000:
        raise ValueError("task limit must be between 1 and 5000")

    source_artifact = json.loads(args.source.read_text(encoding="utf-8"))
    get_json, credential_context = build_getter_from_env(
        args.credential_env_file,
        allow_discovery_credential=args.allow_discovery_credential,
        allow_insecure_tls_discovery=args.allow_insecure_tls_discovery,
    )
    artifact = collect_pve_backup_task_results(
        source_artifact,
        get_json,
        source_id=args.source_id,
        node=args.node,
        credential_context=credential_context,
        task_limit=args.task_limit,
    )
    atomic_write_json(args.out, artifact)
    atomic_write_text(args.summary_out, render_markdown(artifact))


if __name__ == "__main__":
    main()
