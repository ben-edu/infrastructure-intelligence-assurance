from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

import jsonschema
import pytest

from infra_assurance.postgresql_infrastructure_recovery_context import (
    build_postgresql_infrastructure_recovery_context,
    render_postgresql_infrastructure_recovery_markdown,
)

ROOT = Path(__file__).resolve().parents[1]


def _relationship(
    *,
    mapping_status="OBSERVED",
    persistence_status="OBSERVED",
    instance_status="OBSERVED",
    vmid=106,
):
    mapping = {
        "status": mapping_status,
        "kubernetes_node": "k3s-master-01" if mapping_status == "OBSERVED" else None,
        "pve_source_id": "pve-bm2" if mapping_status == "OBSERVED" else None,
        "pve_node": "delfan" if mapping_status == "OBSERVED" else None,
        "vmid": vmid if mapping_status == "OBSERVED" else None,
    }
    persistence = {
        "status": persistence_status,
        "pvc_name": (
            "data-keycloak-postgresql-0"
            if persistence_status == "OBSERVED"
            else None
        ),
        "pvc_phase": "Bound" if persistence_status == "OBSERVED" else None,
        "storage_class": "local-path" if persistence_status == "OBSERVED" else None,
        "pv_name": (
            "pvc-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
            if persistence_status == "OBSERVED"
            else None
        ),
        "storage_node": (
            "k3s-master-01" if persistence_status == "OBSERVED" else None
        ),
    }
    return {
        "postgresql_infrastructure_relationship_evidence_version": "0.1",
        "generated_at": "2026-08-16T13:00:00Z",
        "mutation_allowed": False,
        "cluster_id": "k3s-main",
        "source": {
            "type": "BOUNDED_KUBERNETES_PVE_RELATIONSHIP_OBSERVATION",
            "source_id": "m5-postgresql-live-gate",
            "status": "COMPLETE",
        },
        "instances": [
            {
                "instance_id": (
                    "postgresql:kubernetes:k3s-main:keycloak:"
                    "StatefulSet:keycloak-postgresql"
                ),
                "subject": {
                    "system": "kubernetes",
                    "cluster": "k3s-main",
                    "database_engine": "POSTGRESQL",
                    "namespace": "keycloak",
                    "workload_kind": "StatefulSet",
                    "workload_name": "keycloak-postgresql",
                    "container_name": "postgresql",
                    "image": (
                        "docker.io/bitnamilegacy/"
                        "postgresql:17.4.0-debian-12-r17"
                    ),
                },
                "instance_observation_status": instance_status,
                "persistence": persistence,
                "node_vm_mapping": mapping,
                "evidence_ids": [
                    "k8s-pvc-observation:keycloak",
                    "pve-node-vm-observation:106",
                ],
            }
        ],
    }


def _vm_assurance(
    *,
    last_status="OBSERVED",
    latest="2026-08-14T16:39:53Z",
    source_overall="COMPLETE",
    integration_status="COMPLETE",
):
    evidence = None
    if last_status == "OBSERVED":
        evidence = {
            "source_type": "PROXMOX_VE_VZDUMP_TASK_RESULT",
            "source_id": "pve-bm2",
            "recovery_point_id": "pve-rp-aaaaaaaaaaaaaaaaaaaaaaaa",
            "task_result_id": "pve-backup-task:bbbbbbbbbbbbbbbbbbbbbbbb",
            "basis": ["STRICT_SUCCESS_TASK_MATCH"],
        }
    return {
        "vm_backup_assurance_version": "0.2",
        "generated_at": "2026-08-16T12:00:00Z",
        "mutation_allowed": False,
        "source_status": {
            "overall": source_overall,
            "source_id": "pve-bm2",
        },
        "last_successful_backup_integration": {
            "mode": "STRICT_CORRELATION_ONLY",
            "source_id": "pve-bm2",
            "source_status": integration_status,
            "source_freshness": "UNKNOWN",
        },
        "assets": [
            {
                "subject": {
                    "system": "proxmox_ve",
                    "source_id": "pve-bm2",
                    "kind": "VirtualMachine",
                    "vmid": 106,
                },
                "assurance": {
                    "last_successful_backup_status": last_status,
                    "last_successful_backup_at": (
                        latest if last_status == "OBSERVED" else None
                    ),
                    "last_successful_backup_evidence": evidence,
                },
            }
        ],
    }


