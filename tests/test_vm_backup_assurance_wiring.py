from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vm_backup_assurance_is_derived_only():
    text = (ROOT / "src/infra_assurance/vm_backup_assurance.py").read_text().lower()
    for marker in (
        "urllib",
        "requests.",
        "httpx",
        "socket",
        "subprocess",
        "pvesh",
        "pvesm",
        "vzdump",
        "proxmox-backup-client",
        "kubectl",
    ):
        assert marker not in text


def test_runtime_service_does_not_wire_vm_backup_assurance_or_proxmox_credentials():
    unit = (ROOT / "systemd/infra-assurance-kubernetes.service").read_text()
    assert "vm_backup_assurance" not in unit
    assert "iia-vm-backup-assurance" not in unit
    assert "proxmox_ve_backup_evidence" not in unit
    assert "PROXMOX_TOKEN" not in unit
    assert "PROXMOX_BASE_URL" not in unit


def test_package_exposes_vm_assurance_cli():
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'iia-vm-backup-assurance = "infra_assurance.vm_backup_assurance:main"' in pyproject


def test_vm_assurance_does_not_modify_kubernetes_pvc_foundation_contract():
    schema = (ROOT / "schemas/backup-assurance-foundation.schema.json").read_text()
    source = (ROOT / "src/infra_assurance/backup_assurance_foundation.py").read_text()

    assert '"asset_type": {"const": "KUBERNETES_PVC"}' in schema
    assert 'ASSET_TYPE = "KUBERNETES_PVC"' in source
