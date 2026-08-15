from __future__ import annotations

import json
from copy import deepcopy

from infra_assurance.routing_context_integration import (
    enrich_incidents_with_routing,
    enrich_inventory_with_routing,
)


def _entity(kind: str, namespace: str, name: str, selector_service: str | None = None) -> dict:
    services = []
    if selector_service:
        services.append(
            {
                "subject": selector_service,
                "basis": "SERVICE_SELECTOR_MATCH_INFERENCE",
                "evidence_ids": [f"selector-{name}"],
            }
        )
    return {
        "entity_id": f"id-{name}",
        "entity_type": "KUBERNETES_WORKLOAD",
        "subject": {
            "system": "kubernetes",
            "cluster": "k3s-main",
            "api_group": "apps",
            "kind": kind,
            "namespace": namespace,
            "name": name,
        },
        "observed": {
            "existence": "PRESENT",
            "observation_status": "COMPLETE",
            "freshness": "CURRENT",
            "observed_at": "2026-08-15T12:00:00Z",
            "expires_at": "2026-08-15T12:05:00Z",
            "evidence_id": f"observed-{name}",
            "attributes": {},
        },
        "declared": {
            "coverage": "OUTSIDE_DECLARED_SCOPE",
            "comparison": None,
            "evidence_id": None,
            "source_id": None,
            "revision": None,
        },
        "relationships": {
            "services": services,
            "ingress_route_candidates": [],
            "persistent_volume_claims": [],
        },
        "recent_change": {"state": "UNCHANGED", "items": []},
        "attention": [],
        "evidence_ids": [f"observed-{name}"],
    }


def _inventory(entities: list[dict]) -> dict:
    return {
        "inventory_version": "0.3",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T12:00:00Z",
        "mutation_allowed": False,
        "scope": {
            "entity_type": "KUBERNETES_WORKLOAD",
            "workload_kinds": ["Deployment", "StatefulSet", "DaemonSet"],
        },
        "summary": {
            "workloads_total": len(entities),
            "namespaces_total": 1,
            "declared_workloads": 0,
            "workloads_in_sync": 0,
            "workloads_outside_declared_scope": len(entities),
            "workloads_with_attention": 0,
            "workloads_changed_in_latest_diff": 0,
            "service_links": sum(len(x["relationships"]["services"]) for x in entities),
            "ingress_route_candidates": 0,
            "pvc_links": 0,
            "related_drift_subjects": 0,
        },
        "namespace_counts": {"monitoring": len(entities)},
        "entities": entities,
    }


def _routing(routes: list[dict], overall: str = "COMPLETE") -> dict:
    return {
        "routing_ownership_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T12:00:01Z",
        "mutation_allowed": False,
        "source_status": {"overall": overall},
        "service_routes": routes,
    }


def _route(service: str, workloads: list[tuple[str, int]], state: str = "RESOLVED_WORKLOAD_ROUTING", completeness: str = "COMPLETE") -> dict:
    resolved = [
        {
            "subject": subject,
            "pod_targets": pods,
            "basis": [
                "ENDPOINTSLICE_SERVICE_NAME_LABEL",
                "ENDPOINT_TARGET_REF",
                "POD_CONTROLLER_OWNER_REFERENCE",
                "CURRENT_WORKLOAD_OBSERVATION",
            ],
            "evidence_ids": [f"route-{subject}"],
        }
        for subject, pods in workloads
    ]
    return {
        "service": service,
        "service_observation": "PRESENT",
        "endpoint_slices": ["EndpointSlice/monitoring/example"],
        "paths": [
            {
                "resolution": "RESOLVED_WORKLOAD" if workloads else "NON_POD_TARGET",
                "evidence_ids": ["route-path"],
            }
        ],
        "resolved_workloads": resolved,
        "scope_completeness": completeness,
        "state": state,
    }


