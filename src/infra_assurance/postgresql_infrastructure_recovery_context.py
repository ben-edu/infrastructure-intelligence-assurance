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
RELATIONSHIP_EVIDENCE_VERSION = "0.1"
REQUIRED_VM_ASSURANCE_VERSION = "0.2"
DATABASE_ENGINE = "POSTGRESQL"
RELATIONSHIP_SOURCE_TYPE = "BOUNDED_KUBERNETES_PVE_RELATIONSHIP_OBSERVATION"

_OBSERVATION_STATUSES = {"OBSERVED", "UNKNOWN", "FAILED_TO_OBSERVE"}
_RECOVERY_POINT_ID = re.compile(r"^pve-rp-[a-f0-9]{24}$")
_TASK_RESULT_ID = re.compile(r"^pve-backup-task:[a-f0-9]{24}$")


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _require_observation_status(value: Any, field: str) -> str:
    if value not in _OBSERVATION_STATUSES:
        raise ValueError(f"{field} has unsupported observation status")
    return str(value)


def _validate_relationship_evidence(
    artifact: dict[str, Any],
) -> tuple[str, str, list[dict[str, Any]]]:
    if (
        artifact.get("postgresql_infrastructure_relationship_evidence_version")
        != RELATIONSHIP_EVIDENCE_VERSION
    ):
        raise ValueError("unsupported PostgreSQL infrastructure relationship evidence version")
    if artifact.get("mutation_allowed") is not False:
        raise ValueError("relationship evidence must be read-only")

    cluster_id = _require_nonempty_string(artifact.get("cluster_id"), "cluster_id")
    source = artifact.get("source")
    if not isinstance(source, dict):
        raise ValueError("relationship evidence is missing source metadata")
    if source.get("type") != RELATIONSHIP_SOURCE_TYPE:
        raise ValueError("unsupported relationship evidence source type")
    source_status = source.get("status")
    if source_status not in {"COMPLETE", "PARTIAL", "FAILED_TO_OBSERVE"}:
        raise ValueError("unsupported relationship evidence source status")
    _require_nonempty_string(source.get("source_id"), "source.source_id")

    instances = artifact.get("instances")
    if not isinstance(instances, list):
        raise ValueError("relationship evidence instances must be a list")

    seen: set[str] = set()
    for item in instances:
        if not isinstance(item, dict):
            raise ValueError("relationship evidence instance must be an object")
        instance_id = _require_nonempty_string(item.get("instance_id"), "instance_id")
        if instance_id in seen:
            raise ValueError("duplicate PostgreSQL infrastructure relationship instance_id")
        seen.add(instance_id)

        subject = item.get("subject")
        if not isinstance(subject, dict):
            raise ValueError("relationship instance is missing subject")
        if subject.get("system") != "kubernetes":
            raise ValueError("only Kubernetes PostgreSQL subjects are supported")
        if subject.get("cluster") != cluster_id:
            raise ValueError("relationship subject cluster does not match artifact cluster")
        if subject.get("database_engine") != DATABASE_ENGINE:
            raise ValueError("relationship subject must identify POSTGRESQL")
        for key in ("namespace", "workload_kind", "workload_name"):
            _require_nonempty_string(subject.get(key), f"subject.{key}")

        _require_observation_status(
            item.get("instance_observation_status"),
            "instance_observation_status",
        )

        persistence = item.get("persistence")
        if not isinstance(persistence, dict):
            raise ValueError("relationship instance is missing persistence")
        persistence_status = _require_observation_status(
            persistence.get("status"),
            "persistence.status",
        )
        if persistence_status == "OBSERVED":
            for key in ("pvc_name", "pv_name", "storage_class", "storage_node"):
                _require_nonempty_string(persistence.get(key), f"persistence.{key}")

        mapping = item.get("node_vm_mapping")
        if not isinstance(mapping, dict):
            raise ValueError("relationship instance is missing node_vm_mapping")
        mapping_status = _require_observation_status(
            mapping.get("status"),
            "node_vm_mapping.status",
        )
        if mapping_status == "OBSERVED":
            kubernetes_node = _require_nonempty_string(
                mapping.get("kubernetes_node"),
                "node_vm_mapping.kubernetes_node",
            )
            if (
                persistence_status == "OBSERVED"
                and kubernetes_node != persistence.get("storage_node")
            ):
                raise ValueError(
                    "observed Kubernetes storage node and node-to-VM mapping do not match"
                )
            _require_nonempty_string(
                mapping.get("pve_source_id"),
                "node_vm_mapping.pve_source_id",
            )
            _require_nonempty_string(
                mapping.get("pve_node"),
                "node_vm_mapping.pve_node",
            )
            vmid = mapping.get("vmid")
            if isinstance(vmid, bool) or not isinstance(vmid, int) or vmid < 1:
                raise ValueError("observed node-to-VM mapping requires a numeric VMID")

    return cluster_id, str(source_status), instances


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
    source_id = _require_nonempty_string(
        source.get("source_id"),
        "vm_assurance.source_id",
    )
    overall = source.get("overall")
    if overall not in {"COMPLETE", "PARTIAL", "FAILED_TO_OBSERVE"}:
        raise ValueError("unsupported VM Backup Assurance overall source status")

    integration = artifact.get("last_successful_backup_integration")
    if not isinstance(integration, dict):
        raise ValueError(
            "VM Backup Assurance is missing last-successful-backup integration"
        )
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
            raise ValueError(
                "VM asset source identity does not match VM assurance source"
            )
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

    observed_at = _require_nonempty_string(
        assurance.get("last_successful_backup_at"),
        "last_successful_backup_at",
    )
    evidence = assurance.get("last_successful_backup_evidence")
    if not isinstance(evidence, dict):
        raise ValueError("OBSERVED VM last-successful-backup requires strict evidence")
    if evidence.get("source_type") != "PROXMOX_VE_VZDUMP_TASK_RESULT":
        raise ValueError("OBSERVED VM last-successful-backup has unsupported evidence source")
    if evidence.get("source_id") != vm_source_id:
        raise ValueError("OBSERVED VM last-successful-backup evidence source does not match VM source")

    recovery_point_id = _require_nonempty_string(
        evidence.get("recovery_point_id"),
        "last_successful_backup_evidence.recovery_point_id",
    )
    if not _RECOVERY_POINT_ID.fullmatch(recovery_point_id):
        raise ValueError("OBSERVED VM last-successful-backup has invalid recovery point ID")

    task_result_id = _require_nonempty_string(
        evidence.get("task_result_id"),
        "last_successful_backup_evidence.task_result_id",
    )
    if not _TASK_RESULT_ID.fullmatch(task_result_id):
        raise ValueError("OBSERVED VM last-successful-backup has invalid task result ID")

    if evidence.get("basis") != ["STRICT_SUCCESS_TASK_MATCH"]:
        raise ValueError("OBSERVED VM last-successful-backup requires STRICT_SUCCESS_TASK_MATCH")

    safe_evidence = {
        "source_type": "PROXMOX_VE_VZDUMP_TASK_RESULT",
        "source_id": vm_source_id,
        "recovery_point_id": recovery_point_id,
        "task_result_id": task_result_id,
        "basis": ["STRICT_SUCCESS_TASK_MATCH"],
    }
    return "OBSERVED", observed_at, safe_evidence


