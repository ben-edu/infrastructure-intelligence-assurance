from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_backup_assurance_runs_after_observability_post_steps():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text()
    rule_integration = text.index("infra_assurance.prometheus_rule_context_integration")
    backup = text.index("infra_assurance.backup_assurance_foundation")
    assert rule_integration < backup
    assert "--snapshot /var/lib/infra-assurance/evidence/kubernetes.json" in text
    assert "--topology /var/lib/infra-assurance/evidence/topology.json" in text
    assert "--out /var/lib/infra-assurance/evidence/backup-assurance.json" in text
    assert "--summary-out /var/lib/infra-assurance/evidence/backup-assurance.md" in text


def test_backup_assurance_foundation_is_derived_only():
    text = (
        ROOT
        / "src"
        / "infra_assurance"
        / "backup_assurance_foundation.py"
    ).read_text()
    for marker in (
        "subprocess",
        "kubectl",
        "_proxy_get_json",
        "requests.",
        "httpx",
        "urllib",
        "socket",
        "proxmox",
        "pbs",
        "psql",
        "mariadb",
    ):
        assert marker not in text.lower()


def test_package_exposes_backup_assurance_cli_and_current_version():
    pyproject = (ROOT / "pyproject.toml").read_text()
    init = (ROOT / "src" / "infra_assurance" / "__init__.py").read_text()
    assert 'version = "0.19.0"' in pyproject
    assert '__version__ = "0.19.0"' in init
    assert (
        'iia-backup-assurance-foundation = '
        '"infra_assurance.backup_assurance_foundation:main"'
    ) in pyproject


def test_backup_assurance_requires_no_rbac_change_marker():
    rbac = (ROOT / "deploy" / "kubernetes" / "observer-rbac.yaml").read_text()
    assert "backup-assurance" not in rbac
    assert "backup_assurance" not in rbac
