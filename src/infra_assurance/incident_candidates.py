from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

INCIDENT_CANDIDATES_VERSION = "0.1"
DEFAULT_MAX_RELATED = 20


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_id(*parts: Any) -> str:
    raw = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _workload_subject(entity: dict[str, Any]) -> str:
    subject = entity.get("subject", {})
    namespace = subject.get("namespace")
    if namespace:
        return f"{subject.get('kind')}/{namespace}/{subject.get('name')}"
    return f"{subject.get('kind')}/{subject.get('name')}"


def _namespace_from_subject(subject: str) -> str | None:
    parts = subject.split("/")
    if len(parts) == 2 and parts[0] == "Namespace":
        return parts[1]
    if len(parts) == 3:
        return parts[1]
    return None


def _alert_source_status(alert_attention: dict[str, Any]) -> str:
    source = alert_attention.get("source_status", {})
    if source.get("prometheus") == "COMPLETE" and source.get("alertmanager") == "COMPLETE":
        return "COMPLETE"
    return "PARTIAL"


def _change_context_status(change_context: dict[str, Any]) -> str:
    truncation = change_context.get("truncation", {})
    if any(bool(value) for key, value in truncation.items() if key.endswith("_truncated")):
        return "PARTIAL"
    return "COMPLETE"


def _candidate_state(attentions: list[dict[str, Any]]) -> str:
    states = {item.get("handling_state") for item in attentions}
    if "ACTIVE" in states:
        return "ACTIVE"
    if "UNKNOWN" in states or "UNPROCESSED" in states:
        return "UNKNOWN"
    if states & {"SILENCED", "INHIBITED", "SILENCED_AND_INHIBITED", "SUPPRESSED_OTHER"}:
        return "SUPPRESSED"
    return "UNKNOWN"


def _alert_projection(item: dict[str, Any]) -> dict[str, Any]:
    labels = item.get("labels", {})
    return {
        "attention_id": item.get("attention_id"),
        "handling_state": item.get("handling_state", "UNKNOWN"),
        "alertname": labels.get("alertname"),
        "severity": labels.get("severity"),
        "starts_at": item.get("starts_at"),
        "evidence_ids": list(item.get("evidence_ids", [])),
    }


def _event_projection(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": item.get("event_id"),
        "subject": item.get("subject"),
        "reason": item.get("reason"),
        "last_seen": item.get("last_seen"),
        "count": item.get("count", 1),
        "basis": list(item.get("basis", [])),
        "evidence_ids": list(item.get("evidence_ids", [])),
    }


def _entity_projection(entity: dict[str, Any], *, basis: list[str]) -> dict[str, Any]:
    runtime = entity.get("runtime_observability") or {}
    declared = entity.get("declared") or {}
    observed = entity.get("observed") or {}
    return {
        "subject": _workload_subject(entity),
        "basis": basis,
        "observed_freshness": observed.get("freshness", "UNKNOWN"),
        "declared_coverage": declared.get("coverage"),
        "declared_comparison": declared.get("comparison"),
        "prometheus_runtime_state": runtime.get("state"),
        "evidence_ids": list(entity.get("evidence_ids", [])),
    }


