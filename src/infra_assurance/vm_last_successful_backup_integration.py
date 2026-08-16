from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_json, atomic_write_text

INTEGRATION_VERSION = "0.1"
OUTPUT_VM_ASSURANCE_VERSION = "0.2"
REQUIRED_VM_ASSURANCE_VERSION = "0.1"
REQUIRED_TASK_RESULTS_VERSION = "0.1"


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _task_index(task_artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in task_artifact.get("task_results", []):
        if not isinstance(item, dict):
            continue
        task_result_id = item.get("task_result_id")
        if not isinstance(task_result_id, str) or not task_result_id:
            continue
        if task_result_id in result:
            raise ValueError("duplicate task_result_id in task artifact")
        result[task_result_id] = item
    return result


def _recovery_point_owner(vm_artifact: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for asset in vm_artifact.get("assets", []):
        if not isinstance(asset, dict):
            continue
        subject = asset.get("subject", {})
        vmid = subject.get("vmid")
        if isinstance(vmid, bool) or not isinstance(vmid, int):
            continue
        for recovery_point_id in asset.get("source_recovery_point_ids", []):
            if not isinstance(recovery_point_id, str) or not recovery_point_id:
                continue
            previous = result.get(recovery_point_id)
            if previous is not None and previous != vmid:
                raise ValueError("recovery point identity is assigned to multiple VMs")
            result[recovery_point_id] = vmid
    return result


def _validated_correlations(
    vm_artifact: dict[str, Any],
    task_artifact: dict[str, Any],
) -> tuple[dict[int, list[dict[str, Any]]], int]:
    task_index = _task_index(task_artifact)
    point_owner = _recovery_point_owner(vm_artifact)
    strict_by_vmid: dict[int, list[dict[str, Any]]] = {}
    unmatched = 0

    for correlation in task_artifact.get("recovery_point_correlations", []):
        if not isinstance(correlation, dict):
            continue
        recovery_point_id = correlation.get("recovery_point_id")
        vmid = correlation.get("vmid")
        status = correlation.get("status")

        if not isinstance(recovery_point_id, str) or not recovery_point_id:
            raise ValueError("task correlation is missing recovery_point_id")
        if isinstance(vmid, bool) or not isinstance(vmid, int):
            raise ValueError("task correlation is missing numeric VMID")
        if recovery_point_id not in point_owner:
            raise ValueError("task correlation references an unknown recovery point")
        if point_owner[recovery_point_id] != vmid:
            raise ValueError("task correlation VMID does not match VM assurance recovery-point ownership")

        if status == "NO_STRICT_MATCH_IN_RETURNED_HISTORY":
            unmatched += 1
            continue
        if status != "STRICT_SUCCESS_TASK_MATCH":
            raise ValueError("unsupported recovery-point correlation status")

        task_result_id = correlation.get("task_result_id")
        if not isinstance(task_result_id, str) or not task_result_id:
            raise ValueError("strict task correlation is missing task_result_id")
        task = task_index.get(task_result_id)
        if task is None:
            raise ValueError("strict task correlation references a missing task result")
        if task.get("task_type") != "VZDUMP":
            raise ValueError("strict task correlation does not reference a VZDUMP result")
        if task.get("result") != "SUCCESS":
            raise ValueError("strict task correlation does not reference a successful result")
        if task.get("vmid") != vmid:
            raise ValueError("strict task correlation VMID does not match task result")
        successful_at = task.get("end_time")
        if not isinstance(successful_at, str) or not successful_at:
            raise ValueError("successful task result is missing completion time")

        strict_by_vmid.setdefault(vmid, []).append(
            {
                "recovery_point_id": recovery_point_id,
                "task_result_id": task_result_id,
                "successful_at": successful_at,
            }
        )

    for values in strict_by_vmid.values():
        values.sort(
            key=lambda item: (
                item["successful_at"],
                item["task_result_id"],
                item["recovery_point_id"],
            )
        )

    return strict_by_vmid, unmatched


def _mark_last_successful_backup_observed(
    asset: dict[str, Any],
    *,
    source_id: str,
    evidence: dict[str, Any],
) -> None:
    assurance = asset.setdefault("assurance", {})
    assurance["last_successful_backup_status"] = "OBSERVED"
    assurance["last_successful_backup_at"] = evidence["successful_at"]
    assurance["last_successful_backup_evidence"] = {
        "source_type": "PROXMOX_VE_VZDUMP_TASK_RESULT",
        "source_id": source_id,
        "recovery_point_id": evidence["recovery_point_id"],
        "task_result_id": evidence["task_result_id"],
        "basis": ["STRICT_SUCCESS_TASK_MATCH"],
    }

    for item in asset.get("required_evidence", []):
        if not isinstance(item, dict) or item.get("target") != "LAST_SUCCESSFUL_BACKUP":
            continue
        item["status"] = "OBSERVED"
        item["statement"] = (
            "A retained recovery point is strictly correlated to an authoritative successful PVE VZDUMP task result."
        )


def _mark_last_successful_backup_unknown(asset: dict[str, Any]) -> None:
    assurance = asset.setdefault("assurance", {})
    assurance["last_successful_backup_status"] = "UNKNOWN"
    assurance["last_successful_backup_at"] = None
    assurance["last_successful_backup_evidence"] = None


def build_vm_last_successful_backup_integration(
    vm_assurance_artifact: dict[str, Any],
    task_result_artifact: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    vm_artifact = deepcopy(vm_assurance_artifact)
    task_artifact = deepcopy(task_result_artifact)

    if vm_artifact.get("vm_backup_assurance_version") != REQUIRED_VM_ASSURANCE_VERSION:
        raise ValueError("unsupported VM Backup Assurance input version")
    if task_artifact.get("pve_backup_task_results_version") != REQUIRED_TASK_RESULTS_VERSION:
        raise ValueError("unsupported PVE backup task-results input version")
    if vm_artifact.get("mutation_allowed") is not False:
        raise ValueError("VM Backup Assurance input must be read-only evidence")
    if task_artifact.get("mutation_allowed") is not False:
        raise ValueError("PVE task-results input must be read-only evidence")

    vm_source = vm_artifact.get("source_status", {})
    task_source = task_artifact.get("source", {})
    vm_source_id = vm_source.get("source_id")
    task_source_id = task_source.get("source_id")
    if not isinstance(vm_source_id, str) or not vm_source_id:
        raise ValueError("VM Backup Assurance input is missing source identity")
    if vm_source_id != task_source_id:
        raise ValueError("VM Backup Assurance and task-result source identities do not match")
    if vm_source.get("source_type") != "PROXMOX_VE":
        raise ValueError("VM Backup Assurance source type is not PROXMOX_VE")
    if task_source.get("type") != "proxmox_ve_api":
        raise ValueError("task-result source type is not Proxmox VE API")

    strict_by_vmid, unmatched = _validated_correlations(vm_artifact, task_artifact)
    task_source_status = task_source.get("status")
    if task_source_status not in {"COMPLETE", "FAILED_TO_OBSERVE"}:
        task_source_status = "FAILED_TO_OBSERVE"

    assets = vm_artifact.get("assets", [])
    if not isinstance(assets, list):
        raise ValueError("VM Backup Assurance assets must be a list")

    observed_assets = 0
    strict_consumed = 0

    preserved_fields = (
        "protection_status",
        "integrity_verification_status",
        "restore_verification_status",
        "failure_domain_status",
        "scheduled_protection_status",
        "rpo_status",
        "rto_status",
    )

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        subject = asset.get("subject", {})
        vmid = subject.get("vmid")
        if isinstance(vmid, bool) or not isinstance(vmid, int):
            continue
        if subject.get("source_id") != vm_source_id:
            raise ValueError("VM asset source identity does not match assurance source")

        assurance = asset.get("assurance", {})
        before = {key: assurance.get(key) for key in preserved_fields}
        matches = strict_by_vmid.get(vmid, []) if task_source_status == "COMPLETE" else []

        asset_points = {
            value
            for value in asset.get("source_recovery_point_ids", [])
            if isinstance(value, str) and value
        }
        valid_matches = [item for item in matches if item["recovery_point_id"] in asset_points]

        if valid_matches:
            latest = max(
                valid_matches,
                key=lambda item: (
                    item["successful_at"],
                    item["task_result_id"],
                    item["recovery_point_id"],
                ),
            )
            _mark_last_successful_backup_observed(
                asset,
                source_id=vm_source_id,
                evidence=latest,
            )
            observed_assets += 1
            strict_consumed += len(valid_matches)
        else:
            _mark_last_successful_backup_unknown(asset)

        after = {key: asset.get("assurance", {}).get(key) for key in preserved_fields}
        if after != before:
            raise ValueError("integration attempted to modify unrelated assurance dimensions")

    vm_artifact["vm_backup_assurance_version"] = OUTPUT_VM_ASSURANCE_VERSION
    vm_artifact["generated_at"] = _rfc3339(now or datetime.now(timezone.utc))
    vm_artifact["mutation_allowed"] = False
    vm_artifact["last_successful_backup_integration"] = {
        "version": INTEGRATION_VERSION,
        "mode": "STRICT_CORRELATION_ONLY",
        "source_type": "PROXMOX_VE_VZDUMP_TASK_RESULTS",
        "source_id": vm_source_id,
        "source_artifact_version": task_artifact.get("pve_backup_task_results_version"),
        "source_status": task_source_status,
        "source_generated_at": task_artifact.get("generated_at"),
        "source_freshness": "UNKNOWN",
        "historical_completeness": task_source.get("historical_completeness", "NOT_ESTABLISHED"),
    }

    summary = vm_artifact.setdefault("summary", {})
    summary["last_successful_backup_observed"] = observed_assets
    summary["last_successful_backup_unknown"] = len(assets) - observed_assets
    summary["strict_success_correlations_consumed"] = strict_consumed
    summary["unmatched_recovery_points_in_returned_task_history"] = unmatched

    unknowns = vm_artifact.setdefault("unknowns", [])
    existing_codes = {
        item.get("code")
        for item in unknowns
        if isinstance(item, dict)
    }
    additions = (
        (
            "TASK_RESULT_SOURCE_FRESHNESS_UNKNOWN",
            "The accepted PVE task-result artifact has no TTL/expiry contract, so task-result source freshness remains UNKNOWN.",
        ),
        (
            "TASK_HISTORY_COMPLETENESS_NOT_ESTABLISHED",
            "PVE task-history retention completeness is not established. Missing historical matches are not failed-backup evidence.",
        ),
    )
    if unmatched:
        additions += (
            (
                "UNMATCHED_HISTORICAL_RECOVERY_POINTS_NOT_FAILURES",
                "Some retained recovery points have no strict task-result match in returned history; they remain unsupported historical evidence, not failed backups.",
            ),
        )

    for code, statement in additions:
        if code in existing_codes:
            continue
        unknowns.append(
            {
                "code": code,
                "subject": vm_source_id if code == "TASK_RESULT_SOURCE_FRESHNESS_UNKNOWN" else None,
                "statement": statement,
            }
        )

    return vm_artifact


def render_vm_last_successful_backup_markdown(artifact: dict[str, Any]) -> str:
    integration = artifact.get("last_successful_backup_integration", {})
    summary = artifact.get("summary", {})
    lines = [
        "# Backup and Recovery Assurance — VM Last Successful Backup",
        "",
        f"Generated: `{artifact.get('generated_at')}`",
        f"Mutation allowed: `{str(artifact.get('mutation_allowed', True)).lower()}`",
        f"Source: `{integration.get('source_type')}/{integration.get('source_id')}`",
        f"Source status: `{integration.get('source_status')}`",
        f"Source freshness: `{integration.get('source_freshness')}`",
        f"Historical completeness: `{integration.get('historical_completeness')}`",
        "",
        "## Summary",
        "",
        f"- assets_total: {summary.get('assets_total', 0)}",
        f"- last_successful_backup_observed: {summary.get('last_successful_backup_observed', 0)}",
        f"- last_successful_backup_unknown: {summary.get('last_successful_backup_unknown', 0)}",
        f"- strict_success_correlations_consumed: {summary.get('strict_success_correlations_consumed', 0)}",
        f"- unmatched_recovery_points_in_returned_task_history: {summary.get('unmatched_recovery_points_in_returned_task_history', 0)}",
        f"- unprotected_claims: {summary.get('unprotected_claims', 0)}",
        "",
        "## VM last successful backup",
        "",
    ]

    for asset in artifact.get("assets", []):
        subject = asset.get("subject", {})
        assurance = asset.get("assurance", {})
        evidence = assurance.get("last_successful_backup_evidence") or {}
        lines.append(
            "- VMID "
            + str(subject.get("vmid"))
            + " status="
            + str(assurance.get("last_successful_backup_status"))
            + " latest="
            + str(assurance.get("last_successful_backup_at") or "unknown")
            + " evidence="
            + str(evidence.get("basis", ["none"])[0] if evidence else "none")
        )

    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "Only accepted strict recovery-point/task correlations may establish an observed last successful backup.",
            "Protection, restore verification, integrity verification, failure domain, scheduled protection, RPO, and RTO are not strengthened by this integration.",
            "Historical task completeness remains unestablished; unmatched old recovery points are not backup-failure evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive VM last-successful-backup assurance from accepted task-result evidence.")
    parser.add_argument("--vm-assurance", required=True, type=Path)
    parser.add_argument("--task-results", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--summary-out", required=True, type=Path)
    args = parser.parse_args(argv)

    vm_artifact = json.loads(args.vm_assurance.read_text(encoding="utf-8"))
    task_artifact = json.loads(args.task_results.read_text(encoding="utf-8"))
    result = build_vm_last_successful_backup_integration(vm_artifact, task_artifact)
    atomic_write_json(args.out, result)
    atomic_write_text(args.summary_out, render_vm_last_successful_backup_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
