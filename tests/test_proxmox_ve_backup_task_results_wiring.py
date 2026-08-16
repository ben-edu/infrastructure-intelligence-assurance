from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_exposes_task_result_cli():
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'iia-proxmox-ve-backup-task-results = "infra_assurance.proxmox_ve_backup_task_results:main"' in pyproject


def test_task_result_collector_is_manual_only_and_runtime_unwired():
    unit = (ROOT / "systemd/infra-assurance-kubernetes.service").read_text()
    assert "proxmox_ve_backup_task_results" not in unit
    assert "iia-proxmox-ve-backup-task-results" not in unit
    assert "PROXMOX_TOKEN" not in unit
    assert "PROXMOX_BASE_URL" not in unit


def test_task_result_source_has_no_control_methods_or_raw_log_endpoint():
    text = (ROOT / "src/infra_assurance/proxmox_ve_backup_task_results.py").read_text()

    assert '"typefilter": "vzdump"' in text
    assert '"limit": str(task_limit)' in text
    assert "STRICT_START_DELTA_SECONDS = 2" in text
    assert '"runtime_credential_approved": False' in text

    for forbidden in (
        'method="POST"',
        'method="PUT"',
        'method="DELETE"',
        'method="PATCH"',
        "/log",
        "subprocess",
        "pvesh",
        "pvesm",
        "vzdump --",
        "proxmox-backup-client",
    ):
        assert forbidden not in text


def test_schema_excludes_raw_task_and_credential_fields():
    schema = (ROOT / "schemas/proxmox-ve-backup-task-results.schema.json").read_text()

    for forbidden in (
        '"upid"',
        '"user"',
        '"token"',
        '"authorization"',
        '"raw_error"',
        '"command"',
        '"log"',
        '"url"',
    ):
        assert forbidden not in schema