def _incident(service: str, workload_subject: str | None = None) -> dict:
    workloads = []
    if workload_subject:
        workloads.append(
            {
                "subject": workload_subject,
                "basis": ["SERVICE_SELECTOR_MATCH_INFERENCE"],
                "observed_freshness": "CURRENT",
                "declared_coverage": "OUTSIDE_DECLARED_SCOPE",
                "declared_comparison": None,
                "prometheus_runtime_state": None,
                "evidence_ids": ["selector-evidence"],
            }
        )
    return {
        "incident_candidates_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T12:00:02Z",
        "mutation_allowed": False,
        "source_status": {
            "alert_attention": "COMPLETE",
            "kubernetes_events": "COMPLETE",
            "change_context": "COMPLETE",
            "drift": "EVALUATED",
            "inventory": "COMPLETE",
        },
        "summary": {
            "alert_attention_records": 1,
            "incident_candidates": 1,
            "active_candidates": 1,
            "suppressed_candidates": 0,
            "unknown_candidates": 0,
            "candidates_with_related_warning_events": 0,
            "candidates_with_exact_recent_change": 0,
            "candidates_with_exact_drift": 0,
            "candidates_with_related_workloads": int(bool(workloads)),
            "candidates_requiring_live_verification": 1,
        },
        "recommended_next_evidence_targets": [],
        "candidates": [
            {
                "candidate_id": "candidate-1",
                "scope": {"type": "SERVICE", "subject": service, "basis": ["TEST"]},
                "state": "ACTIVE",
                "alert_count": 1,
                "alerts": [],
                "event_correlation_statuses": ["NO_DIRECT_EVENT_MATCH"],
                "related_warning_events": [],
                "recent_changes": [],
                "drift_attention": [],
                "impact_context": {
                    "related_workloads_total": len(workloads),
                    "related_workloads": workloads,
                    "related_workloads_truncated": False,
                    "ingress_route_candidates": [],
                    "ingress_route_candidates_truncated": False,
                    "persistent_volume_claims": [],
                    "persistent_volume_claims_truncated": False,
                    "platform_context": None,
                    "basis": ["SERVICE_SELECTOR_MATCH_INFERENCE"] if workloads else [],
                    "caveat": "selector inference",
                },
                "recommended_checks": [
                    {
                        "code": "VERIFY_SERVICE_ENDPOINT_OWNERSHIP",
                        "target": "KUBERNETES_ENDPOINTSLICE_POD",
                        "check": "verify",
                        "rationale": "selector inference only",
                        "live_verification_required": True,
                        "evidence_ids": [],
                    }
                ],
                "evidence_ids": [],
                "caveats": [],
            }
        ],
        "unassociated_change_unknowns": [],
        "unassociated_required_live_verification": [],
        "caveats": [],
    }


def test_inventory_keeps_selector_inference_and_adds_separate_routing_relation():
    service = "Service/monitoring/grafana"
    entity = _entity("Deployment", "monitoring", "grafana", service)
    result = enrich_inventory_with_routing(
        _inventory([entity]),
        _routing([_route(service, [("Deployment/monitoring/grafana", 1)])]),
    )
    workload = result["entities"][0]
    assert result["inventory_version"] == "0.4"
    assert result["routing_ownership_source_status"] == "COMPLETE"
    assert workload["relationships"]["services"][0]["basis"] == "SERVICE_SELECTOR_MATCH_INFERENCE"
    routing_link = workload["relationships"]["routing_services"][0]
    assert routing_link["subject"] == service
    assert routing_link["state"] == "RESOLVED_WORKLOAD_ROUTING"
    assert routing_link["pod_targets"] == 1


def test_loki_headless_multi_controller_routing_is_preserved_on_both_workloads():
    service = "Service/monitoring/loki-headless"
    entities = [
        _entity("StatefulSet", "monitoring", "loki", service),
        _entity("DaemonSet", "monitoring", "loki-canary", service),
    ]
    result = enrich_inventory_with_routing(
        _inventory(entities),
        _routing(
            [
                _route(
                    service,
                    [
                        ("StatefulSet/monitoring/loki", 1),
                        ("DaemonSet/monitoring/loki-canary", 3),
                    ],
                )
            ]
        ),
    )
    linked = {
        entity["relationships"]["routing_services"][0]["subject"]
        for entity in result["entities"]
    }
    assert linked == {service}
    assert result["summary"]["routing_service_links"] == 2
    assert result["summary"]["workloads_with_routing_service"] == 2


