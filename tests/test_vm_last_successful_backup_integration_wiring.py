from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_integration_is_derived_only_and_runtime_unwired():
    text = (ROOT / "src/infra_assurance/vm_last_successful_backup_integration.py").read_text().lower()
    for marker in (
        "urllib",
        "requests.",
        "httpx",
        "socket",
        "subprocess",
        "pvesh",
        "pvesm",
        "vzdump --",
        "proxmox-backup-client",
        "proxmox_token",
        "proxmox_base_url",
    ):
        assert marker not in text

    unit = (ROOT / "systemd/infra-assurance-kubernetes.service").read_text()
    assert "vm_last_successful_backup_integration" not in unit
    assert "iia-vm-last-successful-backup" not in unit
    assert "PROXMOX_TOKEN" not in unit
    assert "PROXMOX_BASE_URL" not in unit


def test_package_exposes_current_integration_cli_and_version():
    pyproject = (ROOT / "pyproject.toml").read_text()
    init = (ROOT / "src/infra_assurance/__init__.py").read_text()
    assert 'version = "0.23.0"' in pyproject
    assert '__version__ = "0.23.0"' in init
    assert 'iia-vm-last-successful-backup = "infra_assurance.vm_last_successful_backup_integration:main"' in pyproject


def test_integration_contract_markers_are_strict():
    text = (ROOT / "src/infra_assurance/vm_last_successful_backup_integration.py").read_text()
    assert 'INTEGRATION_VERSION = "0.1"' in text
    assert 'OUTPUT_VM_ASSURANCE_VERSION = "0.2"' in text
    assert '"mode": "STRICT_CORRELATION_ONLY"' in text
    assert '"basis": ["STRICT_SUCCESS_TASK_MATCH"]' in text
    assert 'assurance["last_successful_backup_status"] = "OBSERVED"' in text
    assert 'assurance["protection_status"]' not in text


def test_schema_keeps_unrelated_assurance_dimensions_unknown():
    schema = (ROOT / "schemas/vm-last-successful-backup-integration.schema.json").read_text()
    for marker in (
        '"protection_status": {"const": "UNKNOWN"}',
        '"integrity_verification_status": {"const": "UNKNOWN"}',
        '"restore_verification_status": {"const": "UNKNOWN"}',
        '"failure_domain_status": {"const": "UNKNOWN"}',
        '"scheduled_protection_status": {"const": "UNKNOWN"}',
        '"rpo_status": {"const": "UNKNOWN"}',
        '"rto_status": {"const": "RTO_UNKNOWN"}',
    ):
        assert marker in schema


def test_kubernetes_pvc_foundation_contract_is_untouched():
    schema = (ROOT / "schemas/backup-assurance-foundation.schema.json").read_text()
    source = (ROOT / "src/infra_assurance/backup_assurance_foundation.py").read_text()
    assert '"asset_type": {"const": "KUBERNETES_PVC"}' in schema
    assert 'ASSET_TYPE = "KUBERNETES_PVC"' in source
