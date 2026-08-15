from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_json, atomic_write_text

VM_BACKUP_ASSURANCE_VERSION = "0.1"
SOURCE_ARTIFACT_VERSION = "0.1"
ASSET_TYPE = "VIRTUAL_MACHINE"

_REQUIRED_TARGETS = (
    (
        "BACKUP_MECHANISM",
        "Identify the authoritative backup mechanism used for this VM, if any.",
    ),
    (
        "LAST_SUCCESSFUL_BACKUP",
        "Observe the latest successful backup result from an authoritative task/result source; recovery-point presence alone is not promoted to task success.",
    ),
    (
        "BACKUP_RETENTION",
        "Observe effective retention and retained recovery points; configuration alone is not retention-effectiveness verification.",
    ),
    (
        "BACKUP_FAILURE_DOMAIN",
        "Verify whether backup copies are outside the relevant VM/storage failure domain.",
    ),
    (
        "BACKUP_INTEGRITY_VERIFICATION",
        "Observe authoritative backup integrity or verification evidence.",
    ),
    (
        "RESTORE_TEST",
        "Observe a real restore test and its verified recovery result.",
    ),
    (
        "RPO_TARGET_AND_RESULT",
        "Observe the target RPO and sufficient recovery-point/task history to evaluate it.",
    ),
    (
        "RTO_TARGET_AND_RESULT",
        "Observe the target RTO and a restore test sufficient to evaluate recovery time.",
    ),
)


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _observation_status(source: dict[str, Any], operation: str) -> str:
    for item in source.get("observations", []):
        if item.get("operation") == operation:
            status = item.get("status")
            if status in {"COMPLETE", "PARTIAL", "FAILED_TO_OBSERVE"}:
                return status
            return "FAILED_TO_OBSERVE"
    return "FAILED_TO_OBSERVE"


