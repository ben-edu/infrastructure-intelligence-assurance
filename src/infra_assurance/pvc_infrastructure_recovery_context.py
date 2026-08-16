from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import atomic_write_json, atomic_write_text

CONTEXT_VERSION = "0.1"
FOUNDATION_VERSION = "0.1"
RELATIONSHIP_EVIDENCE_VERSION = "0.1"
REQUIRED_VM_ASSURANCE_VERSION = "0.2"
ASSET_TYPE = "KUBERNETES_PVC"
RELATIONSHIP_SOURCE_TYPE = "BOUNDED_KUBERNETES_PVE_RELATIONSHIP_OBSERVATION"

_OBSERVATION_STATUSES = {"OBSERVED", "UNKNOWN", "FAILED_TO_OBSERVE"}
_RECOVERY_POINT_ID = re.compile(r"^pve-rp-[a-f0-9]{24}$")
_TASK_RESULT_ID = re.compile(r"^pve-backup-task:[a-f0-9]{24}$")


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _require_status(value: Any, field: str) -> str:
    if value not in _OBSERVATION_STATUSES:
        raise ValueError(f"{field} has unsupported observation status")
    return str(value)


def _validate_foundation(
    artifact: dict[str, Any],
) -> tuple[str, dict[str, dict[str, Any]]]:
    if artifact.get("backup_assurance_version") != FOUNDATION_VERSION:
        raise ValueError("unsupported PVC backup assurance foundation version")
    if artifact.get("mutation_allowed") is not False:
        raise ValueError("PVC foundation must be read-only")

    cluster_id = _require_string(artifact.get("cluster_id"), "foundation.cluster_id")
    scope = artifact.get("scope")
    if not isinstance(scope, dict) or scope.get("asset_type") != ASSET_TYPE:
        raise ValueError("foundation scope must identify KUBERNETES_PVC")

    assets = artifact.get("assets")
    if not isinstance(assets, list):
        raise ValueError("foundation assets must be a list")

    index: dict[str, dict[str, Any]] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError("foundation asset must be an object")
        asset_id = _require_string(asset.get("asset_id"), "foundation.asset_id")
        if asset_id in index:
            raise ValueError("duplicate PVC foundation asset_id")
        if asset.get("asset_type") != ASSET_TYPE:
            raise ValueError("foundation asset_type must be KUBERNETES_PVC")

        subject = asset.get("subject")
        if not isinstance(subject, dict):
            raise ValueError("foundation asset is missing subject")
        if subject.get("kind") != "PersistentVolumeClaim":
            raise ValueError("foundation subject must be a PersistentVolumeClaim")
        if subject.get("cluster") != cluster_id:
            raise ValueError("foundation subject cluster does not match foundation cluster")
        _require_string(subject.get("namespace"), "foundation.subject.namespace")
        _require_string(subject.get("name"), "foundation.subject.name")
        index[asset_id] = asset

    return cluster_id, index


