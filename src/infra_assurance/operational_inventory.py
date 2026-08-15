from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .evidence import freshness

INVENTORY_VERSION = "0.1"
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet"}


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _label(subject: dict[str, Any]) -> str:
    namespace = f"{subject['namespace']}/" if subject.get("namespace") else ""
    return f"{subject['kind']}/{namespace}{subject['name']}"


def _subject_key(subject: dict[str, Any]) -> tuple[Any, ...]:
    return (
        subject["system"],
        subject["cluster"],
        subject.get("api_group", ""),
        subject["kind"],
        subject.get("namespace"),
        subject["name"],
    )


def _entity_id(subject: dict[str, Any]) -> str:
    api_group = subject.get("api_group") or "core"
    namespace = subject.get("namespace") or "-"
    return (
        f"kubernetes:{subject['cluster']}:{api_group}:"
        f"{subject['kind']}:{namespace}:{subject['name']}"
    )


def _observed_workloads(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for envelope in snapshot.get("evidence", []):
        subject = envelope.get("subject", {})
        if subject.get("kind") not in WORKLOAD_KINDS:
            continue
        if envelope.get("plane") != "observed":
            continue
        if envelope.get("existence") != "PRESENT":
            continue
        if envelope.get("observation_status") != "COMPLETE":
            continue
        result.append(envelope)
    return sorted(
        result,
        key=lambda item: (
            item["subject"].get("namespace") or "",
            item["subject"]["kind"],
            item["subject"]["name"],
        ),
    )


def _declared_index(declared_load: dict[str, Any]) -> dict[tuple[Any, ...], dict[str, Any]]:
    return {
        _subject_key(record["subject"]): record
        for record in declared_load.get("records", [])
        if record.get("plane") == "declared" and record.get("subject")
    }


def _drift_index(drift: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["subject"]: item
        for item in drift.get("results", [])
        if isinstance(item, dict) and item.get("subject")
    }


def _change_index(diff: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["subject"]: item
        for item in diff.get("changes", [])
        if isinstance(item, dict) and item.get("subject")
    }


def _unsafe_diff_kinds(diff: dict[str, Any]) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for item in diff.get("unknowns", []):
        kind = item.get("resource_kind")
        if kind:
            result.add((item.get("api_group", ""), kind))
    return result


def _relation_indexes(topology: dict[str, Any]) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    services_by_workload: dict[str, list[dict[str, Any]]] = {}
    ingresses_by_service: dict[str, list[dict[str, Any]]] = {}
    pvcs_by_workload: dict[str, list[dict[str, Any]]] = {}

    for relation in topology.get("relations", []):
        relation_type = relation.get("type")
        if relation_type == "SERVICE_SELECTOR_MATCHES_WORKLOAD":
            services_by_workload.setdefault(relation["target"], []).append(relation)
        elif relation_type == "INGRESS_REFERENCES_SERVICE":
            ingresses_by_service.setdefault(relation["target"], []).append(relation)
        elif relation_type == "WORKLOAD_REFERENCES_PVC":
            pvcs_by_workload.setdefault(relation["source"], []).append(relation)

    return services_by_workload, ingresses_by_service, pvcs_by_workload


def _observed_projection(envelope: dict[str, Any], now: datetime) -> dict[str, Any]:
    data = envelope.get("data", {})
    allowed = (
        "desired_replicas",
        "ready_replicas",
        "desired_scheduled",
        "current_scheduled",
        "number_ready",
        "images",
    )
    attributes = {key: data[key] for key in allowed if key in data}
    try:
        freshness_state = freshness(envelope, now)
    except ValueError:
        freshness_state = "UNKNOWN"
    return {
        "existence": envelope.get("existence", "UNKNOWN"),
        "observation_status": envelope.get("observation_status"),
        "freshness": freshness_state,
        "observed_at": envelope.get("observed_at"),
        "expires_at": envelope.get("expires_at"),
        "evidence_id": envelope["evidence_id"],
        "attributes": attributes,
    }


def _declared_projection(
    subject: dict[str, Any],
    declared: dict[str, Any] | None,
    declared_load: dict[str, Any],
    drift_result: dict[str, Any] | None,
) -> dict[str, Any]:
    load_status = declared_load.get("status")
    if declared is not None:
        provenance = declared.get("provenance", {})
        return {
            "coverage": "DECLARED",
            "comparison": drift_result.get("classification") if drift_result else "UNKNOWN",
            "evidence_id": declared.get("evidence_id"),
            "source_id": provenance.get("source_id"),
            "revision": provenance.get("revision"),
        }

    if load_status == "AVAILABLE":
        coverage = "OUTSIDE_DECLARED_SCOPE"
    elif load_status == "AVAILABLE_PARTIAL":
        coverage = "DECLARED_COVERAGE_INCOMPLETE"
    else:
        coverage = "DECLARED_SOURCE_UNAVAILABLE"

    return {
        "coverage": coverage,
        "comparison": None,
        "evidence_id": None,
        "source_id": None,
        "revision": None,
    }


def _service_links(relations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "subject": relation["source"],
            "basis": relation["basis"],
            "evidence_ids": relation.get("evidence_ids", []),
            "selector": relation.get("details", {}).get("selector"),
        }
        for relation in sorted(relations, key=lambda item: item["source"])
    ]