def test_service_incident_prefers_complete_routing_and_preserves_all_backends():
    service = "Service/monitoring/loki-headless"
    entities = [
        _entity("StatefulSet", "monitoring", "loki", service),
        _entity("DaemonSet", "monitoring", "loki-canary", service),
    ]
    inventory = enrich_inventory_with_routing(
        _inventory(entities),
        _routing(
            [
                _route(
                    service,
                    [
                        ("StatefulSet/monitoring/loki", 1),
                        ("DaemonSet/monitoring/loki-canary", 3),
                    ],
                )
            ]
        ),
    )
    incidents = enrich_incidents_with_routing(
        _incident(service, "StatefulSet/monitoring/loki"),
        inventory,
    )
    candidate = incidents["candidates"][0]
    impact = candidate["impact_context"]
    assert incidents["incident_candidates_version"] == "0.2"
    assert incidents["source_status"]["routing_ownership"] == "COMPLETE"
    assert impact["service_routing"]["selection"] == "PREFERRED_ROUTING_EVIDENCE"
    assert {x["subject"] for x in impact["related_workloads"]} == {
        "StatefulSet/monitoring/loki",
        "DaemonSet/monitoring/loki-canary",
    }
    assert impact["basis"] == ["ENDPOINTSLICE_POD_CONTROLLER_OWNER_ROUTING"]
    assert all(x["code"] != "VERIFY_SERVICE_ENDPOINT_OWNERSHIP" for x in candidate["recommended_checks"])


def test_non_pod_routing_does_not_fall_back_to_selector_workload_claim():
    service = "Service/kube-system/kube-prom-stack-kubelet"
    entity = _entity("DaemonSet", "kube-system", "node-agent", service)
    routing = _routing([
        _route(service, [], state="NON_POD_ROUTING")
    ])
    inventory = enrich_inventory_with_routing(_inventory([entity]), routing)
    incidents = enrich_incidents_with_routing(
        _incident(service, "DaemonSet/kube-system/node-agent"),
        inventory,
    )
    impact = incidents["candidates"][0]["impact_context"]
    assert impact["service_routing"]["state"] == "NON_POD_ROUTING"
    assert impact["service_routing"]["selection"] == "NO_WORKLOAD_ROUTING_CLAIM"
    assert impact["related_workloads_total"] == 0
    assert impact["related_workloads"] == []


def test_namespace_candidate_is_not_promoted_by_similar_service_routing():
    service = "Service/kube-system/kube-prom-stack-kubelet"
    entity = _entity("DaemonSet", "kube-system", "node-agent", service)
    inventory = enrich_inventory_with_routing(
        _inventory([entity]),
        _routing([_route(service, [], state="NON_POD_ROUTING")]),
    )
    incidents = _incident(service)
    incidents["candidates"][0]["scope"] = {
        "type": "NAMESPACE",
        "subject": "Namespace/monitoring",
        "basis": ["CURRENT_NAMESPACE_OBSERVATION"],
    }
    before = deepcopy(incidents["candidates"][0]["impact_context"])
    result = enrich_incidents_with_routing(incidents, inventory)
    after = result["candidates"][0]["impact_context"]
    assert after == before
    assert "service_routing" not in after


def test_integration_projection_contains_no_raw_routing_paths_or_sensitive_fields():
    service = "Service/monitoring/grafana"
    entity = _entity("Deployment", "monitoring", "grafana", service)
    routing = _routing([_route(service, [("Deployment/monitoring/grafana", 1)])])
    result = enrich_inventory_with_routing(_inventory([entity]), routing)
    raw = json.dumps(result)
    for forbidden in ("podIP", "hostIP", "addresses", "annotations", "secretKeyRef", "password", "token"):
        assert forbidden not in raw
    assert '"paths"' not in raw
