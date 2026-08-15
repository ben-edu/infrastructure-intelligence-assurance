from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scope_validation_runs_after_routing_and_before_incident_grouping():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text(
        encoding="utf-8"
    )
    routing = "ExecStartPost=/usr/bin/python3 -m infra_assurance.routing_ownership"
    scope = "ExecStartPost=/usr/bin/python3 -m infra_assurance.alert_scope_runtime"
    incident = "ExecStartPost=/usr/bin/python3 -m infra_assurance.incident_runtime"

    assert routing in text
    assert scope in text
    assert incident in text
    assert text.index(routing) < text.index(scope) < text.index(incident)

    scope_line = next(
        line
        for line in text.splitlines()
        if line.startswith(scope)
    )
    assert "--attention /var/lib/infra-assurance/evidence/alert-attention.json" in scope_line
    assert "--snapshot /var/lib/infra-assurance/evidence/kubernetes.json" in scope_line
    assert "--event-runtime /var/lib/infra-assurance/evidence/kubernetes-event-runtime.json" in scope_line
    assert "--event-correlation-out /var/lib/infra-assurance/evidence/kubernetes-event-correlation.json" in scope_line


def test_scope_validation_performs_no_infrastructure_query():
    runtime = (ROOT / "src" / "infra_assurance" / "alert_scope_runtime.py").read_text(
        encoding="utf-8"
    )
    validator = (ROOT / "src" / "infra_assurance" / "alert_scope_validation.py").read_text(
        encoding="utf-8"
    )
    combined = runtime + validator

    for marker in (
        "subprocess",
        "kubectl",
        "urllib",
        "requests.",
        "httpx",
    ):
        assert marker not in combined


def test_scope_validation_slice_does_not_change_kubernetes_rbac():
    text = (ROOT / "deploy" / "kubernetes" / "observer-rbac.yaml").read_text(
        encoding="utf-8"
    )
    assert 'resources:\n      - pods\n    verbs: ["get"]' in text
    assert 'resources:\n      - replicasets\n    verbs: ["get"]' in text
    assert 'resources:\n      - endpointslices\n    verbs: ["list"]' in text
    assert "secrets\n" not in text
