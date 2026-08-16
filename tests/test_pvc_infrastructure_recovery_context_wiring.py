from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_context_is_pure_derived_and_runtime_unwired():
    text = (
        ROOT / "src/infra_assurance/pvc_infrastructure_recovery_context.py"
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
        "proxmox_token",
        "proxmox_base_url",
    ):
        assert marker not in text

    unit = (ROOT / "systemd/infra-assurance-kubernetes.service").read_text()
    assert "pvc_infrastructure_recovery_context" not in unit
    assert "iia-pvc-infrastructure-recovery-context" not in unit


def test_package_version_and_cli_are_in_sync():
    pyproject = (ROOT / "pyproject.toml").read_text()
    init = (ROOT / "src/infra_assurance/__init__.py").read_text()

    project_match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    init_match = re.search(r'^__version__ = "([^"]+)"$', init, re.MULTILINE)

    assert project_match is not None
    assert init_match is not None
    assert project_match.group(1) == init_match.group(1) == "0.27.0"
    assert (
        'iia-pvc-infrastructure-recovery-context = '
        '"infra_assurance.pvc_infrastructure_recovery_context:main"'
        in pyproject
    )


def test_schema_forbids_pvc_protection_promotion():
    schema = (
        ROOT / "schemas/pvc-infrastructure-recovery-context.schema.json"
    ).read_text()

    for marker in (
        '"protection_status": {"const": "UNKNOWN"}',
        '"backup_freshness_status": {"const": "UNKNOWN"}',
        '"backup_mechanism_status": {"const": "UNKNOWN"}',
        '"retention_effectiveness_status": {"const": "UNKNOWN"}',
        '"failure_domain_status": {"const": "UNKNOWN"}',
        '"integrity_verification_status": {"const": "UNKNOWN"}',
        '"restore_verification_status": {"const": "UNKNOWN"}',
        '"rpo_status": {"const": "UNKNOWN"}',
        '"rto_status": {"const": "RTO_UNKNOWN"}',
        '"unprotected_claims": {"const": 0}',
        '"backup_stale_claims": {"const": 0}',
        '"rpo_violation_claims": {"const": 0}',
    ):
        assert marker in schema


def test_workload_reference_is_context_not_recovery_precondition():
    source = (
        ROOT / "src/infra_assurance/pvc_infrastructure_recovery_context.py"
    ).read_text()

    assert "NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED" in source
    assert "orphan classification" in source
    assert "workload_context" not in (
        "relationship[\"observation_status\"],\n"
        "        storage[\"status\"],\n"
        "        mapping[\"status\"],"
    )


def test_core_contains_no_mutating_operations_or_secret_projection():
    text = (
        ROOT / "src/infra_assurance/pvc_infrastructure_recovery_context.py"
    ).read_text().lower()

    for marker in (
        "kubectl apply",
        "kubectl delete",
        "kubectl patch",
        "kubectl edit",
        "kubectl create",
        "systemctl start",
        "systemctl enable",
        "secret value",
        ".pgpass",
        ".my.cnf",
    ):
        assert marker not in text
