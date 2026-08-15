from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rule_integration_runs_after_rule_context_collection():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text()
    collector = text.index("infra_assurance.prometheus_rule_context --incident")
    integration = text.index("infra_assurance.prometheus_rule_context_integration")
    assert collector < integration
    assert "--rule-context /var/lib/infra-assurance/evidence/prometheus-rule-context.json" in text
    assert "--summary /var/lib/infra-assurance/evidence/incident-candidates.md" in text


def test_rule_integration_is_derived_only_and_has_no_query_client():
    text = (
        ROOT
        / "src"
        / "infra_assurance"
        / "prometheus_rule_context_integration.py"
    ).read_text()
    for marker in (
        "subprocess",
        "kubectl",
        "_proxy_get_json",
        "_proxy_path",
        "requests.",
        "httpx",
        "urllib",
        "socket",
    ):
        assert marker not in text


def test_package_exposes_rule_integration_cli_and_current_version():
    pyproject = (ROOT / "pyproject.toml").read_text()
    init = (ROOT / "src" / "infra_assurance" / "__init__.py").read_text()
    assert 'version = "0.18.0"' in pyproject
    assert '__version__ = "0.18.0"' in init
    assert (
        'iia-prometheus-rule-integration = '
        '"infra_assurance.prometheus_rule_context_integration:main"'
    ) in pyproject


def test_rule_integration_requires_no_rbac_marker():
    rbac = (ROOT / "deploy" / "kubernetes" / "observer-rbac.yaml").read_text()
    assert "prometheus-rule-integration" not in rbac
    assert "prometheus_rule_context_integration" not in rbac
