from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scope_aware_drilldown_runs_after_routing_context_integration():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text()
    routing = text.index("infra_assurance.routing_context_integration")
    drilldown = text.index("infra_assurance.scope_aware_drilldown")
    assert routing < drilldown


def test_scope_aware_drilldown_is_local_derived_only():
    text = (ROOT / "src" / "infra_assurance" / "scope_aware_drilldown.py").read_text()
    for marker in ("subprocess", "kubectl", "urllib", "requests.", "httpx"):
        assert marker not in text


def test_scope_aware_drilldown_console_script_remains_exposed():
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert 'iia-scope-aware-drilldown = "infra_assurance.scope_aware_drilldown:main"' in pyproject
