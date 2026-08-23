from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/discovery/m5_external_backup_target_discovery.py"


def load_module():
    spec = importlib.util.spec_from_file_location("m5_external_backup_target_discovery", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_safe_projection_drops_sensitive_storage_fields():
    module = load_module()
    raw = {
        "storage": "pbs-main",
        "type": "pbs",
        "content": "backup,iso",
        "disable": 0,
        "server": "sensitive.example.internal",
        "path": "/sensitive/path",
        "portal": "10.0.0.1",
        "username": "backup-user",
        "password": "secret",
        "fingerprint": "aa:bb:cc",
        "token": "secret-token",
    }

    projection = module.safe_storage_projection(raw)

    assert projection == {
        "storage_id": "pbs-main",
        "storage_type": "pbs",
        "backup_content_enabled": True,
        "disabled": False,
        "target_classification": "PBS_LIKE_TARGET",
    }
    for forbidden in (
        "server",
        "path",
        "portal",
        "username",
        "password",
        "fingerprint",
        "token",
    ):
        assert forbidden not in projection


def test_target_type_classification_does_not_overclaim_dir_failure_domain():
    module = load_module()

    assert module.classify_target_type("pbs") == "PBS_LIKE_TARGET"
    assert module.classify_target_type("nfs") == "NETWORK_STORAGE_LIKE_TARGET"
    assert module.classify_target_type("cifs") == "NETWORK_STORAGE_LIKE_TARGET"
    assert module.classify_target_type("dir") == "PATH_BASED_LOCATION_UNKNOWN"
    assert module.classify_target_type("zfspool") == "OTHER_STORAGE_TYPE_UNKNOWN"
