from __future__ import annotations

from datetime import datetime, timezone

import pytest

from infra_assurance.vm_last_successful_backup_integration import (
    build_vm_last_successful_backup_integration,
    render_vm_last_successful_backup_markdown,
)


def _asset(vmid: int, point_ids: list[str]) -> dict:
    return {
        "asset_id": f"backup-asset:proxmox-ve:pve-bm2:vm:{vmid}",
        "asset_type": "VIRTUAL_MACHINE",
        "subject": {
            "system": "proxmox_ve",
            "source_id": "pve-bm2",
            "kind": "VirtualMachine",
            "node": "delfan",
            "vmid": vmid,
            "guest_type": "QEMU",
            "guest_status": "RUNNING",
        },
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "freshness": "UNKNOWN",
        "source_context": {},
        "assurance": {
            "protection_status": "UNKNOWN",
            "recovery_point_status": "OBSERVED" if point_ids else "NOT_OBSERVED_IN_COMPLETE_SELECTED_SCOPE",
            "recovery_point_count": len(point_ids),
            "latest_recovery_point_at": "2026-08-14T16:13:14Z" if point_ids else None,
            "backup_mechanism_status": "OBSERVED" if point_ids else "UNKNOWN",
            "backup_mechanisms": [],
            "retention_context": [],
            "last_successful_backup_status": "UNKNOWN",
            "integrity_verification_status": "UNKNOWN",
            "restore_verification_status": "UNKNOWN",
            "failure_domain_status": "UNKNOWN",
            "scheduled_protection_status": "UNKNOWN",
            "rpo_status": "UNKNOWN",
            "rto_status": "RTO_UNKNOWN",
            "basis": [],
            "statement": "fixture",
        },
        "required_evidence": [
            {"target": "BACKUP_MECHANISM", "status": "OBSERVED" if point_ids else "REQUIRED", "statement": "fixture"},
            {"target": "LAST_SUCCESSFUL_BACKUP", "status": "REQUIRED", "statement": "fixture"},
            {"target": "BACKUP_RETENTION", "status": "PARTIAL", "statement": "fixture"},
            {"target": "BACKUP_FAILURE_DOMAIN", "status": "REQUIRED", "statement": "fixture"},
            {"target": "BACKUP_INTEGRITY_VERIFICATION", "status": "REQUIRED", "statement": "fixture"},
            {"target": "RESTORE_TEST", "status": "REQUIRED", "statement": "fixture"},
            {"target": "RPO_TARGET_AND_RESULT", "status": "REQUIRED", "statement": "fixture"},
            {"target": "RTO_TARGET_AND_RESULT", "status": "REQUIRED", "statement": "fixture"},
        ],
        "source_recovery_point_ids": point_ids,
    }


def _vm_artifact() -> dict:
    return {
        "vm_backup_assurance_version": "0.1",
        "generated_at": "2026-08-15T18:18:47Z",
        "mutation_allowed": False,
        "scope": {
            "asset_type": "VIRTUAL_MACHINE",
            "derived_only": True,
            "source_neutral_assurance": True,
            "kubernetes_pvc_assurance_modified": False,
        },
        "source_status": {
            "overall": "COMPLETE",
            "source_type": "PROXMOX_VE",
            "source_id": "pve-bm2",
            "source_artifact_version": "0.1",
            "source_generated_at": "2026-08-15T18:02:54Z",
            "source_freshness": "UNKNOWN",
            "guest_inventory": "COMPLETE",
        },
        "assets": [
            _asset(106, ["pve-rp-4aec7ab32df95c5091c9efd6", "pve-rp-e0200d18b09e58e39e49872d"]),
            _asset(102, []),
        ],
        "summary": {
            "assets_total": 2,
            "recovery_point_observed": 1,
            "scoped_negative_recovery_point": 1,
            "recovery_point_unknown": 0,
            "backup_mechanism_observed": 1,
            "retention_configuration_observed": 2,
            "protection_unknown": 2,
            "restore_verification_unknown": 2,
            "integrity_verification_unknown": 2,
            "rpo_unknown": 2,
            "rto_unknown": 2,
            "unprotected_claims": 0,
            "authoritative_source_artifacts_consumed": 1,
            "kubernetes_pvc_assets_modified": 0,
        },
        "unknowns": [],
    }


