from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_systemd_builds_incident_candidates_as_derived_post_step():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text(encoding="utf-8")
    assert "ExecStartPost=/usr/bin/python3 -m infra_assurance.incident_runtime" in text
    assert "--alert-attention /var/lib/infra-assurance/evidence/alert-attention.json" in text
    assert "--event-correlation /var/lib/infra-assurance/evidence/kubernetes-event-correlation.json" in text
    assert "--inventory /var/lib/infra-assurance/evidence/inventory.json" in text
    assert "--change-context /var/lib/infra-assurance/evidence/change-context.json" in text
    assert "--out /var/lib/infra-assurance/evidence/incident-candidates.json" in text
    assert "--summary-out /var/lib/infra-assurance/evidence/incident-candidates.md" in text


def test_incident_runtime_performs_no_infrastructure_query():
    runtime = (ROOT / "src" / "infra_assurance" / "incident_runtime.py").read_text(encoding="utf-8")
    builder = (ROOT / "src" / "infra_assurance" / "incident_candidates.py").read_text(encoding="utf-8")
    combined = runtime + builder
    assert "subprocess" not in combined
    assert "kubectl" not in combined
    assert "urllib" not in combined
    assert "requests." not in combined


def test_incident_candidates_do_not_consume_unaccepted_routing_ownership_artifact():
    service = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text(encoding="utf-8")
    incident_line = next(
        line
        for line in service.splitlines()
        if line.startswith("ExecStartPost=/usr/bin/python3 -m infra_assurance.incident_runtime")
    )
    assert "kubernetes-routing-ownership" not in incident_line
    runtime = (ROOT / "src" / "infra_assurance" / "incident_runtime.py").read_text(encoding="utf-8")
    builder = (ROOT / "src" / "infra_assurance" / "incident_candidates.py").read_text(encoding="utf-8")
    assert "routing_ownership" not in runtime + builder
