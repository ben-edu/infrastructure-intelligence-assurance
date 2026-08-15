from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evidence import freshness
from .io_utils import atomic_write_json, atomic_write_text

BACKUP_ASSURANCE_VERSION = "0.1"
ASSET_TYPE = "KUBERNETES_PVC"
WORKLOAD_KINDS = ("Deployment", "StatefulSet", "DaemonSet")


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if isinstance(value, str) and value))


def _subject_label(subject: dict[str, Any]) -> str:
    namespace = subject.get("namespace")
    if namespace:
        return f"{subject.get('kind')}/{namespace}/{subject.get('name')}"
    return f"{subject.get('kind')}/{subject.get('name')}"


def _collections(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for envelope in snapshot.get("evidence", []):
        subject = envelope.get("subject", {})
        kind = str(subject.get("kind") or "")
        if kind.endswith("Collection"):
            result[kind.removesuffix("Collection")] = envelope
    return result


def _collection_observation_status(
    collections: dict[str, dict[str, Any]],
    kind: str,
) -> str:
    envelope = collections.get(kind)
    if not envelope:
        return "FAILED_TO_OBSERVE"
    return str(envelope.get("observation_status") or "FAILED_TO_OBSERVE")


def _collection_freshness(
    collections: dict[str, dict[str, Any]],
    kind: str,
    now: datetime,
) -> str:
    envelope = collections.get(kind)
    if not envelope:
        return "UNKNOWN"
    try:
        return freshness(envelope, now)
    except ValueError:
        return "UNKNOWN"


def _relationship_scope_status(
    collections: dict[str, dict[str, Any]],
) -> str:
    required = ("PersistentVolumeClaim", *WORKLOAD_KINDS)
    if all(
        _collection_observation_status(collections, kind) == "COMPLETE"
        for kind in required
    ):
        return "COMPLETE"
    return "PARTIAL"


def _overall_status(
    pvc_status: str,
    relationship_status: str,
) -> str:
    if pvc_status != "COMPLETE":
        return "FAILED_TO_OBSERVE"
    if relationship_status != "COMPLETE":
        return "PARTIAL"
    return "COMPLETE"


def _pvc_envelopes(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for envelope in snapshot.get("evidence", []):
        subject = envelope.get("subject", {})
        if subject.get("kind") != "PersistentVolumeClaim":
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
            item.get("subject", {}).get("namespace") or "",
            item.get("subject", {}).get("name") or "",
        ),
    )


