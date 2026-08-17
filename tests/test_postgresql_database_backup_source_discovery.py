from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/discovery/m5_postgresql_database_backup_source_discovery.py"


def load_module():
    spec = importlib.util.spec_from_file_location("m5_postgresql_backup_discovery", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_workload_projection_excludes_sensitive_values_and_detects_safe_backup_signal():
    module = load_module()
    obj = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "pgbackrest",
                            "image": "example/pgbackrest:1",
                            "command": ["sh", "-c"],
                            "args": ["postgres://user:secret@example.invalid/db"],
                            "env": [
                                {
                                    "name": "DATABASE_URL",
                                    "valueFrom": {
                                        "secretKeyRef": {"name": "db-secret", "key": "url"}
                                    },
                                }
                            ],
                        }
                    ],
                    "volumes": [
                        {"name": "data", "persistentVolumeClaim": {"claimName": "pg-data"}},
                        {"name": "secret", "secret": {"secretName": "db-secret"}},
                        {"name": "cfg", "configMap": {"name": "postgres-backup-config"}},
                    ],
                }
            }
        }
    }

    projection = module.workload_projection(obj)
    rendered = repr(projection)

    assert projection["database_backup_mechanism_status"] == "DECLARED_SIGNAL_OBSERVED"
    assert projection["pvc_volume_count"] == 1
    assert projection["secret_reference_count"] == 2
    assert "pgbackrest" in rendered
    assert "postgres-backup-config" in rendered
    assert "secret" not in rendered.lower().replace("secret_reference_count", "")
    assert "DATABASE_URL" not in rendered
    assert "postgres://" not in rendered
    assert "user:secret" not in rendered
    assert "db-secret" not in rendered
    assert "command" not in projection
    assert "args" not in projection


def test_plain_postgres_container_does_not_promote_backup_mechanism():
    module = load_module()
    obj = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [{"name": "postgres", "image": "postgres:16-alpine"}],
                    "volumes": [{"name": "data", "persistentVolumeClaim": {"claimName": "pg-data"}}],
                }
            }
        }
    }

    projection = module.workload_projection(obj)
    assert projection["database_backup_mechanism_status"] == "DATABASE_BACKUP_MECHANISM_UNKNOWN"
    assert projection["backup_container_signals"] == []