def _postgresql_assurance_unknown() -> dict[str, Any]:
    return {
        "protection_status": "UNKNOWN",
        "backup_mechanism_status": "UNKNOWN",
        "backup_execution_status": "UNKNOWN",
        "backup_artifact_location_status": "UNKNOWN",
        "retention_effectiveness_status": "UNKNOWN",
        "restore_verification_status": "UNKNOWN",
        "integrity_verification_status": "UNKNOWN",
        "rpo_status": "UNKNOWN",
        "rto_status": "RTO_UNKNOWN",
        "basis": ["DATABASE_AWARE_BACKUP_SOURCE_NOT_INTEGRATED"],
        "statement": (
            "Observed infrastructure recovery context is not PostgreSQL-consistent "
            "backup evidence. Database-aware protection, execution, artifact, retention, "
            "restore, integrity, RPO, and RTO remain unknown."
        ),
    }


def _required_postgresql_evidence() -> list[dict[str, Any]]:
    return [
        {
            "target": "POSTGRESQL_BACKUP_MECHANISM",
            "status": "REQUIRED",
            "statement": "Observe an authoritative PostgreSQL-aware backup mechanism.",
        },
        {
            "target": "POSTGRESQL_BACKUP_EXECUTION_RESULT",
            "status": "REQUIRED",
            "statement": (
                "Observe authoritative PostgreSQL-aware backup execution and result evidence."
            ),
        },
        {
            "target": "POSTGRESQL_BACKUP_ARTIFACT_LOCATION",
            "status": "REQUIRED",
            "statement": (
                "Observe where PostgreSQL recovery artifacts are stored without exposing "
                "sensitive connection data."
            ),
        },
        {
            "target": "POSTGRESQL_RETENTION_EFFECTIVENESS",
            "status": "REQUIRED",
            "statement": (
                "Observe effective retention and retained PostgreSQL recovery points."
            ),
        },
        {
            "target": "POSTGRESQL_RESTORE_VERIFICATION",
            "status": "REQUIRED",
            "statement": (
                "Observe an actual PostgreSQL restore test and application/data recovery result."
            ),
        },
        {
            "target": "POSTGRESQL_INTEGRITY_VERIFICATION",
            "status": "REQUIRED",
            "statement": "Observe authoritative PostgreSQL backup integrity verification.",
        },
        {
            "target": "POSTGRESQL_RPO_TARGET_AND_RESULT",
            "status": "REQUIRED",
            "statement": (
                "Establish an accepted PostgreSQL RPO target before evaluating timestamp age."
            ),
        },
        {
            "target": "POSTGRESQL_RTO_TARGET_AND_RESULT",
            "status": "REQUIRED",
            "statement": (
                "Establish an accepted PostgreSQL RTO target and measured restore evidence."
            ),
        },
    ]


