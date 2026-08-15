from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rbac_adds_read_only_events_without_secret_or_mutation_access():
    text = (ROOT / "deploy" / "kubernetes" / "observer-rbac.yaml").read_text(encoding="utf-8")
    assert "- events" in text
    assert 'verbs: ["get", "list", "watch"]' in text
    assert "secrets" not in text.lower().split("kind: Secret", 1)[0]


def test_bootstrap_verifies_event_read_and_event_write_denial():
    text = (ROOT / "scripts" / "bootstrap-observer.sh").read_text(encoding="utf-8")
    assert "assert_can_i yes list events --all-namespaces" in text
    assert "assert_can_i no create events -n default" in text
    assert "assert_can_i no list secrets --all-namespaces" in text
    assert "IIA_EVENT_WINDOW_SECONDS=${EVENT_WINDOW_SECONDS}" in text
    assert "IIA_EVENT_MAX_RECORDS=${EVENT_MAX_RECORDS}" in text


def test_systemd_emits_event_runtime_and_correlation_artifacts():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text(encoding="utf-8")
    assert "--kubernetes-event-runtime-out /var/lib/infra-assurance/evidence/kubernetes-event-runtime.json" in text
    assert "--kubernetes-event-runtime-summary-out /var/lib/infra-assurance/evidence/kubernetes-event-runtime.md" in text
    assert "--event-correlation-out /var/lib/infra-assurance/evidence/kubernetes-event-correlation.json" in text
    assert "--event-correlation-summary-out /var/lib/infra-assurance/evidence/kubernetes-event-correlation.md" in text


def test_runtime_builds_alert_attention_before_event_correlation():
    text = (ROOT / "src" / "infra_assurance" / "kubernetes_runtime.py").read_text(encoding="utf-8")
    attention_pos = text.index("alert_attention = build_alert_attention")
    event_pos = text.index("kubernetes_event_runtime = build_kubernetes_event_runtime")
    correlation_pos = text.index("event_correlation = build_event_correlation")
    assert attention_pos < event_pos < correlation_pos
