from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_routing_context_integration_runs_after_incident_builder():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text()
    routing_collector = text.index("-m infra_assurance.routing_ownership")
    alert_scope = text.index("-m infra_assurance.alert_scope_runtime")
    incident = text.index("-m infra_assurance.incident_runtime")
    integration = text.index("-m infra_assurance.routing_context_integration")
    assert routing_collector < alert_scope < incident < integration
    assert "--routing /var/lib/infra-assurance/evidence/kubernetes-routing-ownership.json" in text
    assert "--inventory /var/lib/infra-assurance/evidence/inventory.json" in text
    assert "--incident /var/lib/infra-assurance/evidence/incident-candidates.json" in text


def test_routing_context_integration_has_no_query_capable_client():
    text = (ROOT / "src" / "infra_assurance" / "routing_context_integration.py").read_text()
    for marker in ("subprocess", "kubectl", "urllib", "requests.", "httpx"):
        assert marker not in text


def test_package_exposes_routing_context_cli_and_no_rbac_edit_is_needed():
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'iia-routing-context = "infra_assurance.routing_context_integration:main"' in pyproject

    rbac = (ROOT / "deploy" / "kubernetes" / "observer-rbac.yaml").read_text()
    assert "routing_context" not in rbac
    assert "routing-context" not in rbac