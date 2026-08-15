from __future__ import annotations

from pathlib import Path

from infra_assurance.routing_ownership import ENDPOINTSLICE_JSONPATH, OWNER_JSONPATH

ROOT = Path(__file__).resolve().parents[1]


def test_rbac_allows_endpointslice_list_but_only_exact_get_capability_for_pods_and_replicasets():
    text = (ROOT / "deploy" / "kubernetes" / "observer-rbac.yaml").read_text(encoding="utf-8")

    pod_rule = text.split('resources:\n      - pods\n', 1)[1].split("---", 1)[0]
    assert 'verbs: ["get"]' in pod_rule
    assert "list" not in pod_rule
    assert "watch" not in pod_rule

    rs_rule = text.split('resources:\n      - replicasets\n', 1)[1].split("---", 1)[0]
    assert 'verbs: ["get"]' in rs_rule
    assert "list" not in rs_rule
    assert "watch" not in rs_rule

    discovery_rule = text.split('apiGroups: ["discovery.k8s.io"]', 1)[1].split("---", 1)[0]
    assert "- endpointslices" in discovery_rule
    assert 'verbs: ["list"]' in discovery_rule
    assert "secrets" not in discovery_rule


def test_projection_queries_exclude_pod_spec_addresses_uid_and_free_form_metadata():
    assert ".spec" not in OWNER_JSONPATH
    assert ".status" not in OWNER_JSONPATH
    assert ".metadata.labels" not in OWNER_JSONPATH
    assert ".metadata.annotations" not in OWNER_JSONPATH
    assert ".metadata.uid" not in OWNER_JSONPATH

    assert ".addresses" not in ENDPOINTSLICE_JSONPATH
    assert ".hostname" not in ENDPOINTSLICE_JSONPATH
    assert ".nodeName" not in ENDPOINTSLICE_JSONPATH
    assert ".zone" not in ENDPOINTSLICE_JSONPATH
    assert ".metadata.annotations" not in ENDPOINTSLICE_JSONPATH
    assert ".metadata.uid" not in ENDPOINTSLICE_JSONPATH
    assert "kubernetes\\.io/service-name" in ENDPOINTSLICE_JSONPATH


def test_systemd_emits_routing_ownership_before_existing_incident_projection():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text(encoding="utf-8")
    routing = "ExecStartPost=/usr/bin/python3 -m infra_assurance.routing_ownership"
    incident = "ExecStartPost=/usr/bin/python3 -m infra_assurance.incident_runtime"
    assert routing in text
    assert "--snapshot /var/lib/infra-assurance/evidence/kubernetes.json" in text
    assert "--out /var/lib/infra-assurance/evidence/kubernetes-routing-ownership.json" in text
    assert "--summary-out /var/lib/infra-assurance/evidence/kubernetes-routing-ownership.md" in text
    assert text.index(routing) < text.index(incident)


def test_routing_artifact_is_not_yet_an_incident_input():
    text = (ROOT / "systemd" / "infra-assurance-kubernetes.service").read_text(encoding="utf-8")
    incident_line = next(
        line
        for line in text.splitlines()
        if line.startswith("ExecStartPost=/usr/bin/python3 -m infra_assurance.incident_runtime")
    )
    assert "kubernetes-routing-ownership" not in incident_line
