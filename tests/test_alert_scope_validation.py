from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from infra_assurance.alert_scope_validation import validate_alert_attention_scopes

ROOT = Path(__file__).resolve().parents[1]


def _collection(kind: str, evidence_id: str, status: str = "COMPLETE") -> dict:
    return {
        "evidence_id": evidence_id,
        "existence": "PRESENT" if status == "COMPLETE" else "UNKNOWN",
        "observation_status": status,
        "subject": {
            "kind": f"{kind}Collection",
            "namespace": None,
            "name": "*",
        },
    }


def _resource(
    kind: str,
    name: str,
    evidence_id: str,
    namespace: str | None = None,
) -> dict:
    return {
        "evidence_id": evidence_id,
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "subject": {
            "kind": kind,
            "namespace": namespace,
            "name": name,
        },
    }


def _snapshot(*resources: dict, service_status: str = "COMPLETE") -> dict:
    return {
        "cluster_id": "k3s-main",
        "evidence": [
            _collection("Namespace", "ns-collection"),
            _collection("Node", "node-collection"),
            _collection("Service", "svc-collection", service_status),
            *resources,
        ],
    }


def _attention(
    *,
    scope_type: str,
    subject: str,
    labels: dict[str, str],
) -> dict:
    return {
        "alert_attention_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T12:00:00Z",
        "mutation_allowed": False,
        "source_status": {
            "prometheus": "COMPLETE",
            "alertmanager": "COMPLETE",
        },
        "summary": {
            "attention_total": 1,
            "scope_workload": int(scope_type == "WORKLOAD"),
            "scope_node": int(scope_type == "NODE"),
            "scope_service": int(scope_type == "SERVICE"),
            "scope_namespace": int(scope_type == "NAMESPACE"),
            "scope_platform": int(scope_type == "PLATFORM"),
        },
        "attention": [
            {
                "attention_id": "attention-1",
                "alertmanager_alert_id": "am-1",
                "prometheus_alert_id": "prom-1",
                "correlation_status": "MATCHED",
                "state": "ACTIVE",
                "handling_state": "ACTIVE",
                "labels": labels,
                "scope": {
                    "type": scope_type,
                    "subject": subject,
                    "basis": ["TEST_SIGNAL_SCOPE"],
                },
                "starts_at": None,
                "updated_at": None,
                "ends_at": None,
                "silence_refs": [],
                "evidence_ids": ["alert-evidence"],
            }
        ],
        "unknowns": [],
        "caveats": [],
    }


def test_exact_observed_service_scope_is_validated():
    source = _attention(
        scope_type="SERVICE",
        subject="Service/monitoring/grafana",
        labels={"namespace": "monitoring", "service": "grafana"},
    )
    result = validate_alert_attention_scopes(
        source,
        _snapshot(
            _resource("Namespace", "monitoring", "ns-monitoring"),
            _resource("Service", "grafana", "svc-grafana", namespace="monitoring"),
        ),
    )

    item = result["attention"][0]
    assert item["scope"]["type"] == "SERVICE"
    assert item["scope"]["subject"] == "Service/monitoring/grafana"
    assert item["scope_validation"]["status"] == "VALIDATED_INFRASTRUCTURE_SUBJECT"
    assert item["scope_validation"]["validated_subject"] == "Service/monitoring/grafana"
    assert "svc-grafana" in item["evidence_ids"]
    assert result["source_status"]["kubernetes_scope"] == "COMPLETE"