def _impact_context(
    scope: dict[str, Any],
    inventory: dict[str, Any],
    *,
    max_related: int,
) -> dict[str, Any]:
    scope_type = scope.get("type")
    subject = str(scope.get("subject") or "")
    entities = list(inventory.get("entities", []))
    related_entities: list[tuple[dict[str, Any], list[str]]] = []
    impact_basis: list[str] = []
    caveat = "Related infrastructure context is not proof of business impact."

    if scope_type == "WORKLOAD":
        for entity in entities:
            if _workload_subject(entity) == subject:
                related_entities.append((entity, ["DIRECT_WORKLOAD_IDENTITY"]))
        impact_basis = ["DIRECT_WORKLOAD_IDENTITY"] if related_entities else []
    elif scope_type == "SERVICE":
        for entity in entities:
            for relation in entity.get("relationships", {}).get("services", []):
                if relation.get("subject") == subject:
                    basis = [str(relation.get("basis") or "SERVICE_RELATION")]
                    related_entities.append((entity, basis))
                    impact_basis.extend(basis)
                    break
        caveat = (
            "Service-related workloads come from existing selector-based controller inference; "
            "EndpointSlice or Pod routing is not proven."
        )
    elif scope_type == "NAMESPACE":
        namespace = _namespace_from_subject(subject)
        if namespace:
            for entity in entities:
                if entity.get("subject", {}).get("namespace") == namespace:
                    related_entities.append((entity, ["NAMESPACE_MEMBERSHIP"]))
            impact_basis = ["NAMESPACE_MEMBERSHIP"] if related_entities else []
        caveat = (
            "Namespace membership is breadth context only; it does not mean every workload in the "
            "namespace is affected by the alert."
        )
    elif scope_type == "NODE":
        caveat = (
            "Workload placement on this Node is unknown in the current model because Pod scheduling "
            "and ownership are not observed by the platform."
        )
    elif scope_type == "PLATFORM":
        caveat = (
            "Platform scope identifies cluster-level attention; all cluster workloads are not "
            "automatically classified as impacted."
        )

    dedup: dict[str, tuple[dict[str, Any], list[str]]] = {}
    for entity, basis in related_entities:
        dedup[_workload_subject(entity)] = (entity, basis)
    related_entities = [dedup[key] for key in sorted(dedup)]

    workload_items = [
        _entity_projection(entity, basis=basis)
        for entity, basis in related_entities[:max_related]
    ]

    ingress: dict[str, dict[str, Any]] = {}
    pvcs: dict[str, dict[str, Any]] = {}
    for entity, _basis in related_entities:
        for relation in entity.get("relationships", {}).get("ingress_route_candidates", []):
            rel_subject = relation.get("subject")
            if rel_subject:
                ingress[str(rel_subject)] = {
                    "subject": rel_subject,
                    "basis": relation.get("basis"),
                    "evidence_ids": list(relation.get("evidence_ids", [])),
                }
        for relation in entity.get("relationships", {}).get("persistent_volume_claims", []):
            rel_subject = relation.get("subject")
            if rel_subject:
                pvcs[str(rel_subject)] = {
                    "subject": rel_subject,
                    "basis": relation.get("basis"),
                    "evidence_ids": list(relation.get("evidence_ids", [])),
                }

    summary = inventory.get("summary", {})
    platform_context = None
    if scope_type == "PLATFORM":
        platform_context = {
            "workloads_total": summary.get("workloads_total", 0),
            "namespaces_total": summary.get("namespaces_total", 0),
        }

    return {
        "related_workloads_total": len(related_entities),
        "related_workloads": workload_items,
        "related_workloads_truncated": len(related_entities) > max_related,
        "ingress_route_candidates": [ingress[key] for key in sorted(ingress)[:max_related]],
        "ingress_route_candidates_truncated": len(ingress) > max_related,
        "persistent_volume_claims": [pvcs[key] for key in sorted(pvcs)[:max_related]],
        "persistent_volume_claims_truncated": len(pvcs) > max_related,
        "platform_context": platform_context,
        "basis": _unique(impact_basis),
        "caveat": caveat,
    }