def _storage_by_id(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in source.get("storages", []):
        storage_id = item.get("storage_id")
        if isinstance(storage_id, str) and storage_id:
            result[storage_id] = item
    return result


def _coverage_by_vmid(source: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for item in source.get("guest_storage_coverage", []):
        vmid = item.get("vmid")
        if isinstance(vmid, bool) or not isinstance(vmid, int):
            continue
        result.setdefault(vmid, []).append(item)
    for values in result.values():
        values.sort(key=lambda row: str(row.get("storage_id") or ""))
    return result


def _points_by_vmid(source: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for item in source.get("recovery_points", []):
        vmid = item.get("vmid")
        if isinstance(vmid, bool) or not isinstance(vmid, int):
            continue
        result.setdefault(vmid, []).append(item)
    for values in result.values():
        values.sort(
            key=lambda row: (
                str(row.get("created_at") or ""),
                str(row.get("recovery_point_id") or ""),
            )
        )
    return result


def _mechanism_evidence(
    source_id: str,
    node: str,
    coverage: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for item in coverage:
        if item.get("local_recovery_point_status") != "RECOVERY_POINT_OBSERVED":
            continue
        storage_id = item.get("storage_id")
        if not isinstance(storage_id, str) or not storage_id:
            continue
        result.append(
            {
                "type": "PROXMOX_VE_STORAGE_ARCHIVE",
                "source_type": "PROXMOX_VE",
                "source_id": source_id,
                "node": node,
                "storage_id": storage_id,
                "basis": ["RECOVERY_POINT_OBSERVED_IN_SOURCE_SCOPE"],
            }
        )
    result.sort(key=lambda item: (item["node"], item["storage_id"]))
    return result


def _retention_context(
    coverage: list[dict[str, Any]],
    storages: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for item in coverage:
        storage_id = item.get("storage_id")
        if not isinstance(storage_id, str) or not storage_id:
            continue
        storage = storages.get(storage_id, {})
        policy = storage.get("retention_policy")
        result.append(
            {
                "storage_id": storage_id,
                "configuration_status": "OBSERVED" if isinstance(policy, str) and policy else "UNKNOWN",
                "retention_policy": policy if isinstance(policy, str) and policy else None,
                "effectiveness_status": "UNKNOWN",
            }
        )
    result.sort(key=lambda item: item["storage_id"])
    return result


def _recovery_state(coverage: list[dict[str, Any]]) -> str:
    states = {item.get("local_recovery_point_status") for item in coverage}
    if "RECOVERY_POINT_OBSERVED" in states:
        return "OBSERVED"
    if states and states.issubset({"NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE"}):
        return "NOT_OBSERVED_IN_COMPLETE_SELECTED_SCOPE"
    return "UNKNOWN"


def _latest_point(points: list[dict[str, Any]]) -> str | None:
    values = [
        item.get("created_at")
        for item in points
        if isinstance(item.get("created_at"), str) and item.get("created_at")
    ]
    return max(values) if values else None


def _required_evidence(
    *,
    mechanism_observed: bool,
    retention_configuration_observed: bool,
) -> list[dict[str, Any]]:
    result = []
    for target, check in _REQUIRED_TARGETS:
        if target == "BACKUP_MECHANISM" and mechanism_observed:
            status = "OBSERVED"
            statement = "An authoritative PVE recovery-point record establishes the source mechanism for the selected scope."
        elif target == "BACKUP_RETENTION" and retention_configuration_observed:
            status = "PARTIAL"
            statement = "Retention configuration is observed, but effective retention assurance still requires retained-history/effectiveness evidence."
        else:
            status = "REQUIRED"
            statement = check
        result.append(
            {
                "target": target,
                "status": status,
                "statement": statement,
            }
        )
    return result


def _asset(
    guest: dict[str, Any],
    *,
    source: dict[str, Any],
    source_id: str,
    node: str,
    storages: dict[str, dict[str, Any]],
    coverage: list[dict[str, Any]],
    points: list[dict[str, Any]],
    guest_inventory_status: str,
) -> dict[str, Any]:
    vmid = guest["vmid"]
    recovery_status = _recovery_state(coverage)
    mechanisms = _mechanism_evidence(source_id, node, coverage)
    retention = _retention_context(coverage, storages)
    retention_observed = any(item["configuration_status"] == "OBSERVED" for item in retention)
    latest = _latest_point(points)

    if recovery_status == "OBSERVED":
        basis = ["AUTHORITATIVE_RECOVERY_POINT_OBSERVED"]
        statement = (
            "At least one authoritative PVE recovery-point artifact is observed for this VM in the selected source scope. "
            "This strengthens mechanism/recovery-point evidence but does not establish complete protection quality."
        )
    elif recovery_status == "NOT_OBSERVED_IN_COMPLETE_SELECTED_SCOPE":
        basis = ["COMPLETE_SELECTED_SOURCE_SCOPE_NO_RECOVERY_POINT_OBSERVED"]
        statement = (
            "No recovery point is observed for this VM in the complete selected PVE storage scope. "
            "This scoped negative evidence is not universal backup absence and is not classified as UNPROTECTED."
        )
    else:
        basis = ["SELECTED_SOURCE_SCOPE_INCOMPLETE_OR_UNKNOWN"]
        statement = (
            "Selected PVE recovery-point evidence is incomplete or unknown for this VM. No absence or protection claim is made."
        )

    return {
        "asset_id": f"backup-asset:proxmox-ve:{source_id}:vm:{vmid}",
        "asset_type": ASSET_TYPE,
        "subject": {
            "system": "proxmox_ve",
            "source_id": source_id,
            "kind": "VirtualMachine",
            "node": guest.get("node") or node,
            "vmid": vmid,
            "guest_type": guest.get("guest_type") or "UNKNOWN",
            "guest_status": guest.get("status") or "UNKNOWN",
        },
        "existence": "PRESENT",
        "observation_status": "COMPLETE" if guest_inventory_status == "COMPLETE" else "PARTIAL",
        "freshness": "UNKNOWN",
        "source_context": {
            "source_type": "PROXMOX_VE",
            "source_id": source_id,
            "source_artifact_version": source.get("proxmox_ve_backup_evidence_version"),
            "source_status": source.get("source", {}).get("status"),
            "source_generated_at": source.get("generated_at"),
            "selected_storage_scopes": [
                {
                    "node": item.get("node"),
                    "storage_id": item.get("storage_id"),
                    "status": (
                        "COMPLETE"
                        if item.get("local_recovery_point_status")
                        in {"RECOVERY_POINT_OBSERVED", "NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE"}
                        else "UNKNOWN"
                    ),
                }
                for item in coverage
            ],
        },
        "assurance": {
            "protection_status": "UNKNOWN",
            "recovery_point_status": recovery_status,
            "recovery_point_count": len(points),
            "latest_recovery_point_at": latest,
            "backup_mechanism_status": "OBSERVED" if mechanisms else "UNKNOWN",
            "backup_mechanisms": mechanisms,
            "retention_context": retention,
            "last_successful_backup_status": "UNKNOWN",
            "integrity_verification_status": "UNKNOWN",
            "restore_verification_status": "UNKNOWN",
            "failure_domain_status": "UNKNOWN",
            "scheduled_protection_status": "UNKNOWN",
            "rpo_status": "UNKNOWN",
            "rto_status": "RTO_UNKNOWN",
            "basis": basis,
            "statement": statement,
        },
        "required_evidence": _required_evidence(
            mechanism_observed=bool(mechanisms),
            retention_configuration_observed=retention_observed,
        ),
        "source_recovery_point_ids": [
            item["recovery_point_id"]
            for item in points
            if isinstance(item.get("recovery_point_id"), str) and item.get("recovery_point_id")
        ],
    }


def build_vm_backup_assurance(
    source_artifact: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    source = deepcopy(source_artifact)
    if source.get("proxmox_ve_backup_evidence_version") != SOURCE_ARTIFACT_VERSION:
        raise ValueError("unsupported Proxmox VE backup evidence version")
    if source.get("mutation_allowed") is not False:
        raise ValueError("source artifact must be read-only evidence")

    source_meta = source.get("source", {})
    source_id = str(source_meta.get("source_id") or "")
    node = str(source_meta.get("node") or "")
    if not source_id or not node:
        raise ValueError("source artifact must identify source_id and node")

    now = now or datetime.now(timezone.utc)
    guest_inventory_status = _observation_status(source, "GET_GUEST_RESOURCES")
    source_status = source_meta.get("status")
    if source_status not in {"COMPLETE", "PARTIAL", "FAILED_TO_OBSERVE"}:
        source_status = "FAILED_TO_OBSERVE"

    coverage_index = _coverage_by_vmid(source)
    points_index = _points_by_vmid(source)
    storages = _storage_by_id(source)

    assets: list[dict[str, Any]] = []
    if guest_inventory_status == "COMPLETE":
        for guest in source.get("guests", []):
            vmid = guest.get("vmid")
            if isinstance(vmid, bool) or not isinstance(vmid, int):
                continue
            assets.append(
                _asset(
                    guest,
                    source=source,
                    source_id=source_id,
                    node=node,
                    storages=storages,
                    coverage=coverage_index.get(vmid, []),
                    points=points_index.get(vmid, []),
                    guest_inventory_status=guest_inventory_status,
                )
            )

    assets.sort(key=lambda item: item["subject"]["vmid"])

    recovery_observed = sum(
        item["assurance"]["recovery_point_status"] == "OBSERVED" for item in assets
    )
    scoped_negative = sum(
        item["assurance"]["recovery_point_status"] == "NOT_OBSERVED_IN_COMPLETE_SELECTED_SCOPE"
        for item in assets
    )
    source_unknown = sum(
        item["assurance"]["recovery_point_status"] == "UNKNOWN" for item in assets
    )
    mechanism_observed = sum(
        item["assurance"]["backup_mechanism_status"] == "OBSERVED" for item in assets
    )
    retention_config_observed = sum(
        any(
            retention["configuration_status"] == "OBSERVED"
            for retention in item["assurance"]["retention_context"]
        )
        for item in assets
    )

    unknowns = [
        {
            "code": "SOURCE_ARTIFACT_FRESHNESS_UNKNOWN",
            "subject": source_id,
            "statement": "The accepted PVE source artifact has no expiry/TTL contract in v0.1, so derived source freshness remains UNKNOWN.",
        },
        {
            "code": "OTHER_BACKUP_SOURCES_NOT_EVALUATED",
            "subject": None,
            "statement": "This slice evaluates only the supplied PVE source artifact. Source-scoped negative evidence must not be generalized to every possible backup source.",
        },
        {
            "code": "RESTORE_INTEGRITY_RPO_RTO_REMAIN_UNKNOWN",
            "subject": None,
            "statement": "Recovery-point evidence does not establish restore verification, integrity verification, RPO compliance, or RTO compliance.",
        },
    ]
    if source_status != "COMPLETE":
        unknowns.append(
            {
                "code": "PVE_SOURCE_NOT_COMPLETE",
                "subject": source_id,
                "statement": "The supplied PVE source artifact is not COMPLETE; derived negative or coverage conclusions remain bounded by the observed source records.",
            }
        )
    if guest_inventory_status != "COMPLETE":
        unknowns.append(
            {
                "code": "PVE_GUEST_INVENTORY_FAILED_TO_OBSERVE",
                "subject": source_id,
                "statement": "Current PVE guest inventory was not completely observed, so VM asset existence cannot be exhaustively derived in this slice.",
            }
        )

    return {
        "vm_backup_assurance_version": VM_BACKUP_ASSURANCE_VERSION,
        "generated_at": _rfc3339(now),
        "mutation_allowed": False,
        "scope": {
            "asset_type": ASSET_TYPE,
            "derived_only": True,
            "source_neutral_assurance": True,
            "kubernetes_pvc_assurance_modified": False,
        },
        "source_status": {
            "overall": source_status,
            "source_type": "PROXMOX_VE",
            "source_id": source_id,
            "source_artifact_version": source.get("proxmox_ve_backup_evidence_version"),
            "source_generated_at": source.get("generated_at"),
            "source_freshness": "UNKNOWN",
            "guest_inventory": guest_inventory_status,
        },
        "summary": {
            "assets_total": len(assets),
            "recovery_point_observed": recovery_observed,
            "scoped_negative_recovery_point": scoped_negative,
            "recovery_point_unknown": source_unknown,
            "backup_mechanism_observed": mechanism_observed,
            "retention_configuration_observed": retention_config_observed,
            "protection_unknown": len(assets),
            "restore_verification_unknown": len(assets),
            "integrity_verification_unknown": len(assets),
            "rpo_unknown": len(assets),
            "rto_unknown": len(assets),
            "unprotected_claims": 0,
            "authoritative_source_artifacts_consumed": 1,
            "kubernetes_pvc_assets_modified": 0,
        },
        "assets": assets,
        "unknowns": unknowns,
        "caveats": [
            "Observed recovery-point presence is stronger than capability/configuration evidence but is not complete protection assurance.",
            "A complete selected PVE storage scope with no recovery point is scoped negative evidence, not universal UNPROTECTED status.",
            "PVE archive protection flags are not consumed as platform protection classification.",
            "VM assets remain separate from Kubernetes PVC assets because no accepted VMID-to-PVC identity relation exists.",
            "Future PBS evidence must enter through a separate source adapter with explicit provenance while preserving this common assurance model.",
        ],
    }


def render_vm_backup_assurance_markdown(artifact: dict[str, Any]) -> str:
    lines = [
        "# Backup and Recovery Assurance — Virtual Machines",
        "",
        f"Generated: `{artifact['generated_at']}`",
        "Mutation allowed: `false`",
        f"Source: `{artifact['source_status']['source_type']}/{artifact['source_status']['source_id']}`",
        f"Source status: `{artifact['source_status']['overall']}`",
        f"Source freshness: `{artifact['source_status']['source_freshness']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in artifact["summary"].items():
        lines.append(f"- {key}: {value}")

    lines += ["", "## VM assurance", ""]
    if not artifact["assets"]:
        lines.append("- No current VM assets could be derived from the supplied source artifact.")
    for item in artifact["assets"]:
        subject = item["subject"]
        assurance = item["assurance"]
        lines.append(
            f"- VMID {subject['vmid']} node={subject['node']} "
            f"recovery_point={assurance['recovery_point_status']} "
            f"count={assurance['recovery_point_count']} "
            f"latest={assurance['latest_recovery_point_at'] or 'unknown'} "
            f"mechanism={assurance['backup_mechanism_status']} "
            f"protection={assurance['protection_status']}"
        )

    lines += [
        "",
        "## Trust boundary",
        "",
        "Recovery-point evidence may establish source mechanism and an observed recovery point, but protection, restore verification, integrity, RPO, and RTO remain UNKNOWN until stronger authoritative evidence is integrated.",
        "",
        "No VMID-to-Kubernetes-PVC relation is inferred by this artifact.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Derive source-neutral VM backup assurance from accepted Proxmox VE backup evidence."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path, required=True)
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    artifact = build_vm_backup_assurance(source)
    atomic_write_json(args.out, artifact)
    atomic_write_text(args.summary_out, render_vm_backup_assurance_markdown(artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