def test_complete_chain_observes_infrastructure_recovery_only():
    result = build_postgresql_infrastructure_recovery_context(
        _relationship(),
        _vm_assurance(),
        now=datetime(2026, 8, 16, 14, 0, tzinfo=timezone.utc),
    )

    assert result["postgresql_infrastructure_recovery_context_version"] == "0.1"
    assert result["mutation_allowed"] is False
    assert result["scope"]["database_aware_backup_source_integrated"] is False
    assert result["scope"]["management_host_postgresql_included"] is False

    instance = result["instances"][0]
    recovery = instance["infrastructure_recovery"]
    assert recovery["relationship_status"] == "OBSERVED"
    assert recovery["vmid"] == 106
    assert recovery["underlying_vm_last_successful_backup_status"] == "OBSERVED"
    assert recovery["underlying_vm_last_successful_backup_at"] == (
        "2026-08-14T16:39:53Z"
    )
    assert recovery["basis"] == [
        "POSTGRESQL_WORKLOAD_OBSERVED",
        "PERSISTENT_PVC_OBSERVED",
        "PV_STORAGE_NODE_OBSERVED",
        "KUBERNETES_NODE_TO_PVE_VMID_OBSERVED",
        "VM_LAST_SUCCESSFUL_BACKUP_OBSERVED",
    ]

    pg = instance["postgresql_assurance"]
    assert pg["protection_status"] == "UNKNOWN"
    assert pg["backup_mechanism_status"] == "UNKNOWN"
    assert pg["backup_execution_status"] == "UNKNOWN"
    assert pg["backup_artifact_location_status"] == "UNKNOWN"
    assert pg["retention_effectiveness_status"] == "UNKNOWN"
    assert pg["restore_verification_status"] == "UNKNOWN"
    assert pg["integrity_verification_status"] == "UNKNOWN"
    assert pg["rpo_status"] == "UNKNOWN"
    assert pg["rto_status"] == "RTO_UNKNOWN"

    assert result["summary"]["infrastructure_recovery_observed"] == 1
    assert result["summary"]["unprotected_claims"] == 0
    assert result["summary"]["backup_stale_claims"] == 0
    assert result["summary"]["rpo_violation_claims"] == 0


def test_old_vm_backup_timestamp_is_not_stale_or_rpo_violation():
    result = build_postgresql_infrastructure_recovery_context(
        _relationship(),
        _vm_assurance(latest="2026-04-15T12:36:38Z"),
        now=datetime(2026, 8, 16, 14, 0, tzinfo=timezone.utc),
    )
    instance = result["instances"][0]
    assert instance["infrastructure_recovery"]["relationship_status"] == "OBSERVED"
    assert instance["infrastructure_recovery"][
        "underlying_vm_last_successful_backup_at"
    ] == "2026-04-15T12:36:38Z"
    assert instance["postgresql_assurance"]["rpo_status"] == "UNKNOWN"
    assert result["summary"]["backup_stale_claims"] == 0
    assert result["summary"]["rpo_violation_claims"] == 0


def test_vm_backup_unknown_keeps_infrastructure_recovery_unknown():
    result = build_postgresql_infrastructure_recovery_context(
        _relationship(),
        _vm_assurance(last_status="UNKNOWN"),
    )
    recovery = result["instances"][0]["infrastructure_recovery"]
    assert recovery["relationship_status"] == "UNKNOWN"
    assert recovery["underlying_vm_last_successful_backup_status"] == "UNKNOWN"
    assert recovery["underlying_vm_last_successful_backup_at"] is None
    assert result["summary"]["infrastructure_recovery_unknown"] == 1


