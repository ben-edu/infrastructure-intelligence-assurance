from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from .incident_candidates import render_incident_candidates_markdown
from .io_utils import atomic_write_json, atomic_write_text

INVENTORY_ROUTING_VERSION = "0.4"
INCIDENT_ROUTING_VERSION = "0.2"
ROUTING_SECTION_START = "<!-- ROUTING_OWNERSHIP_INTEGRATION_START -->"
ROUTING_SECTION_END = "<!-- ROUTING_OWNERSHIP_INTEGRATION_END -->"


def _workload_subject(entity: dict[str, Any]) -> str:
    subject = entity.get("subject", {})
    namespace = subject.get("namespace")
    if namespace:
        return f"{subject.get('kind')}/{namespace}/{subject.get('name')}"
    return f"{subject.get('kind')}/{subject.get('name')}"


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if isinstance(value, str) and value))


def _route_evidence_ids(route: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for workload in route.get("resolved_workloads", []):
        values.extend(workload.get("evidence_ids", []))
    for path in route.get("paths", []):
        values.extend(path.get("evidence_ids", []))
    return _unique(values)


def _route_projection(route: dict[str, Any]) -> dict[str, Any]:
    return {
        "service": route.get("service"),
        "state": route.get("state", "UNKNOWN"),
        "scope_completeness": route.get("scope_completeness", "PARTIAL"),
        "resolved_workloads": [
            {
                "subject": item.get("subject"),
                "pod_targets": int(item.get("pod_targets", 0)),
                "basis": list(item.get("basis", [])),
                "evidence_ids": list(item.get("evidence_ids", [])),
            }
            for item in route.get("resolved_workloads", [])
            if item.get("subject")
        ],
        "evidence_ids": _route_evidence_ids(route),
    }


def enrich_inventory_with_routing(
    inventory: dict[str, Any],
    routing: dict[str, Any],
) -> dict[str, Any]:
    """Attach accepted routing evidence without replacing selector inference."""
    if inventory.get("cluster_id") != routing.get("cluster_id"):
        raise ValueError("inventory and routing ownership must target the same cluster")

    result = deepcopy(inventory)
    overall = str(routing.get("source_status", {}).get("overall", "FAILED_TO_OBSERVE"))
    route_projections = [_route_projection(route) for route in routing.get("service_routes", [])]
    route_projections.sort(key=lambda item: str(item.get("service") or ""))

    by_workload: dict[str, list[dict[str, Any]]] = {}
    if overall == "COMPLETE":
        for route in route_projections:
            if route["state"] != "RESOLVED_WORKLOAD_ROUTING":
                continue
            if route["scope_completeness"] != "COMPLETE":
                continue
            for workload in route["resolved_workloads"]:
                relation = {
                    "subject": route["service"],
                    "state": route["state"],
                    "scope_completeness": route["scope_completeness"],
                    "pod_targets": workload["pod_targets"],
                    "basis": list(workload["basis"]),
                    "evidence_ids": list(workload["evidence_ids"]),
                }
                by_workload.setdefault(str(workload["subject"]), []).append(relation)

    matched_workloads: set[str] = set()
    routing_links = 0
    for entity in result.get("entities", []):
        subject = _workload_subject(entity)
        relations = sorted(
            by_workload.get(subject, []),
            key=lambda item: str(item.get("subject") or ""),
        )
        entity.setdefault("relationships", {})["routing_services"] = relations
        if relations:
            matched_workloads.add(subject)
            routing_links += len(relations)
            entity["evidence_ids"] = _unique(
                list(entity.get("evidence_ids", []))
                + [eid for relation in relations for eid in relation.get("evidence_ids", [])]
            )

    referenced_workloads = {
        str(workload["subject"])
        for route in route_projections
        if route["state"] == "RESOLVED_WORKLOAD_ROUTING"
        and route["scope_completeness"] == "COMPLETE"
        for workload in route["resolved_workloads"]
    }
    unmatched = sorted(referenced_workloads - matched_workloads)

    state_counts = Counter(route["state"] for route in route_projections)
    summary = dict(result.get("summary", {}))
    summary.update(
        {
            "routing_service_links": routing_links,
            "workloads_with_routing_service": len(matched_workloads),
            "routing_services_resolved": state_counts["RESOLVED_WORKLOAD_ROUTING"],
            "routing_services_non_pod": state_counts["NON_POD_ROUTING"],
            "routing_services_unknown_or_partial": sum(
                route["state"] in {"UNKNOWN", "PARTIAL_ROUTING", "SERVICE_NOT_OBSERVED"}
                or route["scope_completeness"] != "COMPLETE"
                for route in route_projections
            ),
            "routing_workloads_not_in_inventory": len(unmatched),
        }
    )

    result["inventory_version"] = INVENTORY_ROUTING_VERSION
    result["routing_ownership_source_status"] = overall
    result["routing_ownership_generated_at"] = routing.get("generated_at")
    result["routing_service_states"] = route_projections
    result["routing_ownership_unknowns"] = [
        {
            "code": "ROUTING_WORKLOAD_NOT_IN_INVENTORY",
            "subject": subject,
            "statement": "A routing workload subject could not be joined to the current workload inventory.",
        }
        for subject in unmatched
    ]
    result["summary"] = summary
    return result


def _entity_projection(entity: dict[str, Any], *, basis: list[str]) -> dict[str, Any]:
    runtime = entity.get("runtime_observability") or {}
    declared = entity.get("declared") or {}
    observed = entity.get("observed") or {}
    return {
        "subject": _workload_subject(entity),
        "basis": list(basis),
        "observed_freshness": observed.get("freshness", "UNKNOWN"),
        "declared_coverage": declared.get("coverage"),
        "declared_comparison": declared.get("comparison"),
        "prometheus_runtime_state": runtime.get("state"),
        "evidence_ids": list(entity.get("evidence_ids", [])),
    }


def _related_secondary_context(
    entities: list[dict[str, Any]],
    *,
    max_related: int = 20,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool, bool]:
    ingress: dict[str, dict[str, Any]] = {}
    pvcs: dict[str, dict[str, Any]] = {}
    for entity in entities:
        for relation in entity.get("relationships", {}).get("ingress_route_candidates", []):
            subject = relation.get("subject")
            if subject:
                ingress[str(subject)] = {
                    "subject": subject,
                    "basis": relation.get("basis"),
                    "evidence_ids": list(relation.get("evidence_ids", [])),
                }
        for relation in entity.get("relationships", {}).get("persistent_volume_claims", []):
            subject = relation.get("subject")
            if subject:
                pvcs[str(subject)] = {
                    "subject": subject,
                    "basis": relation.get("basis"),
                    "evidence_ids": list(relation.get("evidence_ids", [])),
                }
    return (
        [ingress[key] for key in sorted(ingress)[:max_related]],
        [pvcs[key] for key in sorted(pvcs)[:max_related]],
        len(ingress) > max_related,
        len(pvcs) > max_related,
    )


def _service_routing_projection(
    *,
    service: str,
    inventory: dict[str, Any],
) -> dict[str, Any]:
    source_status = str(inventory.get("routing_ownership_source_status") or "FAILED_TO_OBSERVE")
    route = next(
        (
            item
            for item in inventory.get("routing_service_states", [])
            if item.get("service") == service
        ),
        None,
    )
    if route is None:
        return {
            "source_status": source_status,
            "service": service,
            "state": "NOT_OBSERVED",
            "scope_completeness": "UNKNOWN",
            "selection": "SELECTOR_INFERENCE_FALLBACK",
            "resolved_workloads": [],
            "evidence_ids": [],
        }

    state = str(route.get("state") or "UNKNOWN")
    completeness = str(route.get("scope_completeness") or "PARTIAL")
    if source_status == "COMPLETE" and state == "RESOLVED_WORKLOAD_ROUTING" and completeness == "COMPLETE":
        selection = "PREFERRED_ROUTING_EVIDENCE"
    elif source_status != "COMPLETE":
        selection = "ROUTING_SOURCE_INCOMPLETE"
    else:
        selection = "NO_WORKLOAD_ROUTING_CLAIM"
    return {
        "source_status": source_status,
        "service": service,
        "state": state,
        "scope_completeness": completeness,
        "selection": selection,
        "resolved_workloads": [item.get("subject") for item in route.get("resolved_workloads", []) if item.get("subject")],
        "evidence_ids": list(route.get("evidence_ids", [])),
    }


def enrich_incidents_with_routing(
    incidents: dict[str, Any],
    inventory: dict[str, Any],
) -> dict[str, Any]:
    """Prefer exact complete routing evidence for Service-scoped impact context."""
    if incidents.get("cluster_id") != inventory.get("cluster_id"):
        raise ValueError("incident candidates and inventory must target the same cluster")

    result = deepcopy(incidents)
    entities_by_subject = {
        _workload_subject(entity): entity for entity in inventory.get("entities", [])
    }
    source_status = str(inventory.get("routing_ownership_source_status") or "FAILED_TO_OBSERVE")
    result["incident_candidates_version"] = INCIDENT_ROUTING_VERSION
    result.setdefault("source_status", {})["routing_ownership"] = source_status

    for candidate in result.get("candidates", []):
        scope = candidate.get("scope", {})
        if scope.get("type") != "SERVICE":
            continue
        service = str(scope.get("subject") or "")
        routing_context = _service_routing_projection(service=service, inventory=inventory)
        impact = candidate.get("impact_context", {})
        impact["service_routing"] = routing_context

        if routing_context["selection"] == "PREFERRED_ROUTING_EVIDENCE":
            matched_entities = [
                entities_by_subject[subject]
                for subject in routing_context["resolved_workloads"]
                if subject in entities_by_subject
            ]
            workload_items = [
                _entity_projection(
                    entity,
                    basis=[
                        "ENDPOINTSLICE_SERVICE_NAME_LABEL",
                        "ENDPOINT_TARGET_REF",
                        "POD_CONTROLLER_OWNER_REFERENCE",
                        "CURRENT_WORKLOAD_OBSERVATION",
                    ],
                )
                for entity in matched_entities
            ]
            ingress, pvcs, ingress_truncated, pvcs_truncated = _related_secondary_context(matched_entities)
            impact["related_workloads_total"] = len(matched_entities)
            impact["related_workloads"] = workload_items
            impact["related_workloads_truncated"] = False
            impact["ingress_route_candidates"] = ingress
            impact["ingress_route_candidates_truncated"] = ingress_truncated
            impact["persistent_volume_claims"] = pvcs
            impact["persistent_volume_claims_truncated"] = pvcs_truncated
            impact["basis"] = ["ENDPOINTSLICE_POD_CONTROLLER_OWNER_ROUTING"]
            impact["caveat"] = (
                "Related workloads are backed by complete EndpointSlice targetRef and Pod/controller owner-reference routing evidence. "
                "This is routing/ownership context, not proof that every related workload is impacted."
            )
            candidate["recommended_checks"] = [
                item
                for item in candidate.get("recommended_checks", [])
                if item.get("code") != "VERIFY_SERVICE_ENDPOINT_OWNERSHIP"
            ]
        elif routing_context["state"] in {
            "NON_POD_ROUTING",
            "PARTIAL_ROUTING",
            "UNKNOWN",
            "SERVICE_NOT_OBSERVED",
            "NO_ENDPOINTS_OBSERVED",
        }:
            impact["related_workloads_total"] = 0
            impact["related_workloads"] = []
            impact["related_workloads_truncated"] = False
            impact["ingress_route_candidates"] = []
            impact["ingress_route_candidates_truncated"] = False
            impact["persistent_volume_claims"] = []
            impact["persistent_volume_claims_truncated"] = False
            impact["basis"] = ["ROUTING_STATE_DOES_NOT_SUPPORT_WORKLOAD_OWNERSHIP"]
            impact["caveat"] = (
                f"Exact routing evidence for {service} is {routing_context['state']} with "
                f"scope completeness {routing_context['scope_completeness']}; no workload impact relation is asserted."
            )

        candidate["impact_context"] = impact
        candidate["evidence_ids"] = _unique(
            list(candidate.get("evidence_ids", []))
            + list(routing_context.get("evidence_ids", []))
            + [eid for item in impact.get("related_workloads", []) for eid in item.get("evidence_ids", [])]
        )

    state_counts = Counter(item.get("state") for item in result.get("candidates", []))
    summary = dict(result.get("summary", {}))
    summary["candidates_with_related_workloads"] = sum(
        item.get("impact_context", {}).get("related_workloads_total", 0) > 0
        for item in result.get("candidates", [])
    )
    summary["service_candidates_with_preferred_routing"] = sum(
        item.get("impact_context", {}).get("service_routing", {}).get("selection")
        == "PREFERRED_ROUTING_EVIDENCE"
        for item in result.get("candidates", [])
    )
    summary["service_candidates_without_workload_routing_claim"] = sum(
        item.get("scope", {}).get("type") == "SERVICE"
        and item.get("impact_context", {}).get("service_routing", {}).get("selection")
        == "NO_WORKLOAD_ROUTING_CLAIM"
        for item in result.get("candidates", [])
    )
    result["summary"] = summary

    recommendation_targets = Counter(
        rec.get("target")
        for candidate in result.get("candidates", [])
        for rec in candidate.get("recommended_checks", [])
        if rec.get("target")
    )
    result["recommended_next_evidence_targets"] = [
        {"target": target, "candidate_checks": count}
        for target, count in sorted(recommendation_targets.items(), key=lambda item: (-item[1], item[0]))
    ]
    caveats = list(result.get("caveats", []))
    caveats.append(
        "Service-scoped workload context prefers complete EndpointSlice/Pod/controller routing ownership over selector inference when the exact Service subject joins; non-Pod or incomplete routing does not create workload ownership."
    )
    result["caveats"] = _unique(caveats)
    return result


def render_inventory_routing_section(inventory: dict[str, Any]) -> str:
    summary = inventory.get("summary", {})
    lines = [
        ROUTING_SECTION_START,
        "",
        "## Routing ownership integration",
        "",
        f"- Source status: {inventory.get('routing_ownership_source_status', 'FAILED_TO_OBSERVE')}",
        f"- Routing service links: {summary.get('routing_service_links', 0)}",
        f"- Workloads with routing service: {summary.get('workloads_with_routing_service', 0)}",
        f"- Resolved Service routes: {summary.get('routing_services_resolved', 0)}",
        f"- Non-Pod Service routes: {summary.get('routing_services_non_pod', 0)}",
        f"- Unknown/partial Service routes: {summary.get('routing_services_unknown_or_partial', 0)}",
        f"- Routing workloads not joined to inventory: {summary.get('routing_workloads_not_in_inventory', 0)}",
        "",
        "Accepted routing relations are separate from selector inference. Multiple real backend controllers are preserved rather than collapsed to one workload.",
        "",
        ROUTING_SECTION_END,
    ]
    return "\n".join(lines) + "\n"


def _replace_marked_section(existing: str, section: str) -> str:
    if ROUTING_SECTION_START not in existing:
        return existing.rstrip() + "\n\n" + section
    before, rest = existing.split(ROUTING_SECTION_START, 1)
    if ROUTING_SECTION_END not in rest:
        return before.rstrip() + "\n\n" + section
    _old, after = rest.split(ROUTING_SECTION_END, 1)
    return before.rstrip() + "\n\n" + section.rstrip() + after


def main() -> int:
    parser = argparse.ArgumentParser(description="Integrate accepted Kubernetes routing ownership into local inventory and incident context.")
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--routing", type=Path, required=True)
    parser.add_argument("--incident", type=Path, required=True)
    parser.add_argument("--inventory-summary", type=Path)
    parser.add_argument("--incident-summary", type=Path)
    args = parser.parse_args()

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    routing = json.loads(args.routing.read_text(encoding="utf-8"))
    incidents = json.loads(args.incident.read_text(encoding="utf-8"))

    enriched_inventory = enrich_inventory_with_routing(inventory, routing)
    enriched_incidents = enrich_incidents_with_routing(incidents, enriched_inventory)

    atomic_write_json(args.inventory, enriched_inventory)
    atomic_write_json(args.incident, enriched_incidents)

    if args.inventory_summary:
        existing = args.inventory_summary.read_text(encoding="utf-8") if args.inventory_summary.exists() else "# Workload Operational Inventory\n"
        atomic_write_text(
            args.inventory_summary,
            _replace_marked_section(existing, render_inventory_routing_section(enriched_inventory)),
        )
    if args.incident_summary:
        atomic_write_text(args.incident_summary, render_incident_candidates_markdown(enriched_incidents))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