def _ingress_candidates(
    service_relations: list[dict[str, Any]],
    ingresses_by_service: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for service_relation in service_relations:
        service_label = service_relation["source"]
        for ingress_relation in ingresses_by_service.get(service_label, []):
            key = (ingress_relation["source"], service_label)
            if key in seen:
                continue
            seen.add(key)
            result.append(
                {
                    "subject": ingress_relation["source"],
                    "via_service": service_label,
                    "basis": "COMPOSED_INFERENCE",
                    "evidence_ids": list(
                        dict.fromkeys(
                            ingress_relation.get("evidence_ids", [])
                            + service_relation.get("evidence_ids", [])
                        )
                    ),
                    "details": ingress_relation.get("details", {}),
                }
            )
    return sorted(result, key=lambda item: (item["subject"], item["via_service"]))


def _pvc_links(relations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "subject": relation["target"],
            "basis": relation["basis"],
            "evidence_ids": relation.get("evidence_ids", []),
        }
        for relation in sorted(relations, key=lambda item: item["target"])
    ]


def _topology_attention(
    topology: dict[str, Any],
    associated_subjects: set[str],
) -> list[dict[str, Any]]:
    result = []
    for issue in topology.get("issues", []):
        if issue.get("subject") not in associated_subjects and issue.get("target") not in associated_subjects:
            continue
        result.append(
            {
                "source": "topology",
                "code": issue["code"],
                "severity": issue["severity"],
                "subject": issue.get("subject"),
                "statement": issue["statement"],
                "evidence_ids": issue.get("evidence_ids", []),
                "required_live_verification": issue.get("required_live_verification"),
            }
        )
    return result


def _drift_attention(
    drift_index: dict[str, dict[str, Any]],
    associated_subjects: set[str],
) -> list[dict[str, Any]]:
    result = []
    for subject in sorted(associated_subjects):
        item = drift_index.get(subject)
        if not item or item.get("classification") == "IN_SYNC":
            continue
        result.append(
            {
                "source": "drift",
                "code": f"DECLARED_OBSERVED_{item['classification']}",
                "severity": item["classification"],
                "subject": subject,
                "statement": f"{subject} declared-vs-observed comparison is {item['classification']}.",
                "evidence_ids": item.get("evidence_ids", []),
                "field_mismatches": item.get("field_mismatches", []),
                "unknown_fields": item.get("unknown_fields", []),
            }
        )
    return result