def test_observed_vm_backup_without_strict_evidence_is_rejected():
    vm = _vm_assurance()
    vm["assets"][0]["assurance"]["last_successful_backup_evidence"] = None
    with pytest.raises(ValueError, match="requires strict evidence"):
        build_postgresql_infrastructure_recovery_context(
            _relationship(),
            vm,
        )


def test_observed_vm_backup_without_strict_success_basis_is_rejected():
    vm = _vm_assurance()
    vm["assets"][0]["assurance"]["last_successful_backup_evidence"][
        "basis"
    ] = ["RECOVERY_POINT_PRESENT"]
    with pytest.raises(ValueError, match="STRICT_SUCCESS_TASK_MATCH"):
        build_postgresql_infrastructure_recovery_context(
            _relationship(),
            vm,
        )


def test_failed_mapping_is_explicit_failed_to_observe():
    result = build_postgresql_infrastructure_recovery_context(
        _relationship(mapping_status="FAILED_TO_OBSERVE"),
        _vm_assurance(),
    )
    recovery = result["instances"][0]["infrastructure_recovery"]
    assert recovery["relationship_status"] == "FAILED_TO_OBSERVE"
    assert recovery["vmid"] is None
    assert result["summary"]["infrastructure_recovery_failed_to_observe"] == 1


def test_incomplete_vm_source_does_not_promote_relationship():
    result = build_postgresql_infrastructure_recovery_context(
        _relationship(),
        _vm_assurance(source_overall="PARTIAL"),
    )
    assert result["source_status"]["vm_backup_assurance"]["status"] == (
        "INCOMPLETE"
    )
    assert result["instances"][0]["infrastructure_recovery"][
        "relationship_status"
    ] == "UNKNOWN"


def test_pve_source_identity_mismatch_is_rejected():
    relationship = _relationship()
    relationship["instances"][0]["node_vm_mapping"]["pve_source_id"] = (
        "pve-other"
    )
    with pytest.raises(ValueError, match="PVE source"):
        build_postgresql_infrastructure_recovery_context(
            relationship,
            _vm_assurance(),
        )


def test_storage_node_mapping_mismatch_is_rejected():
    relationship = _relationship()
    relationship["instances"][0]["node_vm_mapping"]["kubernetes_node"] = (
        "k3s-worker-01"
    )
    with pytest.raises(ValueError, match="storage node"):
        build_postgresql_infrastructure_recovery_context(
            relationship,
            _vm_assurance(),
        )


def test_management_host_subject_is_rejected():
    relationship = _relationship()
    relationship["instances"][0]["subject"]["system"] = "systemd"
    with pytest.raises(ValueError, match="only Kubernetes"):
        build_postgresql_infrastructure_recovery_context(
            relationship,
            _vm_assurance(),
        )


def test_duplicate_instance_identity_is_rejected():
    relationship = _relationship()
    relationship["instances"].append(dict(relationship["instances"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        build_postgresql_infrastructure_recovery_context(
            relationship,
            _vm_assurance(),
        )


def test_output_matches_strict_schema():
    result = build_postgresql_infrastructure_recovery_context(
        _relationship(),
        _vm_assurance(),
    )
    schema = json.loads(
        (
            ROOT
            / "schemas/postgresql-infrastructure-recovery-context.schema.json"
        ).read_text()
    )
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(result)


def test_markdown_preserves_database_backup_unknown_boundary():
    result = build_postgresql_infrastructure_recovery_context(
        _relationship(),
        _vm_assurance(),
    )
    text = render_postgresql_infrastructure_recovery_markdown(result)
    assert "infrastructure_recovery=OBSERVED" in text
    assert "postgresql_backup=UNKNOWN" in text
    assert "RPO_VIOLATION" in text
    assert "password" not in text.lower()
    assert "token" not in text.lower()
    assert "http://" not in text
    assert "https://" not in text
