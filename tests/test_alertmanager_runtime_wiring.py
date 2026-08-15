from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rbac_allows_only_exact_reviewed_observability_proxy_names():
    text = (ROOT / "deploy" / "kubernetes" / "observer-rbac.yaml").read_text(encoding="utf-8")
    role = text.split("kind: Role\nmetadata:\n  name: infra-assurance-observability-proxy", 1)[1].split("---", 1)[0]
    assert "- services/proxy" in role
    assert "- kube-prom-stack-prometheus:9090" in role
    assert "- kube-prom-stack-alertmanager:9093" in role
    assert 'verbs: ["get"]' in role
    for verb in ("create", "update", "patch", "delete"):
        assert verb not in role


def test_bootstrap_pins_alertmanager_and_verifies_denials():
    text = (ROOT / "scripts" / "bootstrap-observer.sh").read_text(encoding="utf-8")
    assert 'ALERTMANAGER_SERVICE="${ALERTMANAGER_SERVICE:-kube-prom-stack-alertmanager}"' in text
    assert 'ALERTMANAGER_PORT="${ALERTMANAGER_PORT:-9093}"' in text
    assert 'assert_can_i yes get "services/${ALERTMANAGER_PROXY_NAME}" --subresource=proxy -n "${ALERTMANAGER_NAMESPACE}"' in text
    assert 'assert_can_i no get "services/${ALERTMANAGER_PROXY_NAME}" --subresource=proxy -n default' in text
    assert 'assert_can_i no get "services/${ALERTMANAGER_SERVICE}" --subresource=proxy -n "${ALERTMANAGER_NAMESPACE}"' in text
    assert 'assert_can_i no get services/alertmanager-operated:9093 --subresource=proxy -n "${ALERTMANAGER_NAMESPACE}"' in text
    assert "assert_can_i no list secrets --all-namespaces" in text


def test_systemd_emits_alertmanager_and_attention_artifacts():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text(encoding="utf-8")
    assert "--alertmanager-runtime-out /var/lib/infra-assurance/evidence/alertmanager-runtime.json" in text
    assert "--alertmanager-runtime-summary-out /var/lib/infra-assurance/evidence/alertmanager-runtime.md" in text
    assert "--alert-attention-out /var/lib/infra-assurance/evidence/alert-attention.json" in text
    assert "--alert-attention-summary-out /var/lib/infra-assurance/evidence/alert-attention.md" in text


def test_alertmanager_is_built_after_prometheus_and_before_attention_projection():
    text = (ROOT / "src" / "infra_assurance" / "kubernetes_runtime.py").read_text(encoding="utf-8")
    prom = text.index("prometheus_runtime = build_prometheus_runtime_intelligence")
    alertmanager = text.index("alertmanager_runtime = build_alertmanager_runtime_intelligence")
    attention = text.index("alert_attention = build_alert_attention")
    assert prom < alertmanager < attention