def test_unobserved_kubelet_service_signal_falls_back_to_observed_namespace_without_rewrite():
    source = _attention(
        scope_type="SERVICE",
        subject="Service/keycloak/kube-prom-stack-kubelet",
        labels={
            "namespace": "keycloak",
            "service": "kube-prom-stack-kubelet",
            "job": "kubelet",
        },
    )
    result = validate_alert_attention_scopes(
        source,
        _snapshot(
            _resource("Namespace", "keycloak", "ns-keycloak"),
            _resource("Namespace", "kube-system", "ns-kube-system"),
            _resource(
                "Service",
                "kube-prom-stack-kubelet",
                "svc-real-kubelet",
                namespace="kube-system",
            ),
        ),
    )

    item = result["attention"][0]
    assert item["scope"] == {
        "type": "NAMESPACE",
        "subject": "Namespace/keycloak",
        "basis": [
            "ALERTMANAGER_NAMESPACE_LABEL",
            "CURRENT_NAMESPACE_OBSERVATION",
            "SERVICE_SIGNAL_DIMENSION_NOT_OBSERVED",
        ],
    }
    assert item["scope_validation"]["status"] == "UNVERIFIED_SIGNAL_DIMENSION"
    assert item["scope_validation"]["claimed_subject"] == "Service/keycloak/kube-prom-stack-kubelet"
    assert item["scope_validation"]["validated_subject"] == "Namespace/keycloak"
    assert "Service/kube-system/kube-prom-stack-kubelet" not in json.dumps(result)
    warning = next(
        x
        for x in result["unknowns"]
        if x["code"] == "ALERT_SCOPE_SERVICE_SIGNAL_NOT_OBSERVED"
    )
    assert "alert-evidence" in warning["evidence_ids"]


def test_unobserved_namespace_signal_falls_back_to_platform():
    source = _attention(
        scope_type="NAMESPACE",
        subject="Namespace/not-real",
        labels={"namespace": "not-real"},
    )
    result = validate_alert_attention_scopes(source, _snapshot())
    item = result["attention"][0]
    assert item["scope"]["type"] == "PLATFORM"
    assert item["scope"]["subject"] == "Platform/k3s-main"
    assert item["scope_validation"]["status"] == "UNVERIFIED_SIGNAL_DIMENSION"
    assert result["source_status"]["kubernetes_scope"] == "COMPLETE"


def test_observed_node_scope_is_validated_from_cluster_scoped_identity():
    source = _attention(
        scope_type="NODE",
        subject="Node/k3s-worker-01",
        labels={"node": "k3s-worker-01"},
    )
    result = validate_alert_attention_scopes(
        source,
        _snapshot(_resource("Node", "k3s-worker-01", "node-worker-01")),
    )
    item = result["attention"][0]
    assert item["scope"]["type"] == "NODE"
    assert item["scope_validation"]["status"] == "VALIDATED_INFRASTRUCTURE_SUBJECT"
    assert item["scope_validation"]["evidence_ids"] == ["node-worker-01"]


def test_incomplete_service_observation_is_partial_not_absence():
    source = _attention(
        scope_type="SERVICE",
        subject="Service/moodle/example",
        labels={"namespace": "moodle", "service": "example"},
    )
    result = validate_alert_attention_scopes(
        source,
        _snapshot(
            _resource("Namespace", "moodle", "ns-moodle"),
            service_status="FAILED_TO_OBSERVE",
        ),
    )
    item = result["attention"][0]
    assert item["scope"]["subject"] == "Namespace/moodle"
    assert item["scope_validation"]["status"] == "UNVERIFIED_SIGNAL_DIMENSION"
    assert result["source_status"]["kubernetes_scope"] == "FAILED_TO_OBSERVE"
    assert any(
        x["code"] == "ALERT_SCOPE_SERVICE_VALIDATION_INCOMPLETE"
        for x in result["unknowns"]
    )


def test_workload_scope_remains_explicitly_inferred_relation():
    source = _attention(
        scope_type="WORKLOAD",
        subject="Deployment/apps/api",
        labels={"namespace": "apps", "service": "api"},
    )
    result = validate_alert_attention_scopes(source, _snapshot())
    item = result["attention"][0]
    assert item["scope"]["subject"] == "Deployment/apps/api"
    assert item["scope_validation"]["status"] == "INFERRED_RELATION"
    assert item["scope_validation"]["validated_subject"] is None


def test_validated_attention_matches_v02_schema():
    source = _attention(
        scope_type="SERVICE",
        subject="Service/monitoring/grafana",
        labels={"namespace": "monitoring", "service": "grafana"},
    )
    result = validate_alert_attention_scopes(
        source,
        _snapshot(
            _resource("Namespace", "monitoring", "ns-monitoring"),
            _resource("Service", "grafana", "svc-grafana", namespace="monitoring"),
        ),
    )
    schema = json.loads(
        (ROOT / "schemas" / "alert-attention-scope-validated.schema.json").read_text()
    )
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(result)