def _relations_by_pvc(topology: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for relation in topology.get("relations", []):
        if relation.get("type") != "WORKLOAD_REFERENCES_PVC":
            continue
        target = relation.get("target")
        if not isinstance(target, str) or not target:
            continue
        result.setdefault(target, []).append(relation)
    for values in result.values():
        values.sort(key=lambda item: str(item.get("source") or ""))
    return result


def _required_backup_evidence() -> list[dict[str, Any]]:
    specs = (
        (
            "OBSERVE_BACKUP_MECHANISM",
            "BACKUP_MECHANISM",
            "Identify the authoritative backup mechanism that protects this asset, if any.",
        ),
        (
            "OBSERVE_LAST_SUCCESSFUL_BACKUP",
            "LAST_SUCCESSFUL_BACKUP",
            "Observe the latest successful backup result from the authoritative backup system.",
        ),
        (
            "OBSERVE_BACKUP_RETENTION",
            "BACKUP_RETENTION",
            "Observe the effective retention policy and retained recovery points.",
        ),
        (
            "OBSERVE_BACKUP_FAILURE_DOMAIN",
            "BACKUP_FAILURE_DOMAIN",
            "Verify whether backup copies are stored outside the same relevant failure domain.",
        ),
        (
            "OBSERVE_BACKUP_INTEGRITY_VERIFICATION",
            "BACKUP_INTEGRITY_VERIFICATION",
            "Observe the latest authoritative integrity or verification result for protected data.",
        ),
        (
            "OBSERVE_RESTORE_TEST",
            "RESTORE_TEST",
            "Observe the latest actual restore test and whether application/data recovery was verified.",
        ),
        (
            "OBSERVE_RPO_TARGET_AND_RESULT",
            "RPO_TARGET_AND_RESULT",
            "Observe the target RPO and enough backup history to evaluate the current result.",
        ),
        (
            "OBSERVE_RTO_TARGET_AND_RESULT",
            "RTO_TARGET_AND_RESULT",
            "Observe the target RTO and a restore test sufficient to evaluate recovery time.",
        ),
    )
    return [
        {
            "code": code,
            "target": target,
            "check": check,
            "authoritative_source_required": True,
        }
        for code, target, check in specs
    ]


def _storage_projection(envelope: dict[str, Any]) -> dict[str, Any]:
    data = envelope.get("data", {})
    allowed = (
        "phase",
        "storage_class",
        "access_modes",
        "requested_storage",
        "capacity",
        "volume_name",
    )
    return {key: data.get(key) for key in allowed}


def _workload_context(
    pvc_label: str,
    relations: list[dict[str, Any]],
    relationship_scope_status: str,
) -> dict[str, Any]:
    related = [
        {
            "subject": relation.get("source"),
            "basis": relation.get("basis"),
            "evidence_ids": list(relation.get("evidence_ids", [])),
        }
        for relation in relations
        if relation.get("source")
    ]

    if relationship_scope_status != "COMPLETE":
        status = "RELATION_SCOPE_INCOMPLETE"
        caveat = (
            "One or more workload/PVC observation collections are incomplete, so workload "
            "relationship coverage for this PVC is incomplete."
        )
    elif related:
        status = "DIRECT_CONTROLLER_REFERENCES_OBSERVED"
        caveat = (
            "Related workloads come only from direct observed controller-spec PVC references. "
            "This does not prove exclusive ownership or current Pod-level use."
        )
    else:
        status = "NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED"
        caveat = (
            f"No direct Deployment/StatefulSet/DaemonSet PVC reference was observed for {pvc_label}. "
            "This is not an orphan classification: Pod-level mounts, generated StatefulSet claims, "
            "Jobs, or other consumers may be outside the current relationship model."
        )

    return {
        "status": status,
        "related_workloads": related,
        "related_workloads_total": len(related),
        "caveat": caveat,
    }


def _asset_projection(
    envelope: dict[str, Any],
    *,
    now: datetime,
    relations: list[dict[str, Any]],
    relationship_scope_status: str,
    pvc_collection_evidence_id: str | None,
) -> dict[str, Any]:
    subject = envelope["subject"]
    label = _subject_label(subject)
    try:
        freshness_state = freshness(envelope, now)
    except ValueError:
        freshness_state = "UNKNOWN"

    workload_context = _workload_context(
        label,
        relations,
        relationship_scope_status,
    )

    evidence_ids = [envelope.get("evidence_id")]
    if pvc_collection_evidence_id:
        evidence_ids.append(pvc_collection_evidence_id)
    for relation in workload_context["related_workloads"]:
        evidence_ids.extend(relation.get("evidence_ids", []))

    namespace = subject.get("namespace") or "-"
    return {
        "asset_id": (
            f"backup-asset:kubernetes:{subject.get('cluster')}:pvc:"
            f"{namespace}:{subject.get('name')}"
        ),
        "asset_type": ASSET_TYPE,
        "subject": subject,
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "freshness": freshness_state,
        "observed_at": envelope.get("observed_at"),
        "expires_at": envelope.get("expires_at"),
        "storage": _storage_projection(envelope),
        "workload_context": workload_context,
        "assurance": {
            "protection_status": "UNKNOWN",
            "backup_freshness_status": "UNKNOWN",
            "integrity_verification_status": "UNKNOWN",
            "restore_verification_status": "UNKNOWN",
            "rpo_status": "UNKNOWN",
            "rto_status": "RTO_UNKNOWN",
            "basis": ["AUTHORITATIVE_BACKUP_EVIDENCE_NOT_INTEGRATED"],
            "statement": (
                "No authoritative backup-system evidence is integrated by this foundation slice. "
                "UNKNOWN does not mean the asset is unprotected."
            ),
        },
        "required_evidence": _required_backup_evidence(),
        "evidence_ids": _unique(evidence_ids),
    }


def build_backup_assurance_foundation(
    snapshot: dict[str, Any],
    topology: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Derive stateful Kubernetes asset candidates without inferring backup protection."""
    if snapshot.get("cluster_id") != topology.get("cluster_id"):
        raise ValueError("backup assurance inputs must target the same cluster")

    now = now or datetime.now(timezone.utc)
    cluster_id = str(snapshot.get("cluster_id") or "")
    if not cluster_id:
        raise ValueError("snapshot must identify a cluster")

    collections = _collections(snapshot)
    pvc_collection = collections.get("PersistentVolumeClaim")
    pvc_status = _collection_observation_status(collections, "PersistentVolumeClaim")
    relationship_status = _relationship_scope_status(collections)
    overall = _overall_status(pvc_status, relationship_status)
    pvc_freshness = _collection_freshness(collections, "PersistentVolumeClaim", now)
    relation_index = _relations_by_pvc(topology)

    assets: list[dict[str, Any]] = []
    if pvc_status == "COMPLETE":
        for envelope in _pvc_envelopes(snapshot):
            label = _subject_label(envelope["subject"])
            assets.append(
                _asset_projection(
                    envelope,
                    now=now,
                    relations=relation_index.get(label, []),
                    relationship_scope_status=relationship_status,
                    pvc_collection_evidence_id=(
                        pvc_collection.get("evidence_id") if pvc_collection else None
                    ),
                )
            )

    unknowns: list[dict[str, Any]] = []
    if pvc_status != "COMPLETE":
        unknowns.append(
            {
                "code": "KUBERNETES_PVC_COLLECTION_FAILED_TO_OBSERVE",
                "subject": "PersistentVolumeClaim/*",
                "statement": (
                    "Current PVC collection is not complete; stateful Kubernetes asset existence "
                    "cannot be classified from this cycle."
                ),
                "evidence_ids": [pvc_collection.get("evidence_id")] if pvc_collection else [],
            }
        )
    if relationship_status != "COMPLETE":
        unknowns.append(
            {
                "code": "KUBERNETES_WORKLOAD_PVC_RELATION_SCOPE_INCOMPLETE",
                "subject": None,
                "statement": (
                    "One or more Deployment, StatefulSet, DaemonSet, or PVC collections are not "
                    "complete; workload-to-PVC relationship coverage is partial."
                ),
                "evidence_ids": _unique(
                    [
                        collections[kind].get("evidence_id")
                        for kind in ("PersistentVolumeClaim", *WORKLOAD_KINDS)
                        if kind in collections
                    ]
                ),
            }
        )

    unknowns.append(
        {
            "code": "AUTHORITATIVE_BACKUP_SOURCE_NOT_INTEGRATED",
            "subject": None,
            "statement": (
                "This foundation slice does not query an authoritative backup system, so backup, "
                "retention, integrity, restore, RPO, and RTO assurance remain UNKNOWN."
            ),
            "evidence_ids": [],
        }
    )

    freshness_counts: dict[str, int] = {}
    for asset in assets:
        key = str(asset["freshness"])
        freshness_counts[key] = freshness_counts.get(key, 0) + 1

    return {
        "backup_assurance_version": BACKUP_ASSURANCE_VERSION,
        "cluster_id": cluster_id,
        "generated_at": _rfc3339(now),
        "mutation_allowed": False,
        "scope": {
            "asset_type": ASSET_TYPE,
            "derived_only": True,
            "authoritative_backup_source_integrated": False,
        },
        "source_status": {
            "overall": overall,
            "kubernetes_pvc_inventory": {
                "observation_status": pvc_status,
                "freshness": pvc_freshness,
                "evidence_id": pvc_collection.get("evidence_id") if pvc_collection else None,
            },
            "workload_pvc_relationships": relationship_status,
        },
        "summary": {
            "assets_total": len(assets),
            "assets_current": freshness_counts.get("CURRENT", 0),
            "assets_stale": freshness_counts.get("STALE", 0),
            "assets_freshness_unknown": freshness_counts.get("UNKNOWN", 0),
            "assets_with_direct_workload_reference": sum(
                asset["workload_context"]["related_workloads_total"] > 0
                for asset in assets
            ),
            "protection_unknown": len(assets),
            "restore_verification_unknown": len(assets),
            "unprotected_claims": 0,
            "authoritative_backup_sources_integrated": 0,
        },
        "assets": assets,
        "unknowns": unknowns,
        "caveats": [
            "Kubernetes PVC existence and storage metadata are not backup evidence.",
            "StorageClass, PVC phase, capacity, volume name, workload kind, labels, names, snapshots, or naming conventions must not be interpreted as proof of protection without authoritative backup evidence.",
            "UNKNOWN protection does not mean UNPROTECTED. UNPROTECTED requires sufficient complete authoritative backup evidence supporting that classification.",
            "A backup that has not been successfully restored must not be treated as fully verified protection.",
        ],
    }


def render_backup_assurance_markdown(artifact: dict[str, Any]) -> str:
    summary = artifact["summary"]
    source = artifact["source_status"]
    lines = [
        "# Backup and Recovery Assurance — Kubernetes PVC Foundation",
        "",
        f"Cluster: `{artifact['cluster_id']}`",
        f"Generated: `{artifact['generated_at']}`",
        "Mutation allowed: `false`",
        f"Overall source status: `{source['overall']}`",
        f"PVC observation: `{source['kubernetes_pvc_inventory']['observation_status']}` / freshness `{source['kubernetes_pvc_inventory']['freshness']}`",
        f"Workload/PVC relationship scope: `{source['workload_pvc_relationships']}`",
        "",
        "## Summary",
        "",
        f"- PVC assets observed: {summary['assets_total']}",
        f"- Current assets: {summary['assets_current']}",
        f"- Stale assets: {summary['assets_stale']}",
        f"- Assets with direct controller reference: {summary['assets_with_direct_workload_reference']}",
        f"- Protection UNKNOWN: {summary['protection_unknown']}",
        f"- Restore verification UNKNOWN: {summary['restore_verification_unknown']}",
        f"- UNPROTECTED claims: {summary['unprotected_claims']}",
        "",
        "## Stateful asset candidates",
        "",
    ]

    if not artifact["assets"]:
        if source["kubernetes_pvc_inventory"]["observation_status"] == "COMPLETE":
            lines.append("- No PVC assets were present in the current complete collection.")
        else:
            lines.append("- PVC asset existence is UNKNOWN because the current collection did not complete.")

    for asset in artifact["assets"]:
        subject = _subject_label(asset["subject"])
        workloads = [
            item["subject"]
            for item in asset["workload_context"]["related_workloads"]
        ]
        lines.append(
            f"- {subject} phase={asset['storage'].get('phase')} capacity={asset['storage'].get('capacity')} "
            f"freshness={asset['freshness']} protection=UNKNOWN restore=UNKNOWN"
        )
        lines.append(
            "  - Direct workload references: "
            + (", ".join(workloads) if workloads else "none observed in current controller relation scope")
        )
        lines.append(
            f"  - Relationship status: {asset['workload_context']['status']}"
        )

    lines.extend(
        [
            "",
            "## Trust boundary",
            "",
            "This artifact identifies stateful Kubernetes PVC assets from current accepted Kubernetes evidence. It does not query a backup system. Protection, retention, integrity, restore, RPO, and RTO remain UNKNOWN until authoritative backup evidence is integrated. UNKNOWN is not UNPROTECTED.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Derive Kubernetes PVC backup-assurance foundation context from local evidence."
    )
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--topology", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args()

    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    topology = json.loads(args.topology.read_text(encoding="utf-8"))
    artifact = build_backup_assurance_foundation(snapshot, topology)
    atomic_write_json(args.out, artifact)
    if args.summary_out:
        atomic_write_text(args.summary_out, render_backup_assurance_markdown(artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
