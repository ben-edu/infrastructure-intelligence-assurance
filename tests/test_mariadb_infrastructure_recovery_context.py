from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

import jsonschema
import pytest

from infra_assurance.mariadb_infrastructure_recovery_context import (
    build_mariadb_infrastructure_recovery_context,
    render_mariadb_infrastructure_recovery_markdown,
)

ROOT = Path(__file__).resolve().parents[1]


def _relationship(*, persistent=True, mapping_status="OBSERVED", vmid=106):
    persistence_status = "OBSERVED" if persistent else "UNKNOWN"
    mapping_status = mapping_status if persistent else "UNKNOWN"
    persistence = {
        "status": persistence_status,
        "pvc_name": "mariadb-pvc" if persistent else None,
        "pvc_phase": "Bound" if persistent else None,
        "storage_class": "local-path" if persistent else None,
        "pv_name": "pvc-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee" if persistent else None,
        "storage_node": "k3s-master-01" if persistent else None,
    }
    mapping = {
        "status": mapping_status,
        "kubernetes_node": "k3s-master-01" if mapping_status == "OBSERVED" else None,
        "pve_source_id": "pve-bm2" if mapping_status == "OBSERVED" else None,
        "pve_node": "delfan" if mapping_status == "OBSERVED" else None,
        "vmid": vmid if mapping_status == "OBSERVED" else None,
    }
    return {
        "mariadb_infrastructure_relationship_evidence_version": "0.1",
        "generated_at": "2026-08-16T14:00:00Z",
        "mutation_allowed": False,
        "cluster_id": "k3s-main",
        "source": {
            "type": "BOUNDED_KUBERNETES_PVE_RELATIONSHIP_OBSERVATION",
            "source_id": "m5-mariadb-live-gate",
            "status": "COMPLETE",
        },
        "instances": [
            {
                "instance_id": "mariadb:kubernetes:k3s-main:misp:Deployment:mariadb",
                "subject": {
                    "system": "kubernetes",
                    "cluster": "k3s-main",
                    "database_engine": "MARIADB_COMPATIBLE",
                    "namespace": "misp",
                    "workload_kind": "Deployment",
                    "workload_name": "mariadb",
                    "container_name": "mariadb",
                    "image": "mariadb:10.5",
                },
                "instance_observation_status": "OBSERVED",
                "persistence": persistence,
                "node_vm_mapping": mapping,
                "evidence_ids": ["k8s-mariadb-observation:misp:mariadb"],
            }
        ],
    }


def _vm_assurance(*, last_status="OBSERVED", latest="2026-08-14T16:39:53Z"):
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
        "source_status": {"overall": "COMPLETE", "source_id": "pve-bm2"},
        "last_successful_backup_integration": {
            "mode": "STRICT_CORRELATION_ONLY",
            "source_id": "pve-bm2",
            "source_status": "COMPLETE",
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
                    "last_successful_backup_at": latest if last_status == "OBSERVED" else None,
                    "last_successful_backup_evidence": evidence,
                },
            }
        ],
    }


def test_complete_persistent_chain_observes_infrastructure_recovery_only():
    result = build_mariadb_infrastructure_recovery_context(
        _relationship(),
        _vm_assurance(),
        now=datetime(2026, 8, 16, 15, 0, tzinfo=timezone.utc),
    )
    assert result["mariadb_infrastructure_recovery_context_version"] == "0.1"
    assert result["mutation_allowed"] is False
    assert result["summary"]["persistence_observed"] == 1
    assert result["summary"]["infrastructure_recovery_observed"] == 1
    assert result["summary"]["mariadb_protection_unknown"] == 1
    instance = result["instances"][0]
    assert instance["infrastructure_recovery"]["relationship_status"] == "OBSERVED"
    assert instance["infrastructure_recovery"]["vmid"] == 106
    assert instance["mariadb_assurance"]["protection_status"] == "UNKNOWN"
    assert result["summary"]["unprotected_claims"] == 0


def test_missing_persistent_pvc_remains_unknown_not_unprotected():
    result = build_mariadb_infrastructure_recovery_context(
        _relationship(persistent=False),
        _vm_assurance(),
    )
    instance = result["instances"][0]
    assert instance["persistence"]["status"] == "UNKNOWN"
    assert instance["infrastructure_recovery"]["relationship_status"] == "UNKNOWN"
    assert result["summary"]["persistence_unknown"] == 1
    assert result["summary"]["infrastructure_recovery_unknown"] == 1
    assert result["summary"]["unprotected_claims"] == 0


def test_old_vm_timestamp_is_not_classified_stale_or_rpo_violation():
    result = build_mariadb_infrastructure_recovery_context(
        _relationship(vmid=106),
        _vm_assurance(latest="2026-04-15T12:36:38Z"),
    )
    assert result["instances"][0]["infrastructure_recovery"]["relationship_status"] == "OBSERVED"
    assert result["instances"][0]["mariadb_assurance"]["rpo_status"] == "UNKNOWN"
    assert result["summary"]["backup_stale_claims"] == 0
    assert result["summary"]["rpo_violation_claims"] == 0


def test_observed_vm_backup_without_strict_evidence_is_rejected():
    vm = _vm_assurance()
    vm["assets"][0]["assurance"]["last_successful_backup_evidence"] = None
    with pytest.raises(ValueError, match="requires strict evidence"):
        build_mariadb_infrastructure_recovery_context(_relationship(), vm)


def test_mapping_cannot_be_observed_without_persistence():
    relationship = _relationship(persistent=False)
    relationship["instances"][0]["node_vm_mapping"] = {
        "status": "OBSERVED",
        "kubernetes_node": "k3s-master-01",
        "pve_source_id": "pve-bm2",
        "pve_node": "delfan",
        "vmid": 106,
    }
    with pytest.raises(ValueError, match="persistent storage"):
        build_mariadb_infrastructure_recovery_context(relationship, _vm_assurance())


def test_pve_source_mismatch_is_rejected():
    relationship = _relationship()
    relationship["instances"][0]["node_vm_mapping"]["pve_source_id"] = "pve-other"
    with pytest.raises(ValueError, match="PVE source"):
        build_mariadb_infrastructure_recovery_context(relationship, _vm_assurance())


def test_output_matches_schema():
    result = build_mariadb_infrastructure_recovery_context(
        _relationship(), _vm_assurance()
    )
    schema = json.loads(
        (ROOT / "schemas/mariadb-infrastructure-recovery-context.schema.json").read_text()
    )
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    ).validate(result)


def test_markdown_preserves_unknown_database_backup_boundary():
    result = build_mariadb_infrastructure_recovery_context(
        _relationship(), _vm_assurance()
    )
    text = render_mariadb_infrastructure_recovery_markdown(result)
    assert "infrastructure_recovery=OBSERVED" in text
    assert "mariadb_backup=UNKNOWN" in text
    assert "RPO_VIOLATION" in text
    assert "password" not in text.lower()
    assert "token" not in text.lower()
    assert "http://" not in text
    assert "https://" not in text