def _task_artifact() -> dict:
    return {
        "pve_backup_task_results_version": "0.1",
        "generated_at": "2026-08-15T21:52:37Z",
        "mutation_allowed": False,
        "source": {
            "type": "proxmox_ve_api",
            "source_id": "pve-bm2",
            "node": "delfan",
            "operation": "GET_BOUNDED_VZDUMP_TASK_RESULTS",
            "status": "COMPLETE",
            "request_mode": "SERVER_FILTERED_VZDUMP",
            "task_limit": 500,
            "limit_saturated": False,
            "historical_completeness": "NOT_ESTABLISHED",
            "credential_file_mode_secure": False,
            "tls_verification": False,
            "runtime_credential_approved": False,
            "discovery_override_used": True,
        },
        "observation": {},
        "task_results": [
            {
                "task_result_id": "pve-task-aaaaaaaaaaaaaaaaaaaaaaaa",
                "task_type": "VZDUMP",
                "node": "delfan",
                "vmid": 106,
                "start_time": "2026-08-14T16:13:13Z",
                "end_time": "2026-08-14T16:39:53Z",
                "result": "SUCCESS",
            }
        ],
        "recovery_point_correlations": [
            {
                "recovery_point_id": "pve-rp-4aec7ab32df95c5091c9efd6",
                "vmid": 106,
                "status": "STRICT_SUCCESS_TASK_MATCH",
                "task_result_id": "pve-task-aaaaaaaaaaaaaaaaaaaaaaaa",
                "start_delta_seconds": 1,
                "basis": ["VMID", "RECOVERY_POINT_CREATED_AT", "VZDUMP_START_TIME"],
            },
            {
                "recovery_point_id": "pve-rp-e0200d18b09e58e39e49872d",
                "vmid": 106,
                "status": "NO_STRICT_MATCH_IN_RETURNED_HISTORY",
                "task_result_id": None,
                "start_delta_seconds": None,
                "basis": ["VMID", "RECOVERY_POINT_CREATED_AT", "VZDUMP_START_TIME"],
            },
        ],
        "summary": {},
        "unknowns": [],
    }


def test_strict_success_strengthens_only_last_successful_backup():
    result = build_vm_last_successful_backup_integration(
        _vm_artifact(),
        _task_artifact(),
        now=datetime(2026, 8, 15, 22, 0, tzinfo=timezone.utc),
    )

    assert result["vm_backup_assurance_version"] == "0.2"
    assert result["mutation_allowed"] is False
    assert result["last_successful_backup_integration"]["mode"] == "STRICT_CORRELATION_ONLY"
    assert result["last_successful_backup_integration"]["source_freshness"] == "UNKNOWN"

    vm106 = result["assets"][0]
    assurance = vm106["assurance"]
    assert assurance["last_successful_backup_status"] == "OBSERVED"
    assert assurance["last_successful_backup_at"] == "2026-08-14T16:39:53Z"
    assert assurance["last_successful_backup_evidence"] == {
        "source_type": "PROXMOX_VE_VZDUMP_TASK_RESULT",
        "source_id": "pve-bm2",
        "recovery_point_id": "pve-rp-4aec7ab32df95c5091c9efd6",
        "task_result_id": "pve-task-aaaaaaaaaaaaaaaaaaaaaaaa",
        "basis": ["STRICT_SUCCESS_TASK_MATCH"],
    }
    assert assurance["protection_status"] == "UNKNOWN"
    assert assurance["restore_verification_status"] == "UNKNOWN"
    assert assurance["integrity_verification_status"] == "UNKNOWN"
    assert assurance["failure_domain_status"] == "UNKNOWN"
    assert assurance["scheduled_protection_status"] == "UNKNOWN"
    assert assurance["rpo_status"] == "UNKNOWN"
    assert assurance["rto_status"] == "RTO_UNKNOWN"

    targets = {item["target"]: item["status"] for item in vm106["required_evidence"]}
    assert targets["LAST_SUCCESSFUL_BACKUP"] == "OBSERVED"
    assert targets["RESTORE_TEST"] == "REQUIRED"
    assert targets["BACKUP_INTEGRITY_VERIFICATION"] == "REQUIRED"
    assert targets["RPO_TARGET_AND_RESULT"] == "REQUIRED"
    assert targets["RTO_TARGET_AND_RESULT"] == "REQUIRED"

    vm102 = result["assets"][1]
    assert vm102["assurance"]["last_successful_backup_status"] == "UNKNOWN"
    assert vm102["assurance"]["last_successful_backup_at"] is None
    assert vm102["assurance"]["last_successful_backup_evidence"] is None

    assert result["summary"]["last_successful_backup_observed"] == 1
    assert result["summary"]["last_successful_backup_unknown"] == 1
    assert result["summary"]["strict_success_correlations_consumed"] == 1
    assert result["summary"]["unmatched_recovery_points_in_returned_task_history"] == 1
    assert result["summary"]["unprotected_claims"] == 0
    assert result["summary"]["kubernetes_pvc_assets_modified"] == 0


