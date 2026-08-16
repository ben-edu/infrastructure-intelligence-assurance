from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_context_is_pure_derived_and_runtime_unwired():
    text = (
        ROOT
        / "src/infra_assurance/postgresql_infrastructure_recovery_context.py"
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
        "psql ",
        "pg_dump",
        "pg_basebackup",
        "proxmox_token",
        "proxmox_base_url",
    ):
        assert marker not in text

    unit = (ROOT / "systemd/infra-assurance-kubernetes.service").read_text()
    assert "postgresql_infrastructure_recovery_context" not in unit
    assert "iia-postgresql-infrastructure-recovery-context" not in unit


def test_package_version_and_cli_are_in_sync():
    pyproject = (ROOT / "pyproject.toml").read_text()
    init = (ROOT / "src/infra_assurance/__init__.py").read_text()

    project_match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    init_match = re.search(r'^__version__ = "([^"]+)"$', init, re.MULTILINE)

    assert project_match is not None
    assert init_match is not None
    assert project_match.group(1) == init_match.group(1)
    assert (
        'iia-postgresql-infrastructure-recovery-context = '
        '"infra_assurance.postgresql_infrastructure_recovery_context:main"'
        in pyproject
    )


def test_schema_forbids_postgresql_assurance_promotion():
    schema = (
        ROOT
        / "schemas/postgresql-infrastructure-recovery-context.schema.json"
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


def test_management_host_is_explicitly_out_of_scope():
    source = (
        ROOT
        / "src/infra_assurance/postgresql_infrastructure_recovery_context.py"
    ).read_text()
    schema = (
        ROOT
        / "schemas/postgresql-infrastructure-recovery-context.schema.json"
    ).read_text()

    assert '"management_host_postgresql_included": False' in source
    assert '"management_host_postgresql_included": {"const": false}' in schema
    assert 'if subject.get("system") != "kubernetes"' in source
