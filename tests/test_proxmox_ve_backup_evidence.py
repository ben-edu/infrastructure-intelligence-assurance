from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

from infra_assurance.proxmox_ve_backup_evidence import (
    build_getter_from_env,
    build_proxmox_ve_backup_evidence,
    render_proxmox_ve_backup_evidence_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 15, 15, 40, 0, tzinfo=timezone.utc)


def _responses(*, content=None, content_status=200, version_status=200):
    if content is None:
        content = [
            {
                "content": "backup",
                "vmid": 100,
                "ctime": 1778200000,
                "format": "vma.zst",
                "size": 123456,
                "protected": 0,
                "volid": "local:backup/vzdump-qemu-100-secret-looking.vma.zst",
                "notes": "must not survive projection",
            }
        ]
    return {
        ("/api2/json/version", None): (
            version_status,
            {"version": "9.1.9", "release": "9.1", "repoid": "safe-repo"}
            if version_status == 200
            else None,
            None if version_status == 200 else "HTTP_ERROR",
        ),
        ("/api2/json/nodes", None): (
            200,
            [{"node": "delfan", "status": "online", "ssl_fingerprint": "drop-me"}],
            None,
        ),
        ("/api2/json/cluster/resources", (("type", "vm"),)): (
            200,
            [
                {"vmid": 100, "type": "qemu", "status": "running", "node": "delfan", "name": "private-name"},
                {"vmid": 101, "type": "qemu", "status": "stopped", "node": "delfan", "name": "private-name-2"},
            ],
            None,
        ),
        ("/api2/json/storage", None): (
            200,
            [
                {
                    "storage": "local",
                    "type": "dir",
                    "content": "iso,backup,images",
                    "disable": 0,
                    "prune-backups": "keep-all=1",
                    "path": "/var/lib/vz",
                    "server": "do-not-project",
                },
                {
                    "storage": "future-pbs",
                    "type": "pbs",
                    "content": "backup",
                    "disable": 1,
                    "server": "secret-endpoint",
                    "username": "drop-me",
                },
            ],
            None,
        ),
        ("/api2/json/cluster/backup", None): (
            200,
            [],
            None,
        ),
        ("/api2/json/nodes/delfan/storage/local/content", (("content", "backup"),)): (
            content_status,
            content if content_status == 200 else None,
            None if content_status == 200 else "HTTP_ERROR",
        ),
    }


def _getter(responses):
    def get_json(path, params=None):
        key = (path, tuple(sorted(params.items())) if params else None)
        return responses[key]

    return get_json


def _build(responses=None):
    return build_proxmox_ve_backup_evidence(
        source_id="pve-bm2",
        node="delfan",
        storage_ids=["local"],
        get_json=_getter(responses or _responses()),
        credential_metadata={
            "runtime_credential_approved": False,
            "credential_file_mode_secure": False,
            "tls_verification": False,
            "discovery_override_used": True,
        },
        now=NOW,
    )


def test_complete_projection_is_bounded_and_preserves_recovery_point_semantics():
    artifact = _build()

    assert artifact["source"]["status"] == "COMPLETE"
    assert artifact["mutation_allowed"] is False
    assert artifact["source"]["credential_runtime_approved"] is False
    assert artifact["summary"]["current_guests_observed"] == 2
    assert artifact["summary"]["recovery_points_observed"] == 1
    assert artifact["summary"]["guests_with_recovery_point_in_selected_scopes"] == 1
    assert artifact["summary"]["guest_storage_scopes_without_recovery_point"] == 1
    assert artifact["summary"]["pbs_storages_configured"] == 1

    point = artifact["recovery_points"][0]
    assert point["vmid"] == 100
    assert point["archive_protection_flag"] is False
    assert point["basis"] == ["PVE_STORAGE_CONTENT_BACKUP_RECORD"]

    coverage = {item["vmid"]: item for item in artifact["guest_storage_coverage"]}
    assert coverage[100]["local_recovery_point_status"] == "RECOVERY_POINT_OBSERVED"
    assert coverage[101]["local_recovery_point_status"] == "NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE"

    raw = json.dumps(artifact)
    for forbidden in (
        "volid",
        "private-name",
        "/var/lib/vz",
        "secret-endpoint",
        "ssl_fingerprint",
        "username",
        "UNPROTECTED",
    ):
        assert forbidden not in raw


