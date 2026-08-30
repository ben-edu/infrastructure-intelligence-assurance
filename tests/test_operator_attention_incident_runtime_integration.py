from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = REPO_ROOT / "systemd" / "infra-assurance-kubernetes.service"
DEPLOY_PATH = REPO_ROOT / "scripts" / "deploy-operator-attention-runtime.sh"


def test_incident_operator_runs_after_existing_incident_and_backup_operator_artifacts():
    service = SERVICE_PATH.read_text(encoding="utf-8")

    incident_runtime = "ExecStartPost=/usr/bin/python3 -m infra_assurance.incident_runtime "
    observability = "ExecStartPost=/usr/bin/python3 -m infra_assurance.prometheus_rule_context_integration "
    backup = "ExecStartPost=/usr/bin/python3 -m infra_assurance.backup_assurance_foundation "
    backup_operator = "ExecStartPost=/usr/bin/python3 -m infra_assurance.operator_attention_backup "
    incident_operator = "ExecStartPost=/usr/bin/python3 -m infra_assurance.operator_attention_incident "

    for line in (incident_runtime, observability, backup, backup_operator, incident_operator):
        assert line in service

    assert service.index(incident_runtime) < service.index(incident_operator)
    assert service.index(observability) < service.index(backup)
    assert service.index(backup) < service.index(backup_operator) < service.index(incident_operator)
    assert "--operator-attention /var/lib/infra-assurance/evidence/operator-attention.json" in service
    assert "--incident-candidates /var/lib/infra-assurance/evidence/incident-candidates.json" in service


def test_incident_runtime_integration_preserves_existing_identity_and_sandbox():
    service = SERVICE_PATH.read_text(encoding="utf-8")

    assert "User=infra-assurance" in service
    assert "Group=infra-assurance" in service
    assert "Environment=PYTHONPATH=/opt/infra-assurance/src" in service
    assert "NoNewPrivileges=true" in service
    assert "ProtectHome=true" in service
    assert "ReadWritePaths=/var/lib/infra-assurance/evidence" in service
    assert service.count("[Service]") == 1


def test_bounded_deployment_helper_installs_incident_operator_dependencies_and_final_scope():
    helper = DEPLOY_PATH.read_text(encoding="utf-8")

    for module in (
        "operator_attention.py",
        "backup_operator_adapter.py",
        "operator_attention_backup.py",
        "incident_operator_adapter.py",
        "operator_attention_incident.py",
    ):
        assert module in helper

    assert "KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY" in helper
    assert "KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY" in helper
    assert "systemd/infra-assurance-kubernetes.service" in helper
    assert "systemctl daemon-reload" in helper
    assert 'systemctl start "${SERVICE}"' in helper
    assert "bootstrap-observer.sh" in helper
    assert "kubectl" not in helper
    assert "systemctl enable" not in helper


def test_final_operator_projection_reuses_existing_artifact_paths_without_new_service_or_timer():
    service = SERVICE_PATH.read_text(encoding="utf-8")

    assert service.count("operator_attention_incident") == 1
    assert service.count("--out /var/lib/infra-assurance/evidence/operator-attention.json") >= 2
    assert service.count("--summary-out /var/lib/infra-assurance/evidence/operator-attention.md") >= 2
    assert "infra-assurance-incident" not in service
    assert ".timer" not in service