def _exact_context(subject: str, change_context: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    changes = [
        {
            "classification": item.get("classification"),
            "subject": item.get("subject"),
            "field_changes": list(item.get("field_changes", [])),
            "evidence_ids": list(item.get("evidence_ids", [])),
        }
        for item in change_context.get("recent_changes", [])
        if item.get("subject") == subject
    ]
    drift = [
        {
            "classification": item.get("classification"),
            "subject": item.get("subject"),
            "field_mismatches": list(item.get("field_mismatches", [])),
            "unknown_fields": list(item.get("unknown_fields", [])),
            "evidence_ids": list(item.get("evidence_ids", [])),
        }
        for item in change_context.get("drift_attention", [])
        if item.get("subject") == subject
    ]
    return changes, drift


def _recommendations(
    *,
    scope: dict[str, Any],
    state: str,
    alerts: list[dict[str, Any]],
    related_events: list[dict[str, Any]],
    impact: dict[str, Any],
    recent_changes: list[dict[str, Any]],
    drift_attention: list[dict[str, Any]],
    alert_source_status: str,
    event_source_status: str,
    evidence_ids: list[str],
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []

    def add(code: str, target: str, check: str, rationale: str, ids: list[str] | None = None) -> None:
        if any(item["code"] == code for item in recommendations):
            return
        recommendations.append(
            {
                "code": code,
                "target": target,
                "check": check,
                "rationale": rationale,
                "live_verification_required": True,
                "evidence_ids": _unique(ids or evidence_ids),
            }
        )

    if alert_source_status != "COMPLETE":
        add(
            "REFRESH_ALERT_EVIDENCE",
            "PROMETHEUS_ALERTMANAGER",
            "Refresh Prometheus and Alertmanager runtime evidence before interpreting this candidate.",
            "The alert-attention source is incomplete.",
        )
    if event_source_status != "COMPLETE":
        add(
            "REFRESH_KUBERNETES_EVENT_EVIDENCE",
            "KUBERNETES_EVENTS",
            "Refresh the bounded Kubernetes Event observation before treating an Event no-match as meaningful.",
            "Kubernetes Event evidence is partial or failed.",
        )

    scope_type = scope.get("type")
    subject = scope.get("subject")
    if state == "ACTIVE":
        add(
            "VERIFY_ALERT_CONDITION_CURRENT",
            "PROMETHEUS_ALERTMANAGER",
            f"Verify the underlying current alert condition for {subject} before any operational action.",
            "An Alertmanager attention record is currently ACTIVE; handling state alone does not explain cause.",
            [eid for alert in alerts for eid in alert.get("evidence_ids", [])],
        )
        if not related_events:
            add(
                "CHECK_SCOPE_LOGS_IF_NEEDED",
                "LOKI_CANDIDATE",
                f"If the alert condition remains unexplained, inspect logs for the supported scope around the alert time.",
                "No recent structured Kubernetes Warning Event is directly related to this active candidate; logs may be the next useful evidence source, but are not queried by this slice.",
            )

    if scope_type == "SERVICE" and impact.get("related_workloads_total", 0) == 0:
        add(
            "VERIFY_SERVICE_ENDPOINT_OWNERSHIP",
            "KUBERNETES_ENDPOINTSLICE_POD",
            f"Verify current EndpointSlice/Pod routing and controller ownership for {subject}.",
            "The current model has no supported Service-to-workload controller relation for this Service.",
        )
    if scope_type == "NODE":
        add(
            "VERIFY_NODE_WORKLOAD_PLACEMENT",
            "KUBERNETES_POD_OWNERSHIP",
            f"Verify which current Pods/workloads are placed on {subject} before estimating impact.",
            "Pod placement is outside the current observation model.",
        )
    if related_events:
        add(
            "VERIFY_RELATED_EVENT_OBJECT_STATE",
            "KUBERNETES_OBJECT",
            "Verify the current state of the involved Kubernetes object for the most relevant recent Warning Event.",
            "The Event is supporting temporal/context evidence only; current object state is required before causal interpretation.",
            [eid for event in related_events for eid in event.get("evidence_ids", [])],
        )
    if recent_changes:
        add(
            "REVIEW_EXACT_RECENT_CHANGE",
            "KUBERNETES_HISTORY",
            f"Review the exact recent change recorded for {subject} and verify whether its timing overlaps the current signal.",
            "A recent change exists on the exact same subject, but temporal coincidence is not root-cause proof.",
            [eid for item in recent_changes for eid in item.get("evidence_ids", [])],
        )
    if drift_attention:
        add(
            "VERIFY_EXACT_DECLARED_OBSERVED_DRIFT",
            "GIT_AND_KUBERNETES",
            f"Verify the exact declared-vs-observed drift for {subject} before remediation planning.",
            "Current drift is attached only because it matches the exact candidate subject.",
            [eid for item in drift_attention for eid in item.get("evidence_ids", [])],
        )

    if scope_type == "PLATFORM" and state == "ACTIVE":
        add(
            "VERIFY_PLATFORM_SIGNAL_INPUTS",
            "PROMETHEUS_KUBERNETES",
            "Verify the cluster-level rule inputs and current capacity/state relevant to this platform-scoped alert.",
            "Platform scope does not imply every workload is impacted.",
        )

    return recommendations


def build_incident_candidates(
    alert_attention: dict[str, Any],
    event_correlation: dict[str, Any],
    inventory: dict[str, Any],
    change_context: dict[str, Any],
    *,
    now: datetime | None = None,
    max_related: int = DEFAULT_MAX_RELATED,
) -> dict[str, Any]:
    """Group current evidence into conservative incident candidates and verification plans."""
    if max_related < 1:
        raise ValueError("max_related must be positive")

    cluster_ids = {
        alert_attention.get("cluster_id"),
        event_correlation.get("cluster_id"),
        inventory.get("cluster_id"),
        change_context.get("task", {}).get("scope", {}).get("cluster"),
    }
    if len(cluster_ids) != 1 or None in cluster_ids:
        raise ValueError("Incident candidate inputs must target the same cluster")
    cluster_id = str(next(iter(cluster_ids)))
    now = now or datetime.now(timezone.utc)

    event_by_attention = {
        item.get("attention_id"): item
        for item in event_correlation.get("correlations", [])
        if item.get("attention_id")
    }
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in alert_attention.get("attention", []):
        scope = item.get("scope", {})
        scope_type = scope.get("type")
        subject = scope.get("subject")
        if not scope_type or not subject:
            continue
        groups[(str(scope_type), str(subject))].append(item)

    alert_source_status = _alert_source_status(alert_attention)
    event_source_status = str(
        event_correlation.get("source_status", {}).get("kubernetes_events", "FAILED_TO_OBSERVE")
    )
    candidates: list[dict[str, Any]] = []

    for (scope_type, subject), attentions in sorted(groups.items()):
        scope = {
            "type": scope_type,
            "subject": subject,
            "basis": _unique(
                [
                    basis
                    for item in attentions
                    for basis in item.get("scope", {}).get("basis", [])
                ]
            ),
        }
        alerts = [_alert_projection(item) for item in attentions]
        related_events_by_id: dict[str, dict[str, Any]] = {}
        correlation_statuses: list[str] = []
        for item in attentions:
            correlation = event_by_attention.get(item.get("attention_id"))
            if not correlation:
                correlation_statuses.append("UNKNOWN")
                continue
            correlation_statuses.append(str(correlation.get("correlation_status") or "UNKNOWN"))
            for event in correlation.get("related_warning_events", []):
                projected = _event_projection(event)
                if projected.get("event_id"):
                    related_events_by_id[str(projected["event_id"])] = projected
        related_events = sorted(
            related_events_by_id.values(),
            key=lambda item: str(item.get("last_seen") or ""),
            reverse=True,
        )[:max_related]

        impact = _impact_context(scope, inventory, max_related=max_related)
        recent_changes, drift_attention = _exact_context(subject, change_context)
        state = _candidate_state(attentions)
        evidence_ids = _unique(
            [eid for alert in alerts for eid in alert.get("evidence_ids", [])]
            + [eid for event in related_events for eid in event.get("evidence_ids", [])]
            + [eid for item in recent_changes for eid in item.get("evidence_ids", [])]
            + [eid for item in drift_attention for eid in item.get("evidence_ids", [])]
            + [eid for workload in impact.get("related_workloads", []) for eid in workload.get("evidence_ids", [])]
        )
        recommendations = _recommendations(
            scope=scope,
            state=state,
            alerts=alerts,
            related_events=related_events,
            impact=impact,
            recent_changes=recent_changes,
            drift_attention=drift_attention,
            alert_source_status=alert_source_status,
            event_source_status=event_source_status,
            evidence_ids=evidence_ids,
        )
        candidates.append(
            {
                "candidate_id": "incident-candidate-" + _stable_id(cluster_id, scope_type, subject),
                "scope": scope,
                "state": state,
                "alert_count": len(alerts),
                "alerts": alerts,
                "event_correlation_statuses": sorted(set(correlation_statuses)),
                "related_warning_events": related_events,
                "recent_changes": recent_changes,
                "drift_attention": drift_attention,
                "impact_context": impact,
                "recommended_checks": recommendations,
                "evidence_ids": evidence_ids,
                "caveats": [
                    "This is an incident candidate, not a confirmed incident or root-cause conclusion.",
                    "Suppressed/inhibited alerts remain evidence and are not treated as resolved conditions.",
                ],
            }
        )

    state_counts = Counter(item["state"] for item in candidates)
    recommendation_targets = Counter(
        rec["target"]
        for candidate in candidates
        for rec in candidate.get("recommended_checks", [])
    )
    source_unknowns = list(change_context.get("unknowns", []))
    source_required = list(change_context.get("required_live_verification", []))

    return {
        "incident_candidates_version": INCIDENT_CANDIDATES_VERSION,
        "cluster_id": cluster_id,
        "generated_at": _rfc3339(now),
        "mutation_allowed": False,
        "source_status": {
            "alert_attention": alert_source_status,
            "kubernetes_events": event_source_status,
            "change_context": _change_context_status(change_context),
            "drift": change_context.get("drift", {}).get("status", "UNKNOWN"),
            "inventory": "COMPLETE",
        },
        "summary": {
            "alert_attention_records": len(alert_attention.get("attention", [])),
            "incident_candidates": len(candidates),
            "active_candidates": state_counts["ACTIVE"],
            "suppressed_candidates": state_counts["SUPPRESSED"],
            "unknown_candidates": state_counts["UNKNOWN"],
            "candidates_with_related_warning_events": sum(
                1 for item in candidates if item["related_warning_events"]
            ),
            "candidates_with_exact_recent_change": sum(
                1 for item in candidates if item["recent_changes"]
            ),
            "candidates_with_exact_drift": sum(
                1 for item in candidates if item["drift_attention"]
            ),
            "candidates_with_related_workloads": sum(
                1 for item in candidates if item["impact_context"]["related_workloads_total"] > 0
            ),
            "candidates_requiring_live_verification": sum(
                1 for item in candidates if item["recommended_checks"]
            ),
        },
        "recommended_next_evidence_targets": [
            {"target": target, "candidate_checks": count}
            for target, count in sorted(
                recommendation_targets.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        "candidates": candidates,
        "unassociated_change_unknowns": source_unknowns[:max_related],
        "unassociated_required_live_verification": source_required[:max_related],
        "caveats": [
            "Candidates are grouped only by an identical supported alert-attention scope type and subject.",
            "Related workloads, routes, and PVCs are infrastructure context; they are not automatic impact claims.",
            "A recent Event, change, or drift record is supporting evidence and does not establish root cause.",
            "Recommended checks identify missing evidence or verification steps; this artifact performs no mutation and no new telemetry query.",
        ],
    }


def render_incident_candidates_markdown(artifact: dict[str, Any]) -> str:
    summary = artifact["summary"]
    lines = [
        "# Incident Candidates and Drill-down",
        "",
        f"Cluster: `{artifact['cluster_id']}`",
        f"Generated: `{artifact['generated_at']}`",
        "Mutation allowed: `false`",
        "",
        "## Summary",
        "",
        f"- Alert attention records: {summary['alert_attention_records']}",
        f"- Incident candidates: {summary['incident_candidates']}",
        f"- Active candidates: {summary['active_candidates']}",
        f"- Suppressed candidates: {summary['suppressed_candidates']}",
        f"- Unknown candidates: {summary['unknown_candidates']}",
        f"- Candidates with related Warning Events: {summary['candidates_with_related_warning_events']}",
        f"- Candidates with exact recent change: {summary['candidates_with_exact_recent_change']}",
        f"- Candidates with exact drift: {summary['candidates_with_exact_drift']}",
        f"- Candidates with related workload context: {summary['candidates_with_related_workloads']}",
        "",
        "## Current candidates",
        "",
    ]
    if not artifact["candidates"]:
        lines.append("- none")
    for candidate in artifact["candidates"]:
        scope = candidate["scope"]
        alert_names = sorted(
            {
                str(item.get("alertname"))
                for item in candidate["alerts"]
                if item.get("alertname")
            }
        )
        lines.append(
            f"- [{candidate['state']}] {scope['subject']} alerts={candidate['alert_count']} "
            f"names={','.join(alert_names) or 'unknown'} related_warnings={len(candidate['related_warning_events'])} "
            f"related_workloads={candidate['impact_context']['related_workloads_total']}"
        )
        for event in candidate["related_warning_events"][:5]:
            lines.append(
                f"  - Event {event['reason']} on {event['subject']} last_seen={event['last_seen']} count={event['count']}"
            )
        for check in candidate["recommended_checks"][:8]:
            lines.append(f"  - Verify [{check['code']}] {check['check']}")

    lines.extend(["", "## Recommended next evidence targets", ""])
    if artifact["recommended_next_evidence_targets"]:
        for item in artifact["recommended_next_evidence_targets"]:
            lines.append(f"- {item['target']}: {item['candidate_checks']} candidate checks")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "An incident candidate is a compact evidence grouping, not a confirmed incident, impact statement, or root-cause conclusion. Recommended checks identify where fresh or specialized evidence is still required.",
            "",
        ]
    )
    return "\n".join(lines)
