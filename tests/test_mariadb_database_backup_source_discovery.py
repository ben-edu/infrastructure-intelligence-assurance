from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/discovery/m5_mariadb_database_backup_source_discovery.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mariadb_backup_discovery", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_projection_detects_safe_backup_signal_without_exposing_secret_or_command_values():
    module = load_module()
    workload = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "mariadb",
                            "image": "mariadb:10.11",
                            "env": [
                                {
                                    "name": "PASSWORD",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": "must-not-leak-secret-name",
                                            "key": "must-not-leak-secret-key",
                                        }
                                    },
                                }
                            ],
                            "command": ["sh", "-c", "mysqldump --password=must-not-leak"],
                            "args": ["must-not-leak-arg"],
                        },
                        {
                            "name": "mariadb-backup",
                            "image": "example/mariadb-backup:1",
                            "envFrom": [{"secretRef": {"name": "another-must-not-leak"}}],
                        },
                    ],
                    "volumes": [
                        {"name": "data", "persistentVolumeClaim": {"claimName": "db-data"}},
                        {"name": "credentials", "secret": {"secretName": "volume-secret-must-not-leak"}},
                        {"name": "backup-config", "configMap": {"name": "mariadb-backup-config"}},
                    ],
                }
            }
        }
    }

    result = module.workload_projection(workload)
    rendered = repr(result)

    assert result["database_backup_mechanism_status"] == "DECLARED_SIGNAL_OBSERVED"
    assert result["secret_reference_count"] == 3
    assert result["pvc_volume_count"] == 1
    assert result["backup_container_signals"] == ["mariadb-backup:example/mariadb-backup:1"]
    assert result["backup_configmap_signals"] == ["mariadb-backup-config"]
    assert "must-not-leak" not in rendered
    assert "PASSWORD" not in rendered
    assert "command" not in rendered
    assert "args" not in rendered


def test_no_safe_signal_remains_unknown_and_never_implies_unprotected():
    module = load_module()
    workload = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [{"name": "mariadb", "image": "mariadb:10.11"}],
                    "volumes": [{"name": "data", "persistentVolumeClaim": {"claimName": "db-data"}}],
                }
            }
        }
    }

    result = module.workload_projection(workload)

    assert result["database_backup_mechanism_status"] == "DATABASE_BACKUP_MECHANISM_UNKNOWN"
    assert "UNPROTECTED" not in repr(result)
