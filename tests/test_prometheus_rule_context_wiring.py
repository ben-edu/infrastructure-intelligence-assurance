from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_prometheus_rule_context_runs_after_scope_aware_drilldown():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text()
    routing = text.index("infra_assurance.routing_context_integration")
    drilldown = text.index("infra_assurance.scope_aware_drilldown")
    rule_context = text.index("infra_assurance.prometheus_rule_context")
    assert routing < drilldown < rule_context
    assert "--incident /var/lib/infra-assurance/evidence/incident-candidates.json" in text
    assert "--out /var/lib/infra-assurance/evidence/prometheus-rule-context.json" in text
    assert "--summary-out /var/lib/infra-assurance/evidence/prometheus-rule-context.md" in text


def test_package_exposes_rule_context_cli():
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'iia-prometheus-rule-context = "infra_assurance.prometheus_rule_context:main"' in pyproject


def test_rule_context_reuses_prometheus_service_proxy_boundary_without_rbac_edit():
    module = (ROOT / "src" / "infra_assurance" / "prometheus_rule_context.py").read_text()
    assert "_proxy_get_json" in module
    assert "_proxy_path" in module
    assert '"type", "alert"' in module
    assert '"exclude_alerts", "true"' in module
    assert '"rule_name[]", name' in module
    for marker in ("requests.", "httpx", "urllib.request", "socket", "LOKI"):
        assert marker not in module

    rbac = (ROOT / "deploy" / "kubernetes" / "observer-rbac.yaml").read_text()
    assert "prometheus-rule-context" not in rbac
    assert "prometheus_rule_context" not in rbac
