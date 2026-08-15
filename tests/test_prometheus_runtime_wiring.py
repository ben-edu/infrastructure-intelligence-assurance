from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_systemd_emits_prometheus_runtime_artifacts():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text(
        encoding="utf-8"
    )
    assert "--prometheus-runtime-out /var/lib/infra-assurance/evidence/prometheus-runtime.json" in text
    assert "--prometheus-runtime-summary-out /var/lib/infra-assurance/evidence/prometheus-runtime.md" in text


def test_runtime_uses_namespaced_port_qualified_get_only_service_proxy_role():
    text = (ROOT / "deploy" / "kubernetes" / "observer-rbac.yaml").read_text(
        encoding="utf-8"
    )
    assert "kind: Role\nmetadata:\n  name: infra-assurance-observability-proxy\n  namespace: monitoring" in text
    role_fragment = text.split("kind: Role\nmetadata:\n  name: infra-assurance-observability-proxy", 1)[1].split("---", 1)[0]
    assert "- services/proxy" in role_fragment
    assert "resourceNames:" in role_fragment
    assert "- kube-prom-stack-prometheus:9090" in role_fragment
    assert 'verbs: ["get"]' in role_fragment
    assert "create" not in role_fragment
    assert "update" not in role_fragment
    assert "patch" not in role_fragment
    assert "delete" not in role_fragment


def test_bootstrap_verifies_exact_port_qualified_proxy_scope_and_retains_secret_denial():
    text = (ROOT / "scripts" / "bootstrap-observer.sh").read_text(encoding="utf-8")
    assert 'PROMETHEUS_PROXY_NAME="${PROMETHEUS_SERVICE}:${PROMETHEUS_PORT}"' in text
    assert 'assert_can_i yes get "services/${PROMETHEUS_PROXY_NAME}" --subresource=proxy -n "${PROMETHEUS_NAMESPACE}"' in text
    assert 'assert_can_i no get services/not-authorized:9090 --subresource=proxy -n "${PROMETHEUS_NAMESPACE}"' in text
    assert 'assert_can_i no get "services/${PROMETHEUS_PROXY_NAME}" --subresource=proxy -n default' in text
    assert 'assert_can_i no get "services/${PROMETHEUS_SERVICE}" --subresource=proxy -n "${PROMETHEUS_NAMESPACE}"' in text
    assert "assert_can_i no list secrets --all-namespaces" in text
    assert '"${PROMETHEUS_PORT}" != "9090"' in text
    assert "IIA_PROMETHEUS_NAMESPACE=${PROMETHEUS_NAMESPACE}" in text
    assert "IIA_PROMETHEUS_SERVICE=${PROMETHEUS_SERVICE}" in text
    assert "IIA_PROMETHEUS_PORT=${PROMETHEUS_PORT}" in text


def test_runtime_is_built_before_inventory_attachment():
    text = (ROOT / "src" / "infra_assurance" / "kubernetes_runtime.py").read_text(
        encoding="utf-8"
    )
    runtime_pos = text.index("prometheus_runtime = build_prometheus_runtime_intelligence")
    inventory_pos = text.index("inventory = build_operational_inventory")
    attach_pos = text.index("inventory = attach_prometheus_runtime")
    assert runtime_pos < inventory_pos < attach_pos
