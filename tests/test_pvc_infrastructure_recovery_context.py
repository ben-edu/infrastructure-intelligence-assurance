from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

from infra_assurance.pvc_infrastructure_recovery_context import (
    build_pvc_infrastructure_recovery_context,
    render_pvc_infrastructure_recovery_markdown,
)

ROOT = Path(__file__).resolve().parents[1]


def _subject() -> dict:
    return {
        "system": "kubernetes",
        "cluster": "k3s-main",
        "kind": "PersistentVolumeClaim",
        "namespace": "keycloak",
        "name": "data-keycloak-postgresql-0",
    }


def _asset_id() -> str:
    return "backup-asset:kubernetes:k3s-main:pvc:keycloak:data-keycloak-postgresql-0"


def _foundation() -> dict:
    return {
        "backup_assurance_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-16T12:00:00Z",
        "mutation_allowed": False,
        "scope": {
            "asset_type": "KUBERNETES_PVC",
            "derived_only": True,
            "authoritative_backup_source_integrated": False,
        },
        "source_status": {
            "overall": "COMPLETE",
            "kubernetes_pvc_inventory": {
                "observation_status": "COMPLETE",
                "freshness": "CURRENT",
                "evidence_id": "evidence:pvc-collection",
            },
            "workload_pvc_relationships": "COMPLETE",
        },
        "summary": {},
        "assets": [
            {
                "asset_id": _asset_id(),
                "asset_type": "KUBERNETES_PVC",
                "subject": _subject(),
                "existence": "PRESENT",
                "observation_status": "COMPLETE",
                "freshness": "CURRENT",
                "observed_at": "2026-08-16T11:59:00Z",
                "expires_at": "2026-08-16T12:14:00Z",
                "storage": {
                    "phase": "Bound",
                    "storage_class": "local-path",
                    "access_modes": ["ReadWriteOnce"],
                    "requested_storage": "8Gi",
                    "capacity": "8Gi",
                    "volume_name": "pvc-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                },
                "workload_context": {
                    "status": "DIRECT_CONTROLLER_REFERENCES_OBSERVED",
                    "related_workloads": [],
                    "related_workloads_total": 1,
                    "caveat": "foundation-only context",
                },
                "assurance": {},
                "required_evidence": [],
                "evidence_ids": ["evidence:pvc-keycloak"],
            }
        ],
        "unknowns": [],
        "caveats": [],
    }


def _relationship(
    *,
    observation_status: str = "OBSERVED",
    storage_status: str = "OBSERVED",
    mapping_status: str = "OBSERVED",
    workload_status: str = "DIRECT_CONTROLLER_REFERENCES_OBSERVED",
    vmid: int = 106,
) -> dict:
    return {
        "pvc_infrastructure_relationship_evidence_version": "0.1",
        "generated_at": "2026-08-16T14:00:00Z",
        "mutation_allowed": False,
        "cluster_id": "k3s-main",
        "source": {
            "type": "BOUNDED_KUBERNETES_PVE_RELATIONSHIP_OBSERVATION",
            "source_id": "m5-pvc-live-gate",
            "status": "COMPLETE",
        },
        "assets": [
            {
                "asset_id": _asset_id(),
                "subject": _subject(),
                "observation_status": observation_status,
                "storage_relationship": {
                    "status": storage_status,
                    "pvc_phase": "Bound" if storage_status == "OBSERVED" else None,
                    "storage_class": "local-path" if storage_status == "OBSERVED" else None,
                    "pv_name": (
                        "pvc-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
                        if storage_status == "OBSERVED"
                        else None
                    ),
                    "storage_node": (
                        "k3s-master-01" if storage_status == "OBSERVED" else None
                    ),
                },
                "workload_context": {
                    "status": workload_status,
                    "related_workloads": (
                        ["StatefulSet/keycloak-postgresql"]
                        if workload_status == "DIRECT_CONTROLLER_REFERENCES_OBSERVED"
                        else []
                    ),
                },
                "node_vm_mapping": {
                    "status": mapping_status,
                    "kubernetes_node": (
                        "k3s-master-01" if mapping_status == "OBSERVED" else None
                    ),
                    "pve_source_id": "pve-bm2" if mapping_status == "OBSERVED" else None,
                    "pve_node": "delfan" if mapping_status == "OBSERVED" else None,
                    "vmid": vmid if mapping_status == "OBSERVED" else None,
                },
                "evidence_ids": ["relationship:keycloak-pvc"],
            }
        ],
    }


def _vm_assurance(
    *,
    last_status: str = "OBSERVED",
    latest: str = "2026-08-14T16:39:53Z",
    source_overall: str = "COMPLETE",
    integration_status: str = "COMPLETE",
) -> dict:
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
    result = build_pvc_infrastructure_recovery_context(
        _foundation(),
        _relationship(),
        _vm_assurance(),
        now=datetime(2026, 8, 16, 15, 0, tzinfo=timezone.utc),
    )

    assert result["pvc_infrastructure_recovery_context_version"] == "0.1"
    assert result["mutation_allowed"] is False
    assert result["scope"]["application_aware_backup_source_integrated"] is False

    asset = result["assets"][0]
    recovery = asset["infrastructure_recovery"]
    assert recovery["relationship_status"] == "OBSERVED"
    assert recovery["vmid"] == 106
    assert recovery["underlying_vm_last_successful_backup_status"] == "OBSERVED"
    assert recovery["underlying_vm_last_successful_backup_at"] == (
        "2026-08-14T16:39:53Z"
    )
    assert recovery["basis"] == [
        "PVC_FOUNDATION_ASSET_OBSERVED",
        "BOUND_PVC_STORAGE_NODE_OBSERVED",
        "KUBERNETES_NODE_TO_PVE_VMID_OBSERVED",
        "VM_LAST_SUCCESSFUL_BACKUP_OBSERVED",
    ]

    assurance = asset["assurance"]
    assert assurance["protection_status"] == "UNKNOWN"
    assert assurance["backup_freshness_status"] == "UNKNOWN"
    assert assurance["backup_mechanism_status"] == "UNKNOWN"
    assert assurance["retention_effectiveness_status"] == "UNKNOWN"
    assert assurance["failure_domain_status"] == "UNKNOWN"
    assert assurance["integrity_verification_status"] == "UNKNOWN"
    assert assurance["restore_verification_status"] == "UNKNOWN"
    assert assurance["rpo_status"] == "UNKNOWN"
    assert assurance["rto_status"] == "RTO_UNKNOWN"

    assert result["summary"]["infrastructure_recovery_observed"] == 1
    assert result["summary"]["protection_unknown"] == 1
    assert result["summary"]["unprotected_claims"] == 0
    assert result["summary"]["backup_stale_claims"] == 0
    assert result["summary"]["rpo_violation_claims"] == 0


def test_no_direct_workload_reference_does_not_block_storage_recovery_context():
    result = build_pvc_infrastructure_recovery_context(
        _foundation(),
        _relationship(workload_status="NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED"),
        _vm_assurance(),
    )
    asset = result["assets"][0]
    assert asset["foundation_context"]["workload_context"]["status"] == (
        "NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED"
    )
    assert asset["infrastructure_recovery"]["relationship_status"] == "OBSERVED"
    assert result["summary"]["direct_workload_reference_none_observed"] == 1
    assert result["summary"]["unprotected_claims"] == 0


def test_old_vm_timestamp_is_not_stale_or_rpo_violation():
    result = build_pvc_infrastructure_recovery_context(
        _foundation(),
        _relationship(),
        _vm_assurance(latest="2026-04-15T12:36:38Z"),
        now=datetime(2026, 8, 16, 15, 0, tzinfo=timezone.utc),
    )
    assert result["assets"][0]["infrastructure_recovery"][
        "underlying_vm_last_successful_backup_at"
    ] == "2026-04-15T12:36:38Z"
    assert result["assets"][0]["assurance"]["backup_freshness_status"] == "UNKNOWN"
    assert result["assets"][0]["assurance"]["rpo_status"] == "UNKNOWN"
    assert result["summary"]["backup_stale_claims"] == 0
    assert result["summary"]["rpo_violation_claims"] == 0


def test_vm_backup_unknown_keeps_recovery_unknown():
    result = build_pvc_infrastructure_recovery_context(
        _foundation(),
        _relationship(),
        _vm_assurance(last_status="UNKNOWN"),
    )
    recovery = result["assets"][0]["infrastructure_recovery"]
    assert recovery["relationship_status"] == "UNKNOWN"
    assert recovery["underlying_vm_last_successful_backup_status"] == "UNKNOWN"
    assert recovery["underlying_vm_last_successful_backup_at"] is None


def test_observed_vm_backup_without_strict_evidence_is_rejected():
    vm = _vm_assurance()
    vm["assets"][0]["assurance"]["last_successful_backup_evidence"] = None
    with pytest.raises(ValueError, match="requires strict evidence"):
        build_pvc_infrastructure_recovery_context(
            _foundation(), _relationship(), vm
        )


def test_observed_vm_backup_without_strict_success_basis_is_rejected():
    vm = _vm_assurance()
    vm["assets"][0]["assurance"]["last_successful_backup_evidence"]["basis"] = [
        "RECOVERY_POINT_PRESENT"
    ]
    with pytest.raises(ValueError, match="STRICT_SUCCESS_TASK_MATCH"):
        build_pvc_infrastructure_recovery_context(
            _foundation(), _relationship(), vm
        )


def test_storage_failure_is_explicit_failed_to_observe():
    result = build_pvc_infrastructure_recovery_context(
        _foundation(),
        _relationship(storage_status="FAILED_TO_OBSERVE", mapping_status="UNKNOWN"),
        _vm_assurance(),
    )
    recovery = result["assets"][0]["infrastructure_recovery"]
    assert recovery["relationship_status"] == "FAILED_TO_OBSERVE"
    assert recovery["vmid"] is None


def test_incomplete_vm_source_does_not_promote_recovery():
    result = build_pvc_infrastructure_recovery_context(
        _foundation(),
        _relationship(),
        _vm_assurance(source_overall="PARTIAL"),
    )
    assert result["source_status"]["vm_backup_assurance"]["status"] == "INCOMPLETE"
    assert result["assets"][0]["infrastructure_recovery"]["relationship_status"] == (
        "UNKNOWN"
    )


def test_pve_source_identity_mismatch_is_rejected():
    relationship = _relationship()
    relationship["assets"][0]["node_vm_mapping"]["pve_source_id"] = "pve-other"
    with pytest.raises(ValueError, match="PVE source"):
        build_pvc_infrastructure_recovery_context(
            _foundation(), relationship, _vm_assurance()
        )


def test_storage_node_mapping_mismatch_is_rejected():
    relationship = _relationship()
    relationship["assets"][0]["node_vm_mapping"]["kubernetes_node"] = (
        "k3s-worker-01"
    )
    with pytest.raises(ValueError, match="storage node"):
        build_pvc_infrastructure_recovery_context(
            _foundation(), relationship, _vm_assurance()
        )


def test_relationship_asset_set_must_exactly_match_foundation():
    relationship = _relationship()
    relationship["assets"] = []
    with pytest.raises(ValueError, match="exactly match"):
        build_pvc_infrastructure_recovery_context(
            _foundation(), relationship, _vm_assurance()
        )


def test_relationship_subject_mismatch_is_rejected():
    relationship = _relationship()
    relationship["assets"][0]["subject"]["name"] = "other"
    with pytest.raises(ValueError, match="subject"):
        build_pvc_infrastructure_recovery_context(
            _foundation(), relationship, _vm_assurance()
        )


def test_output_matches_strict_schema():
    result = build_pvc_infrastructure_recovery_context(
        _foundation(), _relationship(), _vm_assurance()
    )
    schema = json.loads(
        (ROOT / "schemas/pvc-infrastructure-recovery-context.schema.json").read_text()
    )
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(result)


def test_markdown_preserves_protection_unknown_boundary():
    result = build_pvc_infrastructure_recovery_context(
        _foundation(), _relationship(), _vm_assurance()
    )
    text = render_pvc_infrastructure_recovery_markdown(result)
    assert "infrastructure_recovery=OBSERVED" in text
    assert "protection=UNKNOWN" in text
    assert "RPO_VIOLATION" in text
    assert "orphan classification" in text
    assert "password" not in text.lower()
    assert "token" not in text.lower()
    assert "http://" not in text
    assert "https://" not in text
