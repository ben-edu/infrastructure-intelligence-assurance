from __future__ import annotations

from infra_assurance.routing_context_integration import (
    enrich_incidents_with_routing,
    enrich_inventory_with_routing,
)


def _entity(service: str) -> dict:
    return {
        "entity_id": "api",
        "entity_type": "KUBERNETES_WORKLOAD",
        "subject": {
            "system": "kubernetes",
            "cluster": "k3s-main",
            "api_group": "apps",
            "kind": "Deployment",
            "namespace": "apps",
            "name": "api",
        },
        "observed": {
            "existence": "PRESENT",
            "observation_status": "COMPLETE",
            "freshness": "CURRENT",
            "observed_at": "2026-08-15T12:00:00Z",
            "expires_at": "2026-08-15T12:05:00Z",
            "evidence_id": "workload-observed",
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
            "services": [
                {
                    "subject": service,
                    "basis": "SERVICE_SELECTOR_MATCH_INFERENCE",
                    "evidence_ids": ["selector-evidence"],
                }
            ],
            "ingress_route_candidates": [],
            "persistent_volume_claims": [],
        },
        "recent_change": {"state": "UNCHANGED", "items": []},
        "attention": [],
        "evidence_ids": ["workload-observed", "selector-evidence"],
    }


def _inventory(service: str) -> dict:
    return {
        "inventory_version": "0.3",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T12:00:00Z",
        "mutation_allowed": False,
        "scope": {"entity_type": "KUBERNETES_WORKLOAD", "workload_kinds": ["Deployment"]},
        "summary": {
            "workloads_total": 1,
            "namespaces_total": 1,
            "declared_workloads": 0,
            "workloads_in_sync": 0,
            "workloads_outside_declared_scope": 1,
            "workloads_with_attention": 0,
            "workloads_changed_in_latest_diff": 0,
            "service_links": 1,
            "ingress_route_candidates": 0,
            "pvc_links": 0,
            "related_drift_subjects": 0,
        },
        "namespace_counts": {"apps": 1},
        "entities": [_entity(service)],
    }


def _routing(service: str, *, overall: str, include_route: bool) -> dict:
    routes = []
    if include_route:
        routes.append(
            {
                "service": service,
                "service_observation": "PRESENT",
                "endpoint_slices": ["EndpointSlice/apps/api"],
                "paths": [{"resolution": "RESOLVED_WORKLOAD", "evidence_ids": ["route-path"]}],
                "resolved_workloads": [
                    {
                        "subject": "Deployment/apps/api",
                        "pod_targets": 1,
                        "basis": ["ENDPOINT_TARGET_REF", "POD_CONTROLLER_OWNER_REFERENCE"],
                        "evidence_ids": ["route-workload"],
                    }
                ],
                "scope_completeness": "COMPLETE",
                "state": "RESOLVED_WORKLOAD_ROUTING",
            }
        )
    return {
        "routing_ownership_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T12:00:01Z",
        "mutation_allowed": False,
        "source_status": {"overall": overall},
        "service_routes": routes,
    }


def _incident(service: str) -> dict:
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
            "candidates_with_related_workloads": 1,
            "candidates_requiring_live_verification": 1,
        },
        "recommended_next_evidence_targets": [],
        "candidates": [
            {
                "candidate_id": "candidate-api",
                "scope": {"type": "SERVICE", "subject": service, "basis": ["TEST"]},
                "state": "ACTIVE",
                "alert_count": 1,
                "alerts": [],
                "event_correlation_statuses": ["NO_DIRECT_EVENT_MATCH"],
                "related_warning_events": [],
                "recent_changes": [],
                "drift_attention": [],
                "impact_context": {
                    "related_workloads_total": 1,
                    "related_workloads": [
                        {
                            "subject": "Deployment/apps/api",
                            "basis": ["SERVICE_SELECTOR_MATCH_INFERENCE"],
                            "observed_freshness": "CURRENT",
                            "declared_coverage": "OUTSIDE_DECLARED_SCOPE",
                            "declared_comparison": None,
                            "prometheus_runtime_state": None,
                            "evidence_ids": ["selector-evidence"],
                        }
                    ],
                    "related_workloads_truncated": False,
                    "ingress_route_candidates": [],
                    "ingress_route_candidates_truncated": False,
                    "persistent_volume_claims": [],
                    "persistent_volume_claims_truncated": False,
                    "platform_context": None,
                    "basis": ["SERVICE_SELECTOR_MATCH_INFERENCE"],
                    "caveat": "selector inference",
                },
                "recommended_checks": [],
                "evidence_ids": ["selector-evidence"],
                "caveats": [],
            }
        ],
        "unassociated_change_unknowns": [],
        "unassociated_required_live_verification": [],
        "caveats": [],
    }


def test_missing_exact_route_keeps_selector_inference_as_weaker_fallback():
    service = "Service/apps/api"
    inventory = enrich_inventory_with_routing(
        _inventory(service),
        _routing(service, overall="COMPLETE", include_route=False),
    )
    incidents = enrich_incidents_with_routing(_incident(service), inventory)
    impact = incidents["candidates"][0]["impact_context"]
    assert impact["service_routing"]["state"] == "NOT_OBSERVED"
    assert impact["service_routing"]["selection"] == "SELECTOR_INFERENCE_FALLBACK"
    assert impact["related_workloads_total"] == 1
    assert impact["related_workloads"][0]["basis"] == ["SERVICE_SELECTOR_MATCH_INFERENCE"]


def test_partial_routing_source_does_not_upgrade_resolved_route_to_strong_relation():
    service = "Service/apps/api"
    inventory = enrich_inventory_with_routing(
        _inventory(service),
        _routing(service, overall="PARTIAL", include_route=True),
    )
    assert inventory["routing_ownership_source_status"] == "PARTIAL"
    assert inventory["entities"][0]["relationships"]["routing_services"] == []

    incidents = enrich_incidents_with_routing(_incident(service), inventory)
    impact = incidents["candidates"][0]["impact_context"]
    assert impact["service_routing"]["selection"] == "ROUTING_SOURCE_INCOMPLETE"
    assert impact["related_workloads_total"] == 1
    assert impact["related_workloads"][0]["basis"] == ["SERVICE_SELECTOR_MATCH_INFERENCE"]
