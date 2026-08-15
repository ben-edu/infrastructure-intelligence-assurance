from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from infra_assurance.vm_backup_assurance import (
    build_vm_backup_assurance,
    render_vm_backup_assurance_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 15, 20, 0, 0, tzinfo=timezone.utc)


def _source() -> dict:
    return {
        "proxmox_ve_backup_evidence_version": "0.1",
        "generated_at": "2026-08-15T18:02:54Z",
        "mutation_allowed": False,
        "source": {
            "type": "proxmox_ve_api",
            "source_id": "pve-bm2",
            "node": "delfan",
            "operation": "BOUNDED_HTTP_GET_BACKUP_EVIDENCE",
            "status": "COMPLETE",
            "collector": "infra_assurance.proxmox_ve_backup_evidence",
            "collector_version": "0.1",
            "credential_runtime_approved": False,
            "credential_file_mode_secure": False,
            "tls_verification": False,
            "discovery_override_used": True,
        },
        "observations": [
            {"operation": "GET_VERSION", "status": "COMPLETE", "http_status": 200, "error_class": None},
            {"operation": "GET_NODES", "status": "COMPLETE", "http_status": 200, "error_class": None},
            {"operation": "GET_GUEST_RESOURCES", "status": "COMPLETE", "http_status": 200, "error_class": None},
            {"operation": "GET_STORAGE_CONFIG", "status": "COMPLETE", "http_status": 200, "error_class": None},
            {"operation": "GET_CLUSTER_BACKUP_JOBS", "status": "COMPLETE", "http_status": 200, "error_class": None},
            {"operation": "GET_STORAGE_BACKUP_CONTENT:local", "status": "COMPLETE", "http_status": 200, "error_class": None},
        ],
        "pve_identity": {"version": "9.1.9", "release": "9.1", "repoid": "safe-repo"},
        "nodes": [{"node": "delfan", "status": "ONLINE"}],
        "guests": [
            {"vmid": 100, "guest_type": "QEMU", "status": "RUNNING", "node": "delfan", "name": "must-not-project"},
            {"vmid": 102, "guest_type": "QEMU", "status": "STOPPED", "node": "delfan"},
            {"vmid": 106, "guest_type": "QEMU", "status": "RUNNING", "node": "delfan"},
        ],
        "storages": [
            {
                "storage_id": "local",
                "storage_type": "dir",
                "backup_content_enabled": True,
                "disabled": False,
                "retention_policy": "keep-all=1",
                "pbs_backend": False,
                "server": "must-not-project",
            }
        ],
        "backup_jobs": [],
        "content_scopes": [
            {"node": "delfan", "storage_id": "local", "status": "COMPLETE", "recovery_points_observed": 3}
        ],
        "recovery_points": [
            {
                "recovery_point_id": "pve-rp-100-a",
                "vmid": 100,
                "node": "delfan",
                "storage_id": "local",
                "format": "vma.zst",
                "created_at": "2026-05-01T00:00:00Z",
                "size_bytes": 100,
                "archive_protection_flag": False,
                "basis": ["PVE_STORAGE_CONTENT_BACKUP_RECORD"],
                "volid": "must-not-project",
            },
            {
                "recovery_point_id": "pve-rp-100-b",
                "vmid": 100,
                "node": "delfan",
                "storage_id": "local",
                "format": "vma.zst",
                "created_at": "2026-05-08T06:13:59Z",
                "size_bytes": 200,
                "archive_protection_flag": False,
                "basis": ["PVE_STORAGE_CONTENT_BACKUP_RECORD"],
            },
            {
                "recovery_point_id": "pve-rp-106-a",
                "vmid": 106,
                "node": "delfan",
                "storage_id": "local",
                "format": "vma.zst",
                "created_at": "2026-08-14T16:13:14Z",
                "size_bytes": 300,
                "archive_protection_flag": False,
                "basis": ["PVE_STORAGE_CONTENT_BACKUP_RECORD"],
            },
        ],
        "guest_storage_coverage": [
            {
                "vmid": 100,
                "storage_id": "local",
                "local_recovery_point_status": "RECOVERY_POINT_OBSERVED",
                "recovery_point_count": 2,
                "latest_recovery_point_at": "2026-05-08T06:13:59Z",
            },
            {
                "vmid": 102,
                "storage_id": "local",
                "local_recovery_point_status": "NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE",
                "recovery_point_count": 0,
                "latest_recovery_point_at": None,
            },
            {
                "vmid": 106,
                "storage_id": "local",
                "local_recovery_point_status": "RECOVERY_POINT_OBSERVED",
                "recovery_point_count": 1,
                "latest_recovery_point_at": "2026-08-14T16:13:14Z",
            },
        ],
        "summary": {},
        "unknowns": [],
        "errors": [],
        "caveats": [],
        "token": "must-not-project",
    }


def _asset(artifact: dict, vmid: int) -> dict:
    return next(item for item in artifact["assets"] if item["subject"]["vmid"] == vmid)