def _derive_instance(
    item: dict[str, Any],
    *,
    relationship_source_status: str,
    vm_source_id: str,
    vm_source_status: str,
    vm_index: dict[int, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    persistence = item["persistence"]
    mapping = item["node_vm_mapping"]
    edge_statuses = (
        item["instance_observation_status"],
        persistence["status"],
        mapping["status"],
    )

    if (
        mapping.get("status") == "OBSERVED"
        and mapping.get("pve_source_id") != vm_source_id
    ):
        raise ValueError(
            "node-to-VM mapping PVE source does not match VM assurance source"
        )

    vmid = mapping.get("vmid") if mapping.get("status") == "OBSERVED" else None
    vm_asset = vm_index.get(vmid) if isinstance(vmid, int) else None
    vm_assurance = (
        vm_asset.get("assurance", {}) if isinstance(vm_asset, dict) else {}
    )
    if vm_asset is None:
        vm_last_status, vm_last_at, vm_last_evidence = "UNKNOWN", None, None
    else:
        vm_last_status, vm_last_at, vm_last_evidence = _validated_vm_last_success(
            vm_assurance,
            vm_source_id=vm_source_id,
        )

    if "FAILED_TO_OBSERVE" in edge_statuses:
        recovery_status = "FAILED_TO_OBSERVE"
    elif any(status != "OBSERVED" for status in edge_statuses):
        recovery_status = "UNKNOWN"
    elif relationship_source_status != "COMPLETE" or vm_source_status != "COMPLETE":
        recovery_status = "UNKNOWN"
    elif vm_asset is None:
        recovery_status = "UNKNOWN"
    elif vm_last_status == "OBSERVED":
        recovery_status = "OBSERVED"
    else:
        recovery_status = "UNKNOWN"

    unknown = None
    if recovery_status != "OBSERVED":
        reason = {
            "FAILED_TO_OBSERVE": (
                "At least one required infrastructure relationship observation failed."
            ),
            "UNKNOWN": (
                "The complete infrastructure recovery chain is not established by "
                "current accepted evidence."
            ),
        }[recovery_status]
        unknown = {
            "code": "POSTGRESQL_INFRASTRUCTURE_RECOVERY_CONTEXT_NOT_ESTABLISHED",
            "subject": item["instance_id"],
            "status": recovery_status,
            "statement": reason,
        }

    relationship_evidence_ids = [
        value
        for value in item.get("evidence_ids", [])
        if isinstance(value, str) and value
    ]

    return {
        "instance_id": item["instance_id"],
        "subject": deepcopy(item["subject"]),
        "instance_observation_status": item["instance_observation_status"],
        "persistence": {
            "status": persistence["status"],
            "pvc_name": persistence.get("pvc_name"),
            "pvc_phase": persistence.get("pvc_phase"),
            "storage_class": persistence.get("storage_class"),
            "pv_name": persistence.get("pv_name"),
            "storage_node": persistence.get("storage_node"),
        },
        "infrastructure_recovery": {
            "relationship_status": recovery_status,
            "kubernetes_node": mapping.get("kubernetes_node"),
            "pve_source_id": mapping.get("pve_source_id"),
            "pve_node": mapping.get("pve_node"),
            "vmid": vmid,
            "underlying_vm_last_successful_backup_status": vm_last_status,
            "underlying_vm_last_successful_backup_at": vm_last_at,
            "underlying_vm_last_successful_backup_evidence": vm_last_evidence,
            "basis": (
                [
                    "POSTGRESQL_WORKLOAD_OBSERVED",
                    "PERSISTENT_PVC_OBSERVED",
                    "PV_STORAGE_NODE_OBSERVED",
                    "KUBERNETES_NODE_TO_PVE_VMID_OBSERVED",
                    "VM_LAST_SUCCESSFUL_BACKUP_OBSERVED",
                ]
                if recovery_status == "OBSERVED"
                else []
            ),
            "evidence_ids": relationship_evidence_ids,
        },
        "postgresql_assurance": _postgresql_assurance_unknown(),
        "required_evidence": _required_postgresql_evidence(),
    }, unknown


def build_postgresql_infrastructure_recovery_context(
    relationship_evidence: dict[str, Any],
    vm_backup_assurance: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Derive PostgreSQL infrastructure recovery context without promoting database backup assurance."""
    relationship = deepcopy(relationship_evidence)
    vm_artifact = deepcopy(vm_backup_assurance)

    cluster_id, relationship_source_status, source_instances = (
        _validate_relationship_evidence(relationship)
    )
    vm_source_id, vm_source_status, vm_index = _validate_vm_assurance(vm_artifact)

    instances: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    for item in source_instances:
        derived, unknown = _derive_instance(
            item,
            relationship_source_status=relationship_source_status,
            vm_source_id=vm_source_id,
            vm_source_status=vm_source_status,
            vm_index=vm_index,
        )
        instances.append(derived)
        if unknown:
            unknowns.append(unknown)

    unknowns.append(
        {
            "code": "POSTGRESQL_DATABASE_AWARE_BACKUP_SOURCE_NOT_INTEGRATED",
            "subject": None,
            "status": "UNKNOWN",
            "statement": (
                "No authoritative PostgreSQL-aware backup execution/result source is "
                "integrated; database-specific protection, restore, integrity, retention, "
                "RPO, and RTO remain unknown."
            ),
        }
    )
    unknowns.append(
        {
            "code": "POSTGRESQL_RPO_FRESHNESS_POLICY_NOT_ESTABLISHED",
            "subject": None,
            "status": "UNKNOWN",
            "statement": (
                "No accepted PostgreSQL RPO/freshness target exists, so timestamp age "
                "must not be classified as BACKUP_STALE or RPO_VIOLATION."
            ),
        }
    )

    counts = Counter(
        instance["infrastructure_recovery"]["relationship_status"]
        for instance in instances
    )
    vm_observed = sum(
        instance["infrastructure_recovery"][
            "underlying_vm_last_successful_backup_status"
        ]
        == "OBSERVED"
        for instance in instances
    )
    total = len(instances)

    return {
        "postgresql_infrastructure_recovery_context_version": CONTEXT_VERSION,
        "generated_at": _rfc3339(now or datetime.now(timezone.utc)),
        "mutation_allowed": False,
        "scope": {
            "database_engine": DATABASE_ENGINE,
            "platform": "KUBERNETES",
            "cluster_id": cluster_id,
            "derived_only": True,
            "database_aware_backup_source_integrated": False,
            "management_host_postgresql_included": False,
        },
        "source_status": {
            "relationship_evidence": {
                "version": RELATIONSHIP_EVIDENCE_VERSION,
                "source_type": relationship["source"]["type"],
                "source_id": relationship["source"]["source_id"],
                "status": relationship_source_status,
                "generated_at": relationship.get("generated_at"),
            },
            "vm_backup_assurance": {
                "version": REQUIRED_VM_ASSURANCE_VERSION,
                "source_id": vm_source_id,
                "status": vm_source_status,
                "generated_at": vm_artifact.get("generated_at"),
                "integration_mode": vm_artifact[
                    "last_successful_backup_integration"
                ]["mode"],
                "freshness": vm_artifact[
                    "last_successful_backup_integration"
                ].get("source_freshness", "UNKNOWN"),
            },
        },
        "instances": instances,
        "summary": {
            "instances_total": total,
            "infrastructure_recovery_observed": counts.get("OBSERVED", 0),
            "infrastructure_recovery_unknown": counts.get("UNKNOWN", 0),
            "infrastructure_recovery_failed_to_observe": counts.get(
                "FAILED_TO_OBSERVE", 0
            ),
            "underlying_vm_last_successful_backup_observed": vm_observed,
            "postgresql_protection_unknown": total,
            "postgresql_backup_mechanism_unknown": total,
            "postgresql_backup_execution_unknown": total,
            "postgresql_restore_verification_unknown": total,
            "postgresql_integrity_verification_unknown": total,
            "postgresql_rpo_unknown": total,
            "postgresql_rto_unknown": total,
            "unprotected_claims": 0,
            "backup_stale_claims": 0,
            "rpo_violation_claims": 0,
        },
        "unknowns": unknowns,
        "caveats": [
            "Infrastructure recovery context is not PostgreSQL-consistent backup evidence.",
            "An observed successful VM backup does not prove PostgreSQL restore viability or database integrity.",
            "Timestamp age is evidence only; no BACKUP_STALE or RPO_VIOLATION classification is allowed without an accepted target.",
            "UNKNOWN PostgreSQL protection does not mean UNPROTECTED.",
        ],
    }


def render_postgresql_infrastructure_recovery_markdown(
    artifact: dict[str, Any],
) -> str:
    summary = artifact["summary"]
    lines = [
        "# PostgreSQL Infrastructure Recovery Context",
        "",
        f"Cluster: `{artifact['scope']['cluster_id']}`",
        f"Generated: `{artifact['generated_at']}`",
        "Mutation allowed: `false`",
        "Database-aware backup source integrated: `false`",
        "",
        "## Summary",
        "",
        f"- PostgreSQL instances: {summary['instances_total']}",
        f"- infrastructure recovery observed: {summary['infrastructure_recovery_observed']}",
        f"- infrastructure recovery unknown: {summary['infrastructure_recovery_unknown']}",
        f"- infrastructure recovery failed to observe: {summary['infrastructure_recovery_failed_to_observe']}",
        f"- underlying VM last-successful-backup observed: {summary['underlying_vm_last_successful_backup_observed']}",
        f"- PostgreSQL protection unknown: {summary['postgresql_protection_unknown']}",
        f"- unprotected claims: {summary['unprotected_claims']}",
        f"- backup stale claims: {summary['backup_stale_claims']}",
        f"- RPO violation claims: {summary['rpo_violation_claims']}",
        "",
        "## Instances",
        "",
    ]

    for instance in artifact["instances"]:
        subject = instance["subject"]
        recovery = instance["infrastructure_recovery"]
        lines.append(
            "- "
            + f"{subject['namespace']}/{subject['workload_kind']}/{subject['workload_name']}"
            + f" pvc={instance['persistence'].get('pvc_name') or 'unknown'}"
            + f" node={recovery.get('kubernetes_node') or 'unknown'}"
            + f" vmid={recovery.get('vmid') if recovery.get('vmid') is not None else 'unknown'}"
            + f" infrastructure_recovery={recovery['relationship_status']}"
            + f" vm_last_successful_backup={recovery['underlying_vm_last_successful_backup_status']}"
            + f" latest={recovery.get('underlying_vm_last_successful_backup_at') or 'unknown'}"
            + " postgresql_backup=UNKNOWN"
        )

    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "Observed VM recovery evidence is infrastructure context only and must not be represented as PostgreSQL-consistent backup protection.",
            "PostgreSQL backup mechanism, execution/result, artifact location, retention, restore, integrity, RPO, and RTO remain unknown until separate authoritative database-aware evidence is integrated.",
            "Timestamp age alone does not establish BACKUP_STALE or RPO_VIOLATION.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Derive bounded PostgreSQL infrastructure recovery context from accepted "
            "relationship and VM backup evidence."
        )
    )
    parser.add_argument("--relationship-evidence", required=True, type=Path)
    parser.add_argument("--vm-assurance", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--summary-out", required=True, type=Path)
    args = parser.parse_args(argv)

    relationship = json.loads(
        args.relationship_evidence.read_text(encoding="utf-8")
    )
    vm_assurance = json.loads(args.vm_assurance.read_text(encoding="utf-8"))
    result = build_postgresql_infrastructure_recovery_context(
        relationship,
        vm_assurance,
    )
    atomic_write_json(args.out, result)
    atomic_write_text(
        args.summary_out,
        render_postgresql_infrastructure_recovery_markdown(result),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