def _validate_relationship_evidence(
    artifact: dict[str, Any],
    *,
    cluster_id: str,
    foundation_index: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, dict[str, Any]]]:
    if (
        artifact.get("pvc_infrastructure_relationship_evidence_version")
        != RELATIONSHIP_EVIDENCE_VERSION
    ):
        raise ValueError("unsupported PVC infrastructure relationship evidence version")
    if artifact.get("mutation_allowed") is not False:
        raise ValueError("PVC relationship evidence must be read-only")
    if artifact.get("cluster_id") != cluster_id:
        raise ValueError("PVC relationship evidence cluster does not match foundation")

    source = artifact.get("source")
    if not isinstance(source, dict):
        raise ValueError("PVC relationship evidence is missing source metadata")
    if source.get("type") != RELATIONSHIP_SOURCE_TYPE:
        raise ValueError("unsupported PVC relationship evidence source type")
    source_status = source.get("status")
    if source_status not in {"COMPLETE", "PARTIAL", "FAILED_TO_OBSERVE"}:
        raise ValueError("unsupported PVC relationship evidence source status")
    _require_string(source.get("source_id"), "relationship.source.source_id")

    assets = artifact.get("assets")
    if not isinstance(assets, list):
        raise ValueError("PVC relationship evidence assets must be a list")

    index: dict[str, dict[str, Any]] = {}
    for item in assets:
        if not isinstance(item, dict):
            raise ValueError("PVC relationship evidence asset must be an object")
        asset_id = _require_string(item.get("asset_id"), "relationship.asset_id")
        if asset_id in index:
            raise ValueError("duplicate PVC relationship asset_id")
        if asset_id not in foundation_index:
            raise ValueError("PVC relationship asset is not present in foundation")

        subject = item.get("subject")
        if not isinstance(subject, dict):
            raise ValueError("PVC relationship asset is missing subject")
        foundation_subject = foundation_index[asset_id].get("subject")
        if subject != foundation_subject:
            raise ValueError("PVC relationship subject does not match foundation subject")

        _require_status(item.get("observation_status"), "relationship.observation_status")

        storage = item.get("storage_relationship")
        if not isinstance(storage, dict):
            raise ValueError("PVC relationship asset is missing storage_relationship")
        storage_status = _require_status(
            storage.get("status"), "relationship.storage_relationship.status"
        )
        if storage_status == "OBSERVED":
            if storage.get("pvc_phase") != "Bound":
                raise ValueError("observed PVC storage relationship requires Bound phase")
            for key in ("storage_class", "pv_name", "storage_node"):
                _require_string(storage.get(key), f"relationship.storage_relationship.{key}")

        workload = item.get("workload_context")
        if not isinstance(workload, dict):
            raise ValueError("PVC relationship asset is missing workload_context")
        if workload.get("status") not in {
            "DIRECT_CONTROLLER_REFERENCES_OBSERVED",
            "NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED",
            "UNKNOWN",
            "FAILED_TO_OBSERVE",
        }:
            raise ValueError("unsupported PVC workload_context status")
        related = workload.get("related_workloads")
        if not isinstance(related, list):
            raise ValueError("PVC workload_context related_workloads must be a list")

        mapping = item.get("node_vm_mapping")
        if not isinstance(mapping, dict):
            raise ValueError("PVC relationship asset is missing node_vm_mapping")
        mapping_status = _require_status(
            mapping.get("status"), "relationship.node_vm_mapping.status"
        )
        if mapping_status == "OBSERVED":
            if storage_status != "OBSERVED":
                raise ValueError(
                    "node-to-VM mapping cannot be OBSERVED when storage relationship is not OBSERVED"
                )
            kubernetes_node = _require_string(
                mapping.get("kubernetes_node"),
                "relationship.node_vm_mapping.kubernetes_node",
            )
            if kubernetes_node != storage.get("storage_node"):
                raise ValueError("PVC storage node and node-to-VM mapping do not match")
            _require_string(
                mapping.get("pve_source_id"),
                "relationship.node_vm_mapping.pve_source_id",
            )
            _require_string(
                mapping.get("pve_node"), "relationship.node_vm_mapping.pve_node"
            )
            vmid = mapping.get("vmid")
            if isinstance(vmid, bool) or not isinstance(vmid, int) or vmid < 1:
                raise ValueError("observed PVC node-to-VM mapping requires a numeric VMID")

        index[asset_id] = item

    if set(index) != set(foundation_index):
        raise ValueError("PVC relationship asset identities must exactly match foundation assets")

    return str(source_status), index


def _validate_vm_assurance(
    artifact: dict[str, Any],
) -> tuple[str, str, dict[int, dict[str, Any]]]:
    if artifact.get("vm_backup_assurance_version") != REQUIRED_VM_ASSURANCE_VERSION:
        raise ValueError("unsupported VM Backup Assurance version")
    if artifact.get("mutation_allowed") is not False:
        raise ValueError("VM Backup Assurance must be read-only evidence")

    source = artifact.get("source_status")
    if not isinstance(source, dict):
        raise ValueError("VM Backup Assurance is missing source status")
    source_id = _require_string(source.get("source_id"), "vm_assurance.source_id")
    overall = source.get("overall")
    if overall not in {"COMPLETE", "PARTIAL", "FAILED_TO_OBSERVE"}:
        raise ValueError("unsupported VM Backup Assurance overall source status")

    integration = artifact.get("last_successful_backup_integration")
    if not isinstance(integration, dict):
        raise ValueError("VM Backup Assurance is missing last-successful-backup integration")
    if integration.get("mode") != "STRICT_CORRELATION_ONLY":
        raise ValueError("VM Backup Assurance integration mode is not accepted")
    if integration.get("source_id") != source_id:
        raise ValueError("VM Backup Assurance source identities do not match")
    integration_status = integration.get("source_status")
    if integration_status not in {"COMPLETE", "FAILED_TO_OBSERVE"}:
        raise ValueError("unsupported VM last-successful-backup source status")

    index: dict[int, dict[str, Any]] = {}
    for asset in artifact.get("assets", []):
        if not isinstance(asset, dict):
            continue
        subject = asset.get("subject", {})
        vmid = subject.get("vmid")
        if isinstance(vmid, bool) or not isinstance(vmid, int):
            continue
        if vmid in index:
            raise ValueError("duplicate VMID in VM Backup Assurance")
        if subject.get("source_id") != source_id:
            raise ValueError("VM asset source identity does not match VM assurance source")
        index[vmid] = asset

    usable_status = (
        "COMPLETE"
        if overall == "COMPLETE" and integration_status == "COMPLETE"
        else "INCOMPLETE"
    )
    return source_id, usable_status, index