def test_latest_strict_success_uses_successful_task_completion_time():
    tasks = _task_artifact()
    tasks["task_results"].append(
        {
            "task_result_id": "pve-task-bbbbbbbbbbbbbbbbbbbbbbbb",
            "task_type": "VZDUMP",
            "node": "delfan",
            "vmid": 106,
            "start_time": "2026-08-15T10:00:00Z",
            "end_time": "2026-08-15T10:20:00Z",
            "result": "SUCCESS",
        }
    )
    vm = _vm_artifact()
    vm["assets"][0]["source_recovery_point_ids"].append("pve-rp-bbbbbbbbbbbbbbbbbbbbbbbb")
    tasks["recovery_point_correlations"].append(
        {
            "recovery_point_id": "pve-rp-bbbbbbbbbbbbbbbbbbbbbbbb",
            "vmid": 106,
            "status": "STRICT_SUCCESS_TASK_MATCH",
            "task_result_id": "pve-task-bbbbbbbbbbbbbbbbbbbbbbbb",
            "start_delta_seconds": 0,
            "basis": ["VMID", "RECOVERY_POINT_CREATED_AT", "VZDUMP_START_TIME"],
        }
    )

    result = build_vm_last_successful_backup_integration(vm, tasks)
    assurance = result["assets"][0]["assurance"]
    assert assurance["last_successful_backup_at"] == "2026-08-15T10:20:00Z"
    assert assurance["last_successful_backup_evidence"]["task_result_id"] == "pve-task-bbbbbbbbbbbbbbbbbbbbbbbb"


def test_source_identity_mismatch_is_rejected():
    tasks = _task_artifact()
    tasks["source"]["source_id"] = "pve-other"
    with pytest.raises(ValueError, match="source identities do not match"):
        build_vm_last_successful_backup_integration(_vm_artifact(), tasks)


def test_strict_correlation_with_wrong_vmid_is_rejected():
    tasks = _task_artifact()
    tasks["recovery_point_correlations"][0]["vmid"] = 107
    with pytest.raises(ValueError, match="ownership"):
        build_vm_last_successful_backup_integration(_vm_artifact(), tasks)


def test_strict_correlation_to_non_success_task_is_rejected():
    tasks = _task_artifact()
    tasks["task_results"][0]["result"] = "FAILURE"
    with pytest.raises(ValueError, match="successful result"):
        build_vm_last_successful_backup_integration(_vm_artifact(), tasks)


def test_failed_task_source_does_not_promote_last_successful_backup():
    tasks = _task_artifact()
    tasks["source"]["status"] = "FAILED_TO_OBSERVE"
    result = build_vm_last_successful_backup_integration(_vm_artifact(), tasks)
    assert all(
        asset["assurance"]["last_successful_backup_status"] == "UNKNOWN"
        for asset in result["assets"]
    )
    assert result["summary"]["last_successful_backup_observed"] == 0


def test_markdown_exposes_bounded_status_without_sensitive_source_fields():
    result = build_vm_last_successful_backup_integration(_vm_artifact(), _task_artifact())
    text = render_vm_last_successful_backup_markdown(result)
    assert "last_successful_backup_observed: 1" in text
    assert "STRICT_SUCCESS_TASK_MATCH" in text
    assert "token" not in text.lower()
    assert "http://" not in text
    assert "https://" not in text
