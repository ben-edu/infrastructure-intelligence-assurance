from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = REPO_ROOT / "systemd" / "infra-assurance-kubernetes.service"
DEPLOY_PATH = REPO_ROOT / "scripts" / "deploy-operator-attention-runtime.sh"


def test_cross_domain_operator_runs_after_backup_assurance_generation():
    service = SERVICE_PATH.read_text(encoding="utf-8")

    backup_line = (
        "ExecStartPost=/usr/bin/python3 -m infra_assurance.backup_assurance_foundation "
    )
    operator_line = (
        "ExecStartPost=/usr/bin/python3 -m infra_assurance.operator_attention_backup "
    )

    assert backup_line in service
    assert operator_line in service
    assert service.index(backup_line) < service.index(operator_line)
    assert "--backup-assurance /var/lib/infra-assurance/evidence/backup-assurance.json" in service


def test_cross_domain_runtime_preserves_existing_service_identity_and_sandbox():
    service = SERVICE_PATH.read_text(encoding="utf-8")

    assert "User=infra-assurance" in service
    assert "Group=infra-assurance" in service
    assert "Environment=PYTHONPATH=/opt/infra-assurance/src" in service
    assert "NoNewPrivileges=true" in service
    assert "ProtectHome=true" in service
    assert "ReadWritePaths=/var/lib/infra-assurance/evidence" in service
    assert service.count("[Service]") == 1


def test_bounded_deployment_helper_installs_only_required_runtime_modules_and_unit():
    helper = DEPLOY_PATH.read_text(encoding="utf-8")

    for module in (
        "operator_attention.py",
        "backup_operator_adapter.py",
        "operator_attention_backup.py",
    ):
        assert module in helper

    assert "systemd/infra-assurance-kubernetes.service" in helper
    assert "KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY" in helper
    assert "systemctl daemon-reload" in helper
    assert 'systemctl start "${SERVICE}"' in helper
    assert "bootstrap-observer.sh" in helper  # dry-run statement explicitly says it is not run
    assert "kubectl" not in helper
    assert "systemctl enable" not in helper
