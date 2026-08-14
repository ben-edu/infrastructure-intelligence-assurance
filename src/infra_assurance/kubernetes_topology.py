from __future__ import annotations

from typing import Any

WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet"}


def _label(subject: dict[str, Any]) -> str:
    namespace = f"{subject['namespace']}/" if subject.get("namespace") else ""
    return f"{subject['kind']}/{namespace}{subject['name']}"


def _resource_index(
    snapshot: dict[str, Any],
) -> dict[tuple[str, str | None, str], dict[str, Any]]:
    index: dict[tuple[str, str | None, str], dict[str, Any]] = {}
    for envelope in snapshot["evidence"]:
        if envelope["observation_status"] != "COMPLETE":
            continue
        subject = envelope["subject"]
        if subject["kind"].endswith("Collection"):
            continue
        index[(subject["kind"], subject.get("namespace"), subject["name"])] = envelope
    return index


def _collection_index(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for envelope in snapshot["evidence"]:
        subject = envelope["subject"]
        kind = subject["kind"]
        if kind.endswith("Collection"):
            result[kind.removesuffix("Collection")] = envelope
    return result


def _collection_complete(
    collections: dict[str, dict[str, Any]], kind: str
) -> bool:
    envelope = collections.get(kind)
    return bool(envelope and envelope["observation_status"] == "COMPLETE")


def _collection_evidence_id(
    collections: dict[str, dict[str, Any]], kind: str
) -> str | None:
    envelope = collections.get(kind)
    return envelope.get("evidence_id") if envelope else None


def _selector_matches(selector: dict[str, Any], labels: dict[str, Any]) -> bool:
    if not selector:
        return False
    return all(key in labels and str(labels[key]) == str(value) for key, value in selector.items())


def _relation(
    *,
    relation_type: str,
    source: str,
    target: str,
    basis: str,
    evidence_ids: list[str],
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    relation = {
        "type": relation_type,
        "source": source,
        "target": target,
        "basis": basis,
        "evidence_ids": list(dict.fromkeys(evidence_ids)),
    }
    if details:
        relation["details"] = details
    return relation


def _issue(
    *,
    code: str,
    subject: str,
    statement: str,
    evidence_ids: list[str],
    verification: str,
    severity: str = "REQUIRES_VERIFICATION",
    target: str | None = None,
) -> dict[str, Any]:
    result = {
        "code": code,
        "severity": severity,
        "subject": subject,
        "statement": statement,
        "evidence_ids": list(dict.fromkeys(evidence_ids)),
        "required_live_verification": verification,
    }
    if target:
        result["target"] = target
    return result


def _with_collection_evidence(
    evidence_ids: list[str],
    collections: dict[str, dict[str, Any]],
    kind: str,
) -> list[str]:
    collection_id = _collection_evidence_id(collections, kind)
    if collection_id:
        evidence_ids.append(collection_id)
    return evidence_ids


def build_kubernetes_topology(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Derive traceable Kubernetes relationships without replacing source evidence."""
    resources = _resource_index(snapshot)
    collections = _collection_index(snapshot)
    relations: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    workloads = [
        envelope
        for (kind, _namespace, _name), envelope in resources.items()
        if kind in WORKLOAD_KINDS
    ]
    services = [
        envelope
        for (kind, _namespace, _name), envelope in resources.items()
        if kind == "Service"
    ]
    ingresses = [
        envelope
        for (kind, _namespace, _name), envelope in resources.items()
        if kind == "Ingress"
    ]

    # Direct observed Ingress -> Service references.
    for ingress in ingresses:
        subject = ingress["subject"]
        source = _label(subject)
        namespace = subject.get("namespace")

        for backend in ingress["data"].get("backends", []):
            service_name = backend.get("service")
            if not service_name:
                continue

            target = f"Service/{namespace}/{service_name}"
            service = resources.get(("Service", namespace, service_name))

            if service:
                relations.append(
                    _relation(
                        relation_type="INGRESS_REFERENCES_SERVICE",
                        source=source,
                        target=target,
                        basis="OBSERVED_REFERENCE",
                        evidence_ids=[ingress["evidence_id"], service["evidence_id"]],
                        details={
                            "host": backend.get("host"),
                            "path": backend.get("path"),
                            "service_port": backend.get("service_port"),
                        },
                    )
                )
                continue

            evidence_ids = _with_collection_evidence(
                [ingress["evidence_id"]], collections, "Service"
            )
            if _collection_complete(collections, "Service"):
                issues.append(
                    _issue(
                        code="INGRESS_SERVICE_NOT_OBSERVED",
                        subject=source,
                        target=target,
                        statement=(
                            f"{source} references {target}, but that Service was not observed "
                            "in the current complete Service collection."
                        ),
                        evidence_ids=evidence_ids,
                        verification=(
                            f"Verify whether {target} should exist and whether the Ingress "
                            "backend reference is current."
                        ),
                    )
                )
            else:
                issues.append(
                    _issue(
                        code="INGRESS_SERVICE_TARGET_UNKNOWN",
                        subject=source,
                        target=target,
                        statement=(
                            f"{source} references {target}, but current Service observation "
                            "is incomplete or failed, so target existence is unknown."
                        ),
                        evidence_ids=evidence_ids,
                        verification=(
                            "Re-establish a successful Service collection before classifying "
                            f"the backend reference for {source}."
                        ),
                        severity="UNKNOWN_WITH_CURRENT_SCOPE",
                    )
                )

    # Service selector -> workload-controller candidates. This is intentionally an inference:
    # Kubernetes Services target Pods/Endpoints, not controllers directly.
    workload_collections_complete = all(
        _collection_complete(collections, kind) for kind in WORKLOAD_KINDS
    )

    for service in services:
        selector = service["data"].get("selector") or {}
        if not selector:
            continue

        subject = service["subject"]
        source = _label(subject)
        namespace = subject.get("namespace")
        matches = [
            workload
            for workload in workloads
            if workload["subject"].get("namespace") == namespace
            and _selector_matches(selector, workload["data"].get("pod_labels") or {})
        ]

        for workload in matches:
            relations.append(
                _relation(
                    relation_type="SERVICE_SELECTOR_MATCHES_WORKLOAD",
                    source=source,
                    target=_label(workload["subject"]),
                    basis="SELECTOR_MATCH_INFERENCE",
                    evidence_ids=[service["evidence_id"], workload["evidence_id"]],
                    details={"selector": selector},
                )
            )

        if not workload_collections_complete:
            evidence_ids = [service["evidence_id"]]
            for kind in sorted(WORKLOAD_KINDS):
                collection_id = _collection_evidence_id(collections, kind)
                if collection_id:
                    evidence_ids.append(collection_id)
            issues.append(
                _issue(
                    code="SERVICE_SELECTOR_CONTROLLER_SCOPE_INCOMPLETE",
                    subject=source,
                    statement=(
                        f"{source} selector-to-controller reasoning is incomplete because one "
                        "or more workload-controller collections failed or are unavailable."
                    ),
                    evidence_ids=evidence_ids,
                    verification=(
                        f"Re-establish complete Deployment, StatefulSet, and DaemonSet observation "
                        f"before interpreting controller ownership for {source}."
                    ),
                    severity="UNKNOWN_WITH_CURRENT_SCOPE",
                )
            )
        elif not matches:
            issues.append(
                _issue(
                    code="SERVICE_SELECTOR_NO_CONTROLLER_MATCH",
                    subject=source,
                    statement=(
                        f"{source} has a selector, but no observed Deployment, StatefulSet, "
                        "or DaemonSet pod template matched it. The backend may be a standalone "
                        "Pod, Job-managed Pod, or otherwise outside the current controller scope."
                    ),
                    evidence_ids=[service["evidence_id"]],
                    verification=(
                        f"Inspect EndpointSlices or selected Pods for {source} before concluding "
                        "that the Service has no backend."
                    ),
                    severity="UNKNOWN_WITH_CURRENT_SCOPE",
                )
            )
        elif len(matches) > 1:
            issues.append(
                _issue(
                    code="SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES",
                    subject=source,
                    statement=(
                        f"{source} selector matched {len(matches)} observed workload controllers, "
                        "so controller-level ownership is ambiguous."
                    ),
                    evidence_ids=[service["evidence_id"]]
                    + [match["evidence_id"] for match in matches],
                    verification=(
                        f"Inspect EndpointSlices and Pod ownership for {source} before attributing "
                        "traffic to one controller."
                    ),
                    severity="AMBIGUOUS",
                )
            )

    # Direct workload spec -> PVC references.
    for workload in workloads:
        subject = workload["subject"]
        source = _label(subject)
        namespace = subject.get("namespace")

        for claim_name in workload["data"].get("persistent_volume_claims", []):
            target = f"PersistentVolumeClaim/{namespace}/{claim_name}"
            pvc = resources.get(("PersistentVolumeClaim", namespace, claim_name))

            if pvc:
                relations.append(
                    _relation(
                        relation_type="WORKLOAD_REFERENCES_PVC",
                        source=source,
                        target=target,
                        basis="OBSERVED_REFERENCE",
                        evidence_ids=[workload["evidence_id"], pvc["evidence_id"]],
                    )
                )
                continue

            evidence_ids = _with_collection_evidence(
                [workload["evidence_id"]], collections, "PersistentVolumeClaim"
            )
            if _collection_complete(collections, "PersistentVolumeClaim"):
                issues.append(
                    _issue(
                        code="WORKLOAD_PVC_NOT_OBSERVED",
                        subject=source,
                        target=target,
                        statement=(
                            f"{source} references {target}, but that PVC was not observed in the "
                            "current complete PVC collection."
                        ),
                        evidence_ids=evidence_ids,
                        verification=(
                            f"Verify the PVC reference and current namespace state before relying "
                            f"on storage for {source}."
                        ),
                    )
                )
            else:
                issues.append(
                    _issue(
                        code="WORKLOAD_PVC_TARGET_UNKNOWN",
                        subject=source,
                        target=target,
                        statement=(
                            f"{source} references {target}, but current PVC observation is incomplete "
                            "or failed, so target existence is unknown."
                        ),
                        evidence_ids=evidence_ids,
                        verification=(
                            "Re-establish a successful PVC collection before classifying storage "
                            f"availability for {source}."
                        ),
                        severity="UNKNOWN_WITH_CURRENT_SCOPE",
                    )
                )

    summary = {
        "relations_total": len(relations),
        "ingress_service_references": sum(
            relation["type"] == "INGRESS_REFERENCES_SERVICE" for relation in relations
        ),
        "service_workload_selector_matches": sum(
            relation["type"] == "SERVICE_SELECTOR_MATCHES_WORKLOAD" for relation in relations
        ),
        "workload_pvc_references": sum(
            relation["type"] == "WORKLOAD_REFERENCES_PVC" for relation in relations
        ),
        "issues_total": len(issues),
        "issues_requiring_verification": sum(
            issue["severity"]
            in {"REQUIRES_VERIFICATION", "UNKNOWN_WITH_CURRENT_SCOPE", "AMBIGUOUS"}
            for issue in issues
        ),
    }

    return {
        "topology_version": "0.1",
        "cluster_id": snapshot["cluster_id"],
        "generated_at": snapshot["generated_at"],
        "summary": summary,
        "relations": relations,
        "issues": issues,
    }


def render_topology_markdown(topology: dict[str, Any]) -> str:
    summary = topology["summary"]
    lines = [
        "# Kubernetes Relationship Context",
        "",
        f"Cluster: `{topology['cluster_id']}`",
        f"Generated: `{topology['generated_at']}`",
        "",
        "## Relationship coverage",
        "",
        f"- Ingress -> Service observed references: {summary['ingress_service_references']}",
        f"- Service -> workload selector inferences: {summary['service_workload_selector_matches']}",
        f"- Workload -> PVC observed references: {summary['workload_pvc_references']}",
        f"- Total relationships: {summary['relations_total']}",
        "",
        "## Relationship attention",
        "",
    ]

    if topology["issues"]:
        for issue in topology["issues"]:
            lines.append(f"- [{issue['severity']}] {issue['statement']}")
            lines.append(f"  Verification: {issue['required_live_verification']}")
    else:
        lines.append(
            "- No unresolved or ambiguous relationships were derived from the current scope."
        )

    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "Ingress-to-Service and direct workload-to-PVC edges come from observed resource references. Service-to-workload edges are selector-based inferences and do not prove current Pod or EndpointSlice routing.",
            "",
        ]
    )
    return "\n".join(lines)
