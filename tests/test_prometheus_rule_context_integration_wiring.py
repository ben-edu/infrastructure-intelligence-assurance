from __future__ import annotations

import json
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


def test_rule_integration_extension_schema_is_strict_for_rule_projection():
    schema = json.loads(
        (
            ROOT
            / "schemas"
            / "incident-prometheus-rule-context-integration.schema.json"
        ).read_text()
    )
    assert schema["properties"]["incident_candidates_version"]["const"] == "0.4"
    assert schema["properties"]["mutation_allowed"]["const"] is False
    integration = schema["properties"]["prometheus_rule_context_integration"]
    assert integration["properties"]["version"]["const"] == "0.1"
    assert integration["properties"]["mode"]["const"] == "EXACT_COMPLETE_ONLY"

    rule = schema["$defs"]["ruleProjection"]
    assert rule["additionalProperties"] is False
    projected = set(rule["properties"])
    for forbidden in (
        "query",
        "expr",
        "expression",
        "labels",
        "annotations",
        "file",
        "alerts",
        "lastError",
        "runbook_url",
        "dashboard_url",
        "token",
        "password",
    ):
        assert forbidden not in projected