def test_observed_recovery_point_strengthens_mechanism_but_not_protection():
    artifact = build_vm_backup_assurance(_source(), now=NOW)
    vm = _asset(artifact, 100)

    assert vm["assurance"]["protection_status"] == "UNKNOWN"
    assert vm["assurance"]["recovery_point_status"] == "OBSERVED"
    assert vm["assurance"]["backup_mechanism_status"] == "OBSERVED"
    assert vm["assurance"]["latest_recovery_point_at"] == "2026-05-08T06:13:59Z"
    assert vm["assurance"]["recovery_point_count"] == 2
    assert vm["assurance"]["last_successful_backup_status"] == "UNKNOWN"
    assert vm["assurance"]["restore_verification_status"] == "UNKNOWN"
    assert vm["assurance"]["integrity_verification_status"] == "UNKNOWN"
    assert vm["assurance"]["rpo_status"] == "UNKNOWN"
    assert vm["assurance"]["rto_status"] == "RTO_UNKNOWN"
    assert vm["source_recovery_point_ids"] == ["pve-rp-100-a", "pve-rp-100-b"]

    targets = {item["target"]: item["status"] for item in vm["required_evidence"]}
    assert targets["BACKUP_MECHANISM"] == "OBSERVED"
    assert targets["BACKUP_RETENTION"] == "PARTIAL"
    assert targets["LAST_SUCCESSFUL_BACKUP"] == "REQUIRED"
    assert targets["RESTORE_TEST"] == "REQUIRED"


def test_complete_selected_scope_negative_is_not_unprotected():
    artifact = build_vm_backup_assurance(_source(), now=NOW)
    vm = _asset(artifact, 102)

    assert vm["assurance"]["recovery_point_status"] == "NOT_OBSERVED_IN_COMPLETE_SELECTED_SCOPE"
    assert vm["assurance"]["protection_status"] == "UNKNOWN"
    assert vm["assurance"]["backup_mechanism_status"] == "UNKNOWN"
    assert vm["assurance"]["latest_recovery_point_at"] is None
    assert vm["assurance"]["recovery_point_count"] == 0
    assert artifact["summary"]["unprotected_claims"] == 0
    assert "UNPROTECTED" in vm["assurance"]["statement"]


def test_unknown_selected_scope_stays_unknown():
    source = _source()
    source["source"]["status"] = "PARTIAL"
    for item in source["observations"]:
        if item["operation"] == "GET_STORAGE_BACKUP_CONTENT:local":
            item["status"] = "FAILED_TO_OBSERVE"
            item["http_status"] = 403
            item["error_class"] = "HTTP_ERROR"
    for item in source["guest_storage_coverage"]:
        item["local_recovery_point_status"] = "UNKNOWN"
        item["recovery_point_count"] = 0
        item["latest_recovery_point_at"] = None
    source["recovery_points"] = []

    artifact = build_vm_backup_assurance(source, now=NOW)
    assert artifact["source_status"]["overall"] == "PARTIAL"
    assert artifact["summary"]["recovery_point_unknown"] == 3
    assert all(item["assurance"]["recovery_point_status"] == "UNKNOWN" for item in artifact["assets"])
    assert all(item["assurance"]["protection_status"] == "UNKNOWN" for item in artifact["assets"])


def test_failed_guest_inventory_does_not_invent_vm_assets():
    source = _source()
    source["source"]["status"] = "PARTIAL"
    for item in source["observations"]:
        if item["operation"] == "GET_GUEST_RESOURCES":
            item["status"] = "FAILED_TO_OBSERVE"
            item["http_status"] = 403
            item["error_class"] = "HTTP_ERROR"

    artifact = build_vm_backup_assurance(source, now=NOW)
    assert artifact["assets"] == []
    assert artifact["summary"]["assets_total"] == 0
    assert any(item["code"] == "PVE_GUEST_INVENTORY_FAILED_TO_OBSERVE" for item in artifact["unknowns"])


def test_source_input_is_not_mutated_and_unsafe_fields_do_not_project():
    source = _source()
    before = deepcopy(source)
    artifact = build_vm_backup_assurance(source, now=NOW)
    assert source == before

    raw = json.dumps(artifact, sort_keys=True)
    for forbidden_value in ("must-not-project", "volid", "token"):
        assert forbidden_value not in raw


def test_schema_validation_and_strict_projection():
    artifact = build_vm_backup_assurance(_source(), now=NOW)
    schema = json.loads((ROOT / "schemas/vm-backup-assurance.schema.json").read_text())
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(artifact)

    bad = deepcopy(artifact)
    bad["assets"][0]["token"] = "unsafe"
    validator = jsonschema.Draft202012Validator(schema)
    assert list(validator.iter_errors(bad))


def test_summary_is_consistent_and_pvc_domain_is_untouched():
    artifact = build_vm_backup_assurance(_source(), now=NOW)
    assert artifact["summary"] == {
        "assets_total": 3,
        "recovery_point_observed": 2,
        "scoped_negative_recovery_point": 1,
        "recovery_point_unknown": 0,
        "backup_mechanism_observed": 2,
        "retention_configuration_observed": 3,
        "protection_unknown": 3,
        "restore_verification_unknown": 3,
        "integrity_verification_unknown": 3,
        "rpo_unknown": 3,
        "rto_unknown": 3,
        "unprotected_claims": 0,
        "authoritative_source_artifacts_consumed": 1,
        "kubernetes_pvc_assets_modified": 0,
    }
    assert artifact["scope"]["kubernetes_pvc_assurance_modified"] is False


def test_markdown_preserves_assurance_boundary():
    artifact = build_vm_backup_assurance(_source(), now=NOW)
    text = render_vm_backup_assurance_markdown(artifact)
    assert "VMID 100" in text
    assert "recovery_point=OBSERVED" in text
    assert "VMID 102" in text
    assert "NOT_OBSERVED_IN_COMPLETE_SELECTED_SCOPE" in text
    assert "protection=UNKNOWN" in text
    assert "No VMID-to-Kubernetes-PVC relation is inferred" in text