def _recent_changes(
    change_index: dict[str, dict[str, Any]],
    associated_subjects: set[str],
) -> list[dict[str, Any]]:
    return [change_index[subject] for subject in sorted(associated_subjects) if subject in change_index]


def build_operational_inventory(
    snapshot: dict[str, Any],
    topology: dict[str, Any],
    diff: dict[str, Any],
    drift: dict[str, Any],
    declared_load: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a workload-centric CMDB projection without creating a new source of truth."""
    now = now or datetime.now(timezone.utc)
    cluster_id = snapshot["cluster_id"]
    for artifact in (topology, diff, drift):
        if artifact.get("cluster_id") != cluster_id:
            raise ValueError("operational inventory inputs must target the same cluster")

    declared_index = _declared_index(declared_load)
    drift_index = _drift_index(drift)
    change_index = _change_index(diff)
    unsafe_diff_kinds = _unsafe_diff_kinds(diff)
    services_by_workload, ingresses_by_service, pvcs_by_workload = _relation_indexes(topology)

    entities: list[dict[str, Any]] = []
    for workload in _observed_workloads(snapshot):
        subject = workload["subject"]
        label = _label(subject)
        service_relations = services_by_workload.get(label, [])
        services = _service_links(service_relations)
        ingress_candidates = _ingress_candidates(service_relations, ingresses_by_service)
        pvcs = _pvc_links(pvcs_by_workload.get(label, []))

        associated_subjects = {label}
        associated_subjects.update(item["subject"] for item in services)
        associated_subjects.update(item["subject"] for item in ingress_candidates)
        associated_subjects.update(item["subject"] for item in pvcs)

        declared_record = declared_index.get(_subject_key(subject))
        workload_drift = drift_index.get(label)
        declared = _declared_projection(
            subject,
            declared_record,
            declared_load,
            workload_drift,
        )

        changes = _recent_changes(change_index, associated_subjects)
        kind_key = (subject.get("api_group", ""), subject["kind"])
        if diff.get("baseline"):
            change_state = "BASELINE"
        elif kind_key in unsafe_diff_kinds:
            change_state = "UNKNOWN"
        elif label in change_index:
            change_state = change_index[label]["classification"]
        else:
            change_state = "UNCHANGED"

        attention = _topology_attention(topology, associated_subjects)
        attention.extend(_drift_attention(drift_index, associated_subjects))
        if change_state == "UNKNOWN":
            attention.append(
                {
                    "source": "history",
                    "code": "LATEST_CHANGE_UNKNOWN",
                    "severity": "UNKNOWN",
                    "subject": label,
                    "statement": f"Latest change state for {label} is unknown because current collection comparison is unsafe.",
                    "evidence_ids": [],
                }
            )

        observed = _observed_projection(workload, now)
        if observed["freshness"] != "CURRENT":
            attention.append(
                {
                    "source": "observed",
                    "code": "WORKLOAD_EVIDENCE_NOT_CURRENT",
                    "severity": "UNKNOWN",
                    "subject": label,
                    "statement": f"Observed evidence for {label} is not current.",
                    "evidence_ids": [workload["evidence_id"]],
                }
            )

        evidence_ids = [workload["evidence_id"]]
        if declared_record:
            evidence_ids.append(declared_record["evidence_id"])
        for collection in (services, ingress_candidates, pvcs, changes, attention):
            for item in collection:
                evidence_ids.extend(item.get("evidence_ids", []))

        entities.append(
            {
                "entity_id": _entity_id(subject),
                "entity_type": "KUBERNETES_WORKLOAD",
                "subject": subject,
                "observed": observed,
                "declared": declared,
                "relationships": {
                    "services": services,
                    "ingress_route_candidates": ingress_candidates,
                    "persistent_volume_claims": pvcs,
                },
                "recent_change": {
                    "state": change_state,
                    "items": changes,
                },
                "attention": attention,
                "evidence_ids": list(dict.fromkeys(evidence_ids)),
            }
        )

    namespaces = Counter(entity["subject"].get("namespace") or "-" for entity in entities)
    related_drift_subjects = {
        item["subject"]
        for entity in entities
        for item in entity["attention"]
        if item.get("source") == "drift"
    }
    summary = {
        "workloads_total": len(entities),
        "namespaces_total": len(namespaces),
        "declared_workloads": sum(entity["declared"]["coverage"] == "DECLARED" for entity in entities),
        "workloads_in_sync": sum(entity["declared"]["comparison"] == "IN_SYNC" for entity in entities),
        "workloads_outside_declared_scope": sum(
            entity["declared"]["coverage"] == "OUTSIDE_DECLARED_SCOPE" for entity in entities
        ),
        "workloads_with_attention": sum(bool(entity["attention"]) for entity in entities),
        "workloads_changed_in_latest_diff": sum(
            entity["recent_change"]["state"] in {"ADDED", "REMOVED", "MODIFIED", "NEWLY_OBSERVED"}
            for entity in entities
        ),
        "service_links": sum(len(entity["relationships"]["services"]) for entity in entities),
        "ingress_route_candidates": sum(
            len(entity["relationships"]["ingress_route_candidates"]) for entity in entities
        ),
        "pvc_links": sum(
            len(entity["relationships"]["persistent_volume_claims"]) for entity in entities
        ),
        "related_drift_subjects": len(related_drift_subjects),
    }

    return {
        "inventory_version": INVENTORY_VERSION,
        "cluster_id": cluster_id,
        "generated_at": _rfc3339(now),
        "mutation_allowed": False,
        "scope": {
            "entity_type": "KUBERNETES_WORKLOAD",
            "workload_kinds": sorted(WORKLOAD_KINDS),
        },
        "summary": summary,
        "namespace_counts": dict(sorted(namespaces.items())),
        "entities": entities,
    }


def render_operational_inventory_markdown(inventory: dict[str, Any]) -> str:
    summary = inventory["summary"]
    lines = [
        "# Workload Operational Inventory",
        "",
        f"Cluster: `{inventory['cluster_id']}`",
        f"Generated: `{inventory['generated_at']}`",
        "Mutation allowed: `false`",
        "",
        "## Summary",
        "",
        f"- Workloads: {summary['workloads_total']}",
        f"- Namespaces: {summary['namespaces_total']}",
        f"- Git-declared workloads: {summary['declared_workloads']}",
        f"- Workloads in sync: {summary['workloads_in_sync']}",
        f"- Workloads outside configured declared scope: {summary['workloads_outside_declared_scope']}",
        f"- Workloads with attention: {summary['workloads_with_attention']}",
        f"- Related drift subjects: {summary['related_drift_subjects']}",
        f"- Service links: {summary['service_links']}",
        f"- Ingress route candidates: {summary['ingress_route_candidates']}",
        f"- PVC links: {summary['pvc_links']}",
        "",
        "## Attention",
        "",
    ]

    attention_entities = [entity for entity in inventory["entities"] if entity["attention"]]
    if attention_entities:
        for entity in attention_entities:
            label = _label(entity["subject"])
            lines.append(f"- {label}")
            for item in entity["attention"]:
                lines.append(
                    f"  - [{item['source']}:{item['severity']}] {item['statement']}"
                )
    else:
        lines.append("- None.")

    lines.extend(["", "## Namespace workload counts", ""])
    for namespace, count in inventory["namespace_counts"].items():
        lines.append(f"- {namespace}: {count}")

    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "This inventory is a derived workload-centric projection. It does not replace Kubernetes evidence, Git-declared evidence, history, drift, or topology artifacts.",
            "Service-to-workload links are selector-based inferences. Ingress route candidates compose an observed Ingress-to-Service reference with that inference and do not prove current EndpointSlice or Pod routing.",
            "A workload absent from the configured Git declared scope is not classified as drift solely because it is observed live.",
            "",
        ]
    )
    return "\n".join(lines)