def test_complete_empty_content_scope_is_not_failed_observation():
    artifact = _build(_responses(content=[]))

    assert artifact["source"]["status"] == "COMPLETE"
    assert artifact["recovery_points"] == []
    assert artifact["summary"]["guest_storage_scopes_without_recovery_point"] == 2
    assert artifact["summary"]["guest_storage_scopes_unknown"] == 0
    assert all(
        item["local_recovery_point_status"] == "NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE"
        for item in artifact["guest_storage_coverage"]
    )


def test_failed_content_observation_remains_unknown_not_absent():
    artifact = _build(_responses(content_status=403))

    assert artifact["source"]["status"] == "PARTIAL"
    assert artifact["content_scopes"] == [
        {
            "node": "delfan",
            "storage_id": "local",
            "status": "FAILED_TO_OBSERVE",
            "recovery_points_observed": 0,
        }
    ]
    assert artifact["summary"]["guest_storage_scopes_without_recovery_point"] == 0
    assert artifact["summary"]["guest_storage_scopes_unknown"] == 2
    assert all(item["local_recovery_point_status"] == "UNKNOWN" for item in artifact["guest_storage_coverage"])


def test_identity_failure_makes_source_failed_to_observe():
    artifact = _build(_responses(version_status=401))
    assert artifact["source"]["status"] == "FAILED_TO_OBSERVE"
    assert any(item["operation"] == "GET_VERSION" for item in artifact["errors"])


def test_archive_protected_flag_never_becomes_platform_protection_state():
    content = [
        {
            "content": "backup",
            "vmid": 100,
            "ctime": 1778200000,
            "format": "vma.zst",
            "size": 123,
            "protected": 1,
        }
    ]
    artifact = _build(_responses(content=content))
    raw = json.dumps(artifact)
    assert artifact["recovery_points"][0]["archive_protection_flag"] is True
    assert "protection_status" not in raw
    assert "PROTECTED" not in raw
    assert "UNPROTECTED" not in raw


def test_markdown_keeps_assurance_boundary_visible():
    text = render_proxmox_ve_backup_evidence_markdown(_build())
    assert "Runtime credential approved: `false`" in text
    assert "RECOVERY_POINT_OBSERVED" in text
    assert "do not establish restore verification" in text


def test_schema_accepts_artifact_and_rejects_secret_projection():
    artifact = _build()
    schema = json.loads((ROOT / "schemas/proxmox-ve-backup-evidence.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(artifact)

    bad = deepcopy(artifact)
    bad["source"]["token"] = "secret"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)

    bad = deepcopy(artifact)
    bad["recovery_points"][0]["volid"] = "raw-volume-id"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate(bad)


def test_credential_file_requires_explicit_discovery_override(tmp_path):
    env_file = tmp_path / "proxmox.env"
    env_file.write_text(
        "PROXMOX_BASE_URL=https://example.invalid:8006\n"
        "PROXMOX_TOKEN_ID=test@pve!token\n"
        "PROXMOX_TOKEN_SECRET=not-printed\n"
        "PROXMOX_VERIFY_TLS=false\n"
    )
    os.chmod(env_file, 0o644)

    with pytest.raises(PermissionError):
        build_getter_from_env(env_file)

    getter, metadata = build_getter_from_env(
        env_file,
        allow_discovery_credential=True,
        allow_insecure_tls_discovery=True,
    )
    assert callable(getter)
    assert metadata == {
        "credential_file_mode_secure": False,
        "tls_verification": False,
        "runtime_credential_approved": False,
        "discovery_override_used": True,
    }
