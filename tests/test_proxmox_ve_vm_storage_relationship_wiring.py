from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_exposes_vm_storage_relationship_cli():
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'iia-proxmox-ve-vm-storage-relationship = "infra_assurance.proxmox_ve_vm_storage_relationship:main"' in pyproject


def test_collector_is_manual_only_and_runtime_unwired():
    unit = (ROOT / "systemd/infra-assurance-kubernetes.service").read_text()
    assert "proxmox_ve_vm_storage_relationship" not in unit
    assert "iia-proxmox-ve-vm-storage-relationship" not in unit
    assert "PROXMOX_TOKEN" not in unit
    assert "PROXMOX_BASE_URL" not in unit


def test_collector_has_no_control_methods_or_shell_fallbacks():
    text = (ROOT / "src/infra_assurance/proxmox_ve_vm_storage_relationship.py").read_text()
    assert "BACKUP_FAILURE_DOMAIN remains unchanged" in text
    for forbidden in (
        'method="POST"',
        'method="PUT"',
        'method="DELETE"',
        'method="PATCH"',
        "subprocess",
        "pvesh",
        "qm config",
        "pct config",
    ):
        assert forbidden not in text


def test_schema_excludes_sensitive_and_raw_projection_fields():
    schema = (ROOT / "schemas/proxmox-ve-vm-storage-relationship.schema.json").read_text()
    for forbidden in (
        '"raw_disk"',
        '"volid"',
        '"path"',
        '"server"',
        '"token"',
        '"authorization"',
        '"serial"',
        '"mac"',
        '"ip"',
        '"raw_config"',
    ):
        assert forbidden not in schema
