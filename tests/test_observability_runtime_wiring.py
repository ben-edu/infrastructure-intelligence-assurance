from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_systemd_emits_observability_coverage_artifacts():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text(
        encoding="utf-8"
    )
    assert "--observability-coverage-out /var/lib/infra-assurance/evidence/observability-coverage.json" in text
    assert "--observability-coverage-summary-out /var/lib/infra-assurance/evidence/observability-coverage.md" in text


def test_observer_rbac_adds_only_read_access_for_prometheus_operator_resources():
    text = (ROOT / "deploy" / "kubernetes" / "observer-rbac.yaml").read_text(
        encoding="utf-8"
    )
    assert 'apiGroups: ["monitoring.coreos.com"]' in text
    assert "- prometheuses" in text
    assert "- servicemonitors" in text
    assert "- podmonitors" in text
    assert 'verbs: ["get", "list", "watch"]' in text
    assert "create" not in text
    assert "update" not in text
    assert "patch" not in text
    assert "delete" not in text


def test_bootstrap_verifies_new_reads_and_existing_write_denials():
    text = (ROOT / "scripts" / "bootstrap-observer.sh").read_text(encoding="utf-8")
    assert "assert_can_i yes list prometheuses.monitoring.coreos.com --all-namespaces" in text
    assert "assert_can_i yes list servicemonitors.monitoring.coreos.com --all-namespaces" in text
    assert "assert_can_i yes list podmonitors.monitoring.coreos.com --all-namespaces" in text
    assert "assert_can_i no list secrets --all-namespaces" in text
    assert "assert_can_i no create servicemonitors.monitoring.coreos.com -n monitoring" in text


def test_runtime_builds_coverage_before_inventory_enrichment():
    text = (ROOT / "src" / "infra_assurance" / "kubernetes_runtime.py").read_text(
        encoding="utf-8"
    )
    coverage_pos = text.index("observability_coverage = build_prometheus_operator_coverage")
    inventory_pos = text.index("inventory = build_operational_inventory")
    attach_pos = text.index("inventory = attach_observability_coverage")
    assert coverage_pos < inventory_pos < attach_pos
