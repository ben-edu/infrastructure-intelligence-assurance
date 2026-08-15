from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_proxmox_adapter_is_get_only_and_has_no_control_client():
    text = (ROOT / "src/infra_assurance/proxmox_ve_backup_evidence.py").read_text()

    assert 'method="GET"' in text
    for forbidden in (
        'method="POST"',
        'method="PUT"',
        'method="DELETE"',
        'method="PATCH"',
        "subprocess",
        "requests.",
        "httpx",
        "pvesh",
        "pvesm",
        "vzdump",
        "proxmox-backup-client",
    ):
        assert forbidden not in text


def test_runtime_service_does_not_wire_proxmox_discovery_credential():
    unit = (ROOT / "systemd/infra-assurance-kubernetes.service").read_text()
    assert "proxmox_ve_backup_evidence" not in unit
    assert "iia-proxmox-ve-backup-evidence" not in unit
    assert "PROXMOX_TOKEN" not in unit


def test_package_exposes_manual_collector_without_runtime_wiring():
    pyproject = (ROOT / "pyproject.toml").read_text()

    assert 'iia-proxmox-ve-backup-evidence = "infra_assurance.proxmox_ve_backup_evidence:main"' in pyproject
