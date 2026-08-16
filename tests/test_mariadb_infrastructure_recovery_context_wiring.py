from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_context_is_pure_derived_and_runtime_unwired():
    text = (
        ROOT / "src/infra_assurance/mariadb_infrastructure_recovery_context.py"
    ).read_text().lower()

    for marker in (
        "urllib",
        "requests.",
        "httpx",
        "socket",
        "subprocess",
        "kubectl",
        "pvesh",
        "pvesm",
        "mysqldump",
        "mariadb-backup",
        "xtrabackup",
        "proxmox_token",
        "proxmox_base_url",
    ):
        assert marker not in text

    unit = (ROOT / "systemd/infra-assurance-kubernetes.service").read_text()
    assert "mariadb_infrastructure_recovery_context" not in unit
    assert "iia-mariadb-infrastructure-recovery-context" not in unit


def test_package_version_and_cli_are_in_sync():
    pyproject = (ROOT / "pyproject.toml").read_text()
    init = (ROOT / "src/infra_assurance/__init__.py").read_text()

    project_match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    init_match = re.search(r'^__version__ = "([^"]+)"$', init, re.MULTILINE)

    assert project_match is not None
    assert init_match is not None
    assert project_match.group(1) == init_match.group(1)
    assert (
        'iia-mariadb-infrastructure-recovery-context = '
        '"infra_assurance.mariadb_infrastructure_recovery_context:main"'
        in pyproject
    )


def test_schema_forbids_mariadb_assurance_promotion():
    schema = (
        ROOT / "schemas/mariadb-infrastructure-recovery-context.schema.json"
    ).read_text()

    for marker in (
        '"protection_status": {"const": "UNKNOWN"}',
        '"backup_mechanism_status": {"const": "UNKNOWN"}',
        '"backup_execution_status": {"const": "UNKNOWN"}',
        '"backup_artifact_location_status": {"const": "UNKNOWN"}',
        '"retention_effectiveness_status": {"const": "UNKNOWN"}',
        '"restore_verification_status": {"const": "UNKNOWN"}',
        '"integrity_verification_status": {"const": "UNKNOWN"}',
        '"rpo_status": {"const": "UNKNOWN"}',
        '"rto_status": {"const": "RTO_UNKNOWN"}',
        '"unprotected_claims": {"const": 0}',
        '"backup_stale_claims": {"const": 0}',
        '"rpo_violation_claims": {"const": 0}',
    ):
        assert marker in schema


def test_live_gate_is_syntax_valid_and_reuses_bounded_discovery():
    path = ROOT / "scripts/live_gates/m5_mariadb_infrastructure_recovery_context.py"
    text = path.read_text()

    compile(text, str(path), "exec")
    assert "m5_mariadb_backup_recovery_discovery.py" in text
    assert "build_getter_from_env" in text
    assert "misp/mariadb-v2" in text
    assert "not classified UNPROTECTED" in text


def test_live_gate_does_not_contain_mutating_operations():
    text = (
        ROOT / "scripts/live_gates/m5_mariadb_infrastructure_recovery_context.py"
    ).read_text().lower()

    for marker in (
        "set -e",
        "set -euo",
        "kubectl apply",
        "kubectl delete",
        "kubectl patch",
        "kubectl edit",
        "kubectl create",
        "kubectl replace",
        "systemctl start",
        "systemctl enable",
        "mysqldump ",
        "mariadb-backup ",
        "xtrabackup ",
    ):
        assert marker not in text
