from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

SCOPE_VALIDATION_VERSION = "0.2"

VALIDATED = "VALIDATED_INFRASTRUCTURE_SUBJECT"
UNVERIFIED = "UNVERIFIED_SIGNAL_DIMENSION"
INFERRED = "INFERRED_RELATION"
PLATFORM = "PLATFORM_FALLBACK"


def _resource_index(
    snapshot: dict[str, Any],
) -> tuple[
    dict[tuple[str, str | None, str], dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    resources: dict[tuple[str, str | None, str], dict[str, Any]] = {}
    collections: dict[str, dict[str, Any]] = {}

    for envelope in snapshot.get("evidence", []):
        subject = envelope.get("subject", {})
        kind = subject.get("kind")
        name = subject.get("name")
        if not isinstance(kind, str) or not isinstance(name, str):
            continue

        if kind.endswith("Collection"):
            collections[kind.removesuffix("Collection")] = envelope
            continue

        if (
            envelope.get("observation_status") == "COMPLETE"
            and envelope.get("existence") == "PRESENT"
        ):
            resources[(kind, subject.get("namespace"), name)] = envelope

    return resources, collections


def _collection_status(
    collections: dict[str, dict[str, Any]],
    kind: str,
) -> str:
    envelope = collections.get(kind)
    if not envelope:
        return "MISSING"
    return str(envelope.get("observation_status") or "MISSING")


def _collection_evidence_id(
    collections: dict[str, dict[str, Any]],
    kind: str,
) -> str | None:
    envelope = collections.get(kind)
    if not envelope:
        return None
    value = envelope.get("evidence_id")
    return value if isinstance(value, str) else None


def _platform_scope(cluster_id: str, basis: list[str]) -> dict[str, Any]:
    return {
        "type": "PLATFORM",
        "subject": f"Platform/{cluster_id}",
        "basis": basis,
    }


def _namespace_subject(namespace: str) -> str:
    return f"Namespace/{namespace}"


def _validation(
    *,
    status: str,
    claimed_subject: str | None,
    validated_subject: str | None,
    basis: list[str],
    evidence_ids: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "claimed_subject": claimed_subject,
        "validated_subject": validated_subject,
        "basis": list(dict.fromkeys(basis)),
        "evidence_ids": list(dict.fromkeys(evidence_ids)),
    }


def _validated_namespace(
    namespace: str,
    resources: dict[tuple[str, str | None, str], dict[str, Any]],
) -> dict[str, Any] | None:
    return resources.get(("Namespace", None, namespace))


def _fallback_from_unverified_resource(
    *,
    alert: dict[str, Any],
    claimed_subject: str,
    reason_code: str,
    reason_basis: str,
    resources: dict[tuple[str, str | None, str], dict[str, Any]],
    collections: dict[str, dict[str, Any]],
    cluster_id: str,
    collection_kind: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    labels = alert.get("labels", {})
    namespace = labels.get("namespace") if isinstance(labels, dict) else None
    evidence_ids: list[str] = []
    collection_evidence_id = _collection_evidence_id(collections, collection_kind)
    if collection_evidence_id:
        evidence_ids.append(collection_evidence_id)

    if isinstance(namespace, str) and namespace:
        namespace_record = _validated_namespace(namespace, resources)
        if namespace_record is not None:
            evidence_ids.append(namespace_record["evidence_id"])
            scope = {
                "type": "NAMESPACE",
                "subject": _namespace_subject(namespace),
                "basis": [
                    "ALERTMANAGER_NAMESPACE_LABEL",
                    "CURRENT_NAMESPACE_OBSERVATION",
                    reason_basis,
                ],
            }
            validation = _validation(
                status=UNVERIFIED,
                claimed_subject=claimed_subject,
                validated_subject=scope["subject"],
                basis=[reason_basis, "CURRENT_NAMESPACE_OBSERVATION"],
                evidence_ids=evidence_ids,
            )
            warning = {
                "code": reason_code,
                "statement": (
                    f"Alert {alert['alertmanager_alert_id']} carried signal labels that suggested "
                    f"{claimed_subject}, but that infrastructure subject was not validated. "
                    f"The weaker observed namespace scope {scope['subject']} was retained instead."
                ),
                "evidence_ids": list(dict.fromkeys([alert["evidence_id"]] + evidence_ids)),
            }
            return scope, validation, warning

    scope = _platform_scope(
        cluster_id,
        ["ALERTMANAGER_ALERT_WITHOUT_VALIDATED_RESOURCE_SCOPE", reason_basis],
    )
    validation = _validation(
        status=UNVERIFIED,
        claimed_subject=claimed_subject,
        validated_subject=scope["subject"],
        basis=[reason_basis, "PLATFORM_SCOPE_FALLBACK"],
        evidence_ids=evidence_ids,
    )
    warning = {
        "code": reason_code,
        "statement": (
            f"Alert {alert['alertmanager_alert_id']} carried signal labels that suggested "
            f"{claimed_subject}, but that infrastructure subject was not validated and no "
            "stronger observed namespace scope was available; platform scope was retained."
        ),
        "evidence_ids": list(dict.fromkeys([alert["evidence_id"]] + evidence_ids)),
    }
    return scope, validation, warning


def _validate_attention_scope(
    alert: dict[str, Any],
    *,
    resources: dict[tuple[str, str | None, str], dict[str, Any]],
    collections: dict[str, dict[str, Any]],
    cluster_id: str,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any] | None,
    set[str],
]:
    scope = deepcopy(alert.get("scope", {}))
    scope_type = scope.get("type")
    claimed_subject = scope.get("subject") if isinstance(scope.get("subject"), str) else None
    required_collections: set[str] = set()

    if scope_type == "WORKLOAD":
        validation = _validation(
            status=INFERRED,
            claimed_subject=claimed_subject,
            validated_subject=None,
            basis=["PROMETHEUS_TO_WORKLOAD_RELATION_REMAINS_INFERENCE"],
            evidence_ids=[],
        )
        return scope, validation, None, required_collections

    if scope_type == "NODE" and claimed_subject:
        required_collections.add("Node")
        name = claimed_subject.removeprefix("Node/")
        record = resources.get(("Node", None, name))
        if record is not None:
            scope["basis"] = list(
                dict.fromkeys(scope.get("basis", []) + ["CURRENT_NODE_OBSERVATION"])
            )
            validation = _validation(
                status=VALIDATED,
                claimed_subject=claimed_subject,
                validated_subject=claimed_subject,
                basis=["ALERTMANAGER_NODE_LABEL", "CURRENT_NODE_OBSERVATION"],
                evidence_ids=[record["evidence_id"]],
            )
            return scope, validation, None, required_collections

        status = _collection_status(collections, "Node")
        code = (
            "ALERT_SCOPE_NODE_SIGNAL_NOT_OBSERVED"
            if status == "COMPLETE"
            else "ALERT_SCOPE_NODE_VALIDATION_INCOMPLETE"
        )
        basis = (
            "NODE_SIGNAL_DIMENSION_NOT_OBSERVED"
            if status == "COMPLETE"
            else "NODE_OBSERVATION_INCOMPLETE"
        )
        fallback_scope, validation, warning = _fallback_from_unverified_resource(
            alert=alert,
            claimed_subject=claimed_subject,
            reason_code=code,
            reason_basis=basis,
            resources=resources,
            collections=collections,
            cluster_id=cluster_id,
            collection_kind="Node",
        )
        return fallback_scope, validation, warning, required_collections

    if scope_type == "SERVICE" and claimed_subject:
        required_collections.add("Service")
        parts = claimed_subject.split("/", 2)
        if len(parts) == 3:
            namespace, name = parts[1], parts[2]
            record = resources.get(("Service", namespace, name))
        else:
            record = None

        if record is not None:
            scope["basis"] = list(
                dict.fromkeys(scope.get("basis", []) + ["CURRENT_SERVICE_OBSERVATION"])
            )
            validation = _validation(
                status=VALIDATED,
                claimed_subject=claimed_subject,
                validated_subject=claimed_subject,
                basis=[
                    "ALERTMANAGER_NAMESPACE_SERVICE_LABELS",
                    "CURRENT_SERVICE_OBSERVATION",
                ],
                evidence_ids=[record["evidence_id"]],
            )
            return scope, validation, None, required_collections

        status = _collection_status(collections, "Service")
        code = (
            "ALERT_SCOPE_SERVICE_SIGNAL_NOT_OBSERVED"
            if status == "COMPLETE"
            else "ALERT_SCOPE_SERVICE_VALIDATION_INCOMPLETE"
        )
        basis = (
            "SERVICE_SIGNAL_DIMENSION_NOT_OBSERVED"
            if status == "COMPLETE"
            else "SERVICE_OBSERVATION_INCOMPLETE"
        )
        fallback_scope, validation, warning = _fallback_from_unverified_resource(
            alert=alert,
            claimed_subject=claimed_subject,
            reason_code=code,
            reason_basis=basis,
            resources=resources,
            collections=collections,
            cluster_id=cluster_id,
            collection_kind="Service",
        )
        return fallback_scope, validation, warning, required_collections

    if scope_type == "NAMESPACE" and claimed_subject:
        required_collections.add("Namespace")
        namespace = claimed_subject.removeprefix("Namespace/")
        record = _validated_namespace(namespace, resources)
        if record is not None:
            scope["basis"] = list(
                dict.fromkeys(scope.get("basis", []) + ["CURRENT_NAMESPACE_OBSERVATION"])
            )
            validation = _validation(
                status=VALIDATED,
                claimed_subject=claimed_subject,
                validated_subject=claimed_subject,
                basis=["ALERTMANAGER_NAMESPACE_LABEL", "CURRENT_NAMESPACE_OBSERVATION"],
                evidence_ids=[record["evidence_id"]],
            )
            return scope, validation, None, required_collections

        status = _collection_status(collections, "Namespace")
        code = (
            "ALERT_SCOPE_NAMESPACE_SIGNAL_NOT_OBSERVED"
            if status == "COMPLETE"
            else "ALERT_SCOPE_NAMESPACE_VALIDATION_INCOMPLETE"
        )
        basis = (
            "NAMESPACE_SIGNAL_DIMENSION_NOT_OBSERVED"
            if status == "COMPLETE"
            else "NAMESPACE_OBSERVATION_INCOMPLETE"
        )
        fallback_scope = _platform_scope(
            cluster_id,
            ["ALERTMANAGER_ALERT_WITHOUT_VALIDATED_RESOURCE_SCOPE", basis],
        )
        evidence_ids: list[str] = []
        collection_evidence_id = _collection_evidence_id(collections, "Namespace")
        if collection_evidence_id:
            evidence_ids.append(collection_evidence_id)
        validation = _validation(
            status=UNVERIFIED,
            claimed_subject=claimed_subject,
            validated_subject=fallback_scope["subject"],
            basis=[basis, "PLATFORM_SCOPE_FALLBACK"],
            evidence_ids=evidence_ids,
        )
        warning = {
            "code": code,
            "statement": (
                f"Alert {alert['alertmanager_alert_id']} carried namespace signal dimension "
                f"{claimed_subject}, but that namespace identity was not validated; platform "
                "scope was retained instead."
            ),
            "evidence_ids": list(dict.fromkeys([alert["evidence_id"]] + evidence_ids)),
        }
        return fallback_scope, validation, warning, required_collections

    validation = _validation(
        status=PLATFORM,
        claimed_subject=claimed_subject,
        validated_subject=scope.get("subject") if isinstance(scope.get("subject"), str) else None,
        basis=["NO_STRONGER_INFRASTRUCTURE_SUBJECT_CLAIMED"],
        evidence_ids=[],
    )
    return scope, validation, None, required_collections


def _kubernetes_scope_status(
    required_collections: set[str],
    collections: dict[str, dict[str, Any]],
) -> str:
    if not required_collections:
        return "COMPLETE"

    statuses = [_collection_status(collections, kind) for kind in sorted(required_collections)]
    if statuses and all(status == "FAILED_TO_OBSERVE" for status in statuses):
        return "FAILED_TO_OBSERVE"
    if any(status != "COMPLETE" for status in statuses):
        return "PARTIAL"
    return "COMPLETE"


def validate_alert_attention_scopes(
    alert_attention: dict[str, Any],
    kubernetes_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Validate label-derived alert scope against same-cycle Kubernetes evidence."""
    if alert_attention.get("cluster_id") != kubernetes_snapshot.get("cluster_id"):
        raise ValueError("Alert attention and Kubernetes snapshot must target the same cluster")

    result = deepcopy(alert_attention)
    cluster_id = str(result["cluster_id"])
    resources, collections = _resource_index(kubernetes_snapshot)

    corrected: list[dict[str, Any]] = []
    new_unknowns: list[dict[str, Any]] = []
    required_collections: set[str] = set()

    for item in result.get("attention", []):
        updated = deepcopy(item)
        scope, validation, warning, required = _validate_attention_scope(
            updated,
            resources=resources,
            collections=collections,
            cluster_id=cluster_id,
        )
        required_collections.update(required)
        updated["scope"] = scope
        updated["scope_validation"] = validation
        updated["evidence_ids"] = list(
            dict.fromkeys(updated.get("evidence_ids", []) + validation["evidence_ids"])
        )
        corrected.append(updated)
        if warning:
            new_unknowns.append(warning)

    result["alert_attention_version"] = SCOPE_VALIDATION_VERSION
    result["attention"] = corrected
    result["unknowns"] = list(result.get("unknowns", [])) + new_unknowns
    result.setdefault("source_status", {})["kubernetes_scope"] = _kubernetes_scope_status(
        required_collections,
        collections,
    )

    scope_counts = Counter(item["scope"]["type"] for item in corrected)
    validation_counts = Counter(
        item["scope_validation"]["status"] for item in corrected
    )
    summary = dict(result.get("summary", {}))
    summary.update(
        {
            "scope_workload": scope_counts["WORKLOAD"],
            "scope_node": scope_counts["NODE"],
            "scope_service": scope_counts["SERVICE"],
            "scope_namespace": scope_counts["NAMESPACE"],
            "scope_platform": scope_counts["PLATFORM"],
            "scope_identity_validated": validation_counts[VALIDATED],
            "scope_signal_dimension_unverified": validation_counts[UNVERIFIED],
            "scope_relation_inferred": validation_counts[INFERRED],
            "scope_platform_fallback": validation_counts[PLATFORM],
        }
    )
    result["summary"] = summary

    caveats = list(result.get("caveats", []))
    caveats.extend(
        [
            "Alert labels remain signal dimensions. A Service, Node, or Namespace scope is treated as an infrastructure subject only when the same-cycle Kubernetes snapshot validates that exact identity.",
            "An unvalidated Service signal dimension is not rewritten to another Service merely because a similarly named Service exists elsewhere; a validated Namespace or Platform fallback is used instead.",
        ]
    )
    result["caveats"] = list(dict.fromkeys(caveats))
    return result