def _validated_vm_last_success(
    assurance: dict[str, Any],
    *,
    vm_source_id: str,
) -> tuple[str, str | None, dict[str, Any] | None]:
    status = assurance.get("last_successful_backup_status", "UNKNOWN")
    if status == "UNKNOWN":
        if assurance.get("last_successful_backup_at") is not None:
            raise ValueError("UNKNOWN VM last-successful-backup must not carry a timestamp")
        if assurance.get("last_successful_backup_evidence") is not None:
            raise ValueError("UNKNOWN VM last-successful-backup must not carry evidence")
        return "UNKNOWN", None, None
    if status != "OBSERVED":
        raise ValueError("unsupported VM last-successful-backup status")

    observed_at = _require_string(
        assurance.get("last_successful_backup_at"), "last_successful_backup_at"
    )
    evidence = assurance.get("last_successful_backup_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("OBSERVED VM last-successful-backup requires strict evidence")
    if evidence.get("source_type") != "PROXMOX_VE_VZDUMP_TASK_RESULT":
        raise ValueError("OBSERVED VM last-successful-backup has unsupported evidence source")
    if evidence.get("source_id") != vm_source_id:
        raise ValueError("OBSERVED VM last-successful-backup evidence source does not match VM source")

    recovery_point_id = _require_string(
        evidence.get("recovery_point_id"),
        "last_successful_backup_evidence.recovery_point_id",
    )
    task_result_id = _require_string(
        evidence.get("task_result_id"),
        "last_successful_backup_evidence.task_result_id",
    )
    if not _RECOVERY_POINT_ID.fullmatch(recovery_point_id):
        raise ValueError("OBSERVED VM last-successful-backup has invalid recovery point ID")
    if not _TASK_RESULT_ID.fullmatch(task_result_id):
        raise ValueError("OBSERVED VM last-successful-backup has invalid task result ID")
    if evidence.get("basis") != ["STRICT_SUCCESS_TASK_MATCH"]:
        raise ValueError("OBSERVED VM last-successful-backup requires STRICT_SUCCESS_TASK_MATCH")

    return (
        "OBSERVED",
        observed_at,
        {
            "source_type": "PROXMOX_VE_VZDUMP_TASK_RESULT",
            "source_id": vm_source_id,
            "recovery_point_id": recovery_point_id,
            "task_result_id": task_result_id,
            "basis": ["STRICT_SUCCESS_TASK_MATCH"],
        },
    )


def _assurance_unknown() -> dict[str, Any]:
    return {
        "protection_status": "UNKNOWN",
        "backup_freshness_status": "UNKNOWN",
        "backup_mechanism_status": "UNKNOWN",
        "retention_effectiveness_status": "UNKNOWN",
        "failure_domain_status": "UNKNOWN",
        "integrity_verification_status": "UNKNOWN",
        "restore_verification_status": "UNKNOWN",
        "rpo_status": "UNKNOWN",
        "rto_status": "RTO_UNKNOWN",
        "basis": ["APPLICATION_AWARE_BACKUP_EVIDENCE_NOT_INTEGRATED"],
        "statement": (
            "Observed PVC infrastructure recovery context is not application-consistent "
            "backup evidence. Protection, retention, failure-domain independence, integrity, "
            "restore, RPO, and RTO remain unknown."
        ),
    }


def _required_evidence() -> list[dict[str, Any]]:
    targets = (
        "BACKUP_MECHANISM",
        "BACKUP_EXECUTION_RESULT",
        "BACKUP_RETENTION",
        "BACKUP_FAILURE_DOMAIN",
        "BACKUP_INTEGRITY_VERIFICATION",
        "RESTORE_TEST",
        "RPO_TARGET_AND_RESULT",
        "RTO_TARGET_AND_RESULT",
    )
    return [
        {
            "target": target,
            "status": "REQUIRED",
            "statement": f"Observe authoritative evidence for {target.lower()}.",
        }
        for target in targets
    ]


def _derive_asset(
    foundation_asset: dict[str, Any],
    relationship: dict[str, Any],
    *,
    relationship_source_status: str,
    vm_source_id: str,
    vm_source_status: str,
    vm_index: dict[int, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    storage = relationship["storage_relationship"]
    mapping = relationship["node_vm_mapping"]
    edge_statuses = (
        relationship["observation_status"],
        storage["status"],
        mapping["status"],
    )

    if mapping.get("status") == "OBSERVED" and mapping.get("pve_source_id") != vm_source_id:
        raise ValueError("PVC node-to-VM mapping PVE source does not match VM assurance source")

    vmid = mapping.get("vmid") if mapping.get("status") == "OBSERVED" else None
    vm_asset = vm_index.get(vmid) if isinstance(vmid, int) else None
    vm_assurance = vm_asset.get("assurance", {}) if isinstance(vm_asset, dict) else {}
    if vm_asset is None:
        vm_last_status, vm_last_at, vm_last_evidence = "UNKNOWN", None, None
    else:
        vm_last_status, vm_last_at, vm_last_evidence = _validated_vm_last_success(
            vm_assurance, vm_source_id=vm_source_id
        )

    if "FAILED_TO_OBSERVE" in edge_statuses:
        recovery_status = "FAILED_TO_OBSERVE"
    elif any(status != "OBSERVED" for status in edge_statuses):
        recovery_status = "UNKNOWN"
    elif relationship_source_status != "COMPLETE" or vm_source_status != "COMPLETE":
        recovery_status = "UNKNOWN"
    elif vm_asset is None or vm_last_status != "OBSERVED":
        recovery_status = "UNKNOWN"
    else:
        recovery_status = "OBSERVED"

    unknown = None
    if recovery_status != "OBSERVED":
        unknown = {
            "code": "PVC_INFRASTRUCTURE_RECOVERY_CONTEXT_NOT_ESTABLISHED",
            "subject": foundation_asset["asset_id"],
            "status": recovery_status,
            "statement": (
                "At least one required PVC infrastructure relationship observation failed."
                if recovery_status == "FAILED_TO_OBSERVE"
                else "The complete PVC storage-node/VM recovery chain is not established by current accepted evidence."
            ),
        }

    evidence_ids = [
        value
        for value in relationship.get("evidence_ids", [])
        if isinstance(value, str) and value
    ]
    foundation_evidence = foundation_asset.get("evidence_ids", [])
    evidence_ids.extend(
        value for value in foundation_evidence if isinstance(value, str) and value
    )
    evidence_ids = list(dict.fromkeys(evidence_ids))

    basis: list[str] = []
    if recovery_status == "OBSERVED":
        basis = [
            "PVC_FOUNDATION_ASSET_OBSERVED",
            "BOUND_PVC_STORAGE_NODE_OBSERVED",
            "KUBERNETES_NODE_TO_PVE_VMID_OBSERVED",
            "VM_LAST_SUCCESSFUL_BACKUP_OBSERVED",
        ]

    return (
        {
            "asset_id": foundation_asset["asset_id"],
            "asset_type": ASSET_TYPE,
            "subject": deepcopy(foundation_asset["subject"]),
            "foundation_context": {
                "freshness": foundation_asset.get("freshness", "UNKNOWN"),
                "storage": deepcopy(foundation_asset.get("storage", {})),
                "workload_context": deepcopy(relationship["workload_context"]),
            },
            "infrastructure_recovery": {
                "relationship_status": recovery_status,
                "storage_node": storage.get("storage_node"),
                "pve_source_id": mapping.get("pve_source_id"),
                "pve_node": mapping.get("pve_node"),
                "vmid": vmid,
                "underlying_vm_last_successful_backup_status": vm_last_status,
                "underlying_vm_last_successful_backup_at": vm_last_at,
                "underlying_vm_last_successful_backup_evidence": vm_last_evidence,
                "basis": basis,
                "evidence_ids": evidence_ids,
            },
            "assurance": _assurance_unknown(),
            "required_evidence": _required_evidence(),
        },
        unknown,
    )


def build_pvc_infrastructure_recovery_context(
    foundation: dict[str, Any],
    relationship_evidence: dict[str, Any],
    vm_backup_assurance: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    foundation_copy = deepcopy(foundation)
    relationship_copy = deepcopy(relationship_evidence)
    vm_copy = deepcopy(vm_backup_assurance)

    cluster_id, foundation_index = _validate_foundation(foundation_copy)
    relationship_source_status, relationship_index = _validate_relationship_evidence(
        relationship_copy,
        cluster_id=cluster_id,
        foundation_index=foundation_index,
    )
    vm_source_id, vm_source_status, vm_index = _validate_vm_assurance(vm_copy)

    assets: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for asset_id in sorted(foundation_index):
        derived, unknown = _derive_asset(
            foundation_index[asset_id],
            relationship_index[asset_id],
            relationship_source_status=relationship_source_status,
            vm_source_id=vm_source_id,
            vm_source_status=vm_source_status,
            vm_index=vm_index,
        )
        assets.append(derived)
        if unknown:
            unknowns.append(unknown)

    unknowns.extend(
        [
            {
                "code": "PVC_APPLICATION_AWARE_BACKUP_EVIDENCE_NOT_INTEGRATED",
                "subject": None,
                "status": "UNKNOWN",
                "statement": (
                    "Infrastructure recovery context does not establish application-consistent "
                    "backup protection, retention, integrity, restore, or failure-domain assurance."
                ),
            },
            {
                "code": "PVC_RPO_FRESHNESS_POLICY_NOT_ESTABLISHED",
                "subject": None,
                "status": "UNKNOWN",
                "statement": (
                    "No accepted PVC/application RPO or freshness target exists, so VM backup "
                    "timestamp age must not be classified as BACKUP_STALE or RPO_VIOLATION."
                ),
            },
        ]
    )

    recovery_counts = Counter(
        asset["infrastructure_recovery"]["relationship_status"] for asset in assets
    )
    workload_counts = Counter(
        asset["foundation_context"]["workload_context"].get("status", "UNKNOWN")
        for asset in assets
    )
    vm_observed = sum(
        asset["infrastructure_recovery"][
            "underlying_vm_last_successful_backup_status"
        ]
        == "OBSERVED"
        for asset in assets
    )
    total = len(assets)

    return {
        "pvc_infrastructure_recovery_context_version": CONTEXT_VERSION,
        "generated_at": _rfc3339(now or datetime.now(timezone.utc)),
        "mutation_allowed": False,
        "cluster_id": cluster_id,
        "scope": {
            "asset_type": ASSET_TYPE,
            "derived_only": True,
            "application_aware_backup_source_integrated": False,
        },
        "source_status": {
            "pvc_foundation": {
                "version": FOUNDATION_VERSION,
                "status": foundation_copy.get("source_status", {}).get("overall", "UNKNOWN"),
                "generated_at": foundation_copy.get("generated_at"),
            },
            "relationship_evidence": {
                "version": RELATIONSHIP_EVIDENCE_VERSION,
                "source_type": relationship_copy["source"]["type"],
                "source_id": relationship_copy["source"]["source_id"],
                "status": relationship_source_status,
                "generated_at": relationship_copy.get("generated_at"),
            },
            "vm_backup_assurance": {
                "version": REQUIRED_VM_ASSURANCE_VERSION,
                "source_id": vm_source_id,
                "status": vm_source_status,
                "generated_at": vm_copy.get("generated_at"),
                "integration_mode": vm_copy["last_successful_backup_integration"]["mode"],
                "freshness": vm_copy["last_successful_backup_integration"].get(
                    "source_freshness", "UNKNOWN"
                ),
            },
        },
        "assets": assets,
        "summary": {
            "assets_total": total,
            "direct_workload_reference_observed": workload_counts.get(
                "DIRECT_CONTROLLER_REFERENCES_OBSERVED", 0
            ),
            "direct_workload_reference_none_observed": workload_counts.get(
                "NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED", 0
            ),
            "infrastructure_recovery_observed": recovery_counts.get("OBSERVED", 0),
            "infrastructure_recovery_unknown": recovery_counts.get("UNKNOWN", 0),
            "infrastructure_recovery_failed_to_observe": recovery_counts.get(
                "FAILED_TO_OBSERVE", 0
            ),
            "underlying_vm_last_successful_backup_observed": vm_observed,
            "protection_unknown": total,
            "backup_freshness_unknown": total,
            "retention_effectiveness_unknown": total,
            "failure_domain_unknown": total,
            "integrity_verification_unknown": total,
            "restore_verification_unknown": total,
            "rpo_unknown": total,
            "rto_unknown": total,
            "unprotected_claims": 0,
            "backup_stale_claims": 0,
            "rpo_violation_claims": 0,
        },
        "unknowns": unknowns,
        "caveats": [
            "PVC infrastructure recovery context is not application-consistent or database-consistent backup evidence.",
            "A successful underlying VM backup does not prove application restore viability or data integrity.",
            "No direct controller reference observed is bounded relationship evidence only and is not an orphan classification.",
            "Timestamp age alone does not establish BACKUP_STALE or RPO_VIOLATION without an accepted target.",
            "UNKNOWN protection does not mean UNPROTECTED.",
        ],
    }


def render_pvc_infrastructure_recovery_markdown(artifact: dict[str, Any]) -> str:
    summary = artifact["summary"]
    lines = [
        "# PVC Infrastructure Recovery Context",
        "",
        f"Cluster: `{artifact['cluster_id']}`",
        f"Generated: `{artifact['generated_at']}`",
        "Mutation allowed: `false`",
        "Application-aware backup source integrated: `false`",
        "",
        "## Summary",
        "",
        f"- PVC assets: {summary['assets_total']}",
        f"- infrastructure recovery observed: {summary['infrastructure_recovery_observed']}",
        f"- infrastructure recovery unknown: {summary['infrastructure_recovery_unknown']}",
        f"- underlying VM last-successful-backup observed: {summary['underlying_vm_last_successful_backup_observed']}",
        f"- protection unknown: {summary['protection_unknown']}",
        f"- direct workload reference observed: {summary['direct_workload_reference_observed']}",
        f"- direct workload reference none observed: {summary['direct_workload_reference_none_observed']}",
        f"- unprotected claims: {summary['unprotected_claims']}",
        f"- backup stale claims: {summary['backup_stale_claims']}",
        f"- RPO violation claims: {summary['rpo_violation_claims']}",
        "",
        "## Assets",
        "",
    ]

    for asset in artifact["assets"]:
        subject = asset["subject"]
        recovery = asset["infrastructure_recovery"]
        workload = asset["foundation_context"]["workload_context"]
        lines.append(
            "- "
            + f"{subject['namespace']}/{subject['name']}"
            + f" workload_context={workload.get('status', 'UNKNOWN')}"
            + f" node={recovery.get('storage_node') or 'unknown'}"
            + f" vmid={recovery.get('vmid') if recovery.get('vmid') is not None else 'unknown'}"
            + f" infrastructure_recovery={recovery['relationship_status']}"
            + f" vm_last_successful_backup={recovery['underlying_vm_last_successful_backup_status']}"
            + f" latest={recovery.get('underlying_vm_last_successful_backup_at') or 'unknown'}"
            + " protection=UNKNOWN"
        )

    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "Observed infrastructure recovery is VM-level recovery context only; it is not application-consistent or database-consistent backup protection.",
            "Retention, failure-domain independence, integrity, restore verification, RPO, and RTO remain unknown.",
            "No direct controller reference observed is not an orphan classification.",
            "Timestamp age alone does not establish BACKUP_STALE or RPO_VIOLATION.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Derive bounded PVC infrastructure recovery context from PVC foundation, "
            "relationship evidence, and accepted VM backup evidence."
        )
    )
    parser.add_argument("--foundation", required=True, type=Path)
    parser.add_argument("--relationship-evidence", required=True, type=Path)
    parser.add_argument("--vm-assurance", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--summary-out", required=True, type=Path)
    args = parser.parse_args(argv)

    foundation = json.loads(args.foundation.read_text(encoding="utf-8"))
    relationship = json.loads(args.relationship_evidence.read_text(encoding="utf-8"))
    vm_assurance = json.loads(args.vm_assurance.read_text(encoding="utf-8"))
    result = build_pvc_infrastructure_recovery_context(
        foundation,
        relationship,
        vm_assurance,
    )
    atomic_write_json(args.out, result)
    atomic_write_text(
        args.summary_out,
        render_pvc_infrastructure_recovery_markdown(result),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
