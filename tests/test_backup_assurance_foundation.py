from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from infra_assurance.backup_assurance_foundation import (
    build_backup_assurance_foundation,
    render_backup_assurance_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 15, 15, 0, 0, tzinfo=timezone.utc)


def _subject(kind: str, namespace: str | None, name: str, api_group: str = "") -> dict:
    return {
        "system": "kubernetes",
        "cluster": "k3s-main",
        "api_group": api_group,
        "kind": kind,
        "namespace": namespace,
        "name": name,
    }


def _collection(kind: str, evidence_id: str, *, status: str = "COMPLETE") -> dict:
    if status == "COMPLETE":
        return {
            "schema_version": "0.1",
            "evidence_id": evidence_id,
            "plane": "observed",
            "subject": _subject(f"{kind}Collection", None, "*", "apps" if kind in {"Deployment", "StatefulSet", "DaemonSet"} else ""),
            "existence": "PRESENT",
            "observation_status": "COMPLETE",
            "attempted_at": "2026-08-15T14:59:00Z",
            "observed_at": "2026-08-15T14:59:00Z",
            "expires_at": "2026-08-15T15:04:00Z",
            "data": {"resource_kind": kind, "item_count": 1, "scope": "cluster"},
            "provenance": {},
            "errors": [],
        }
    return {
        "schema_version": "0.1",
        "evidence_id": evidence_id,
        "plane": "observed",
        "subject": _subject(f"{kind}Collection", None, "*", "apps" if kind in {"Deployment", "StatefulSet", "DaemonSet"} else ""),
        "existence": "UNKNOWN",
        "observation_status": "FAILED_TO_OBSERVE",
        "attempted_at": "2026-08-15T14:59:00Z",
        "observed_at": None,
        "expires_at": None,
        "data": {},
        "provenance": {},
        "errors": [{"code": "TEST_FAILURE", "summary": "failed"}],
    }


def _pvc(name: str, evidence_id: str, *, expires_at: str = "2026-08-15T15:04:00Z") -> dict:
    return {
        "schema_version": "0.1",
        "evidence_id": evidence_id,
        "plane": "observed",
        "subject": _subject("PersistentVolumeClaim", "monitoring", name),
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": "2026-08-15T14:59:00Z",
        "observed_at": "2026-08-15T14:59:00Z",
        "expires_at": expires_at,
        "data": {
            "phase": "Bound",
            "storage_class": "local-path",
            "access_modes": ["ReadWriteOnce"],
            "requested_storage": "10Gi",
            "capacity": "10Gi",
            "volume_name": f"pv-{name}",
            "annotations": {"backup": "true"},
            "labels": {"protected": "yes"},
        },
        "provenance": {},
        "errors": [],
    }


def _snapshot() -> dict:
    return {
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T14:59:00Z",
        "mutation_allowed": False,
        "evidence": [
            _collection("PersistentVolumeClaim", "ev-pvc-collection"),
            _collection("Deployment", "ev-deploy-collection"),
            _collection("StatefulSet", "ev-sts-collection"),
            _collection("DaemonSet", "ev-ds-collection"),
            _pvc("prometheus-data", "ev-pvc-prom"),
            _pvc("unlinked-data", "ev-pvc-unlinked"),
        ],
    }


def _topology() -> dict:
    return {
        "topology_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": "2026-08-15T14:59:00Z",
        "summary": {},
        "relations": [
            {
                "type": "WORKLOAD_REFERENCES_PVC",
                "source": "StatefulSet/monitoring/prometheus",
                "target": "PersistentVolumeClaim/monitoring/prometheus-data",
                "basis": "OBSERVED_REFERENCE",
                "evidence_ids": ["ev-sts-prom", "ev-pvc-prom"],
            }
        ],
        "issues": [],
    }


def _asset(result: dict, name: str) -> dict:
    return next(
        item
        for item in result["assets"]
        if item["subject"]["name"] == name
    )


def test_complete_pvc_scope_builds_assets_but_never_infers_protection():
    result = build_backup_assurance_foundation(
        _snapshot(),
        _topology(),
        now=NOW,
    )

    assert result["backup_assurance_version"] == "0.1"
    assert result["mutation_allowed"] is False
    assert result["source_status"]["overall"] == "COMPLETE"
    assert result["source_status"]["kubernetes_pvc_inventory"]["observation_status"] == "COMPLETE"
    assert result["source_status"]["workload_pvc_relationships"] == "COMPLETE"
    assert result["scope"] == {
        "asset_type": "KUBERNETES_PVC",
        "derived_only": True,
        "authoritative_backup_source_integrated": False,
    }

    assert result["summary"]["assets_total"] == 2
    assert result["summary"]["assets_current"] == 2
    assert result["summary"]["protection_unknown"] == 2
    assert result["summary"]["restore_verification_unknown"] == 2
    assert result["summary"]["unprotected_claims"] == 0
    assert result["summary"]["authoritative_backup_sources_integrated"] == 0

    for asset in result["assets"]:
        assert asset["existence"] == "PRESENT"
        assert asset["observation_status"] == "COMPLETE"
        assert asset["assurance"]["protection_status"] == "UNKNOWN"
        assert asset["assurance"]["backup_freshness_status"] == "UNKNOWN"
        assert asset["assurance"]["integrity_verification_status"] == "UNKNOWN"
        assert asset["assurance"]["restore_verification_status"] == "UNKNOWN"
        assert asset["assurance"]["rpo_status"] == "UNKNOWN"
        assert asset["assurance"]["rto_status"] == "RTO_UNKNOWN"
        assert len(asset["required_evidence"]) == 8

    raw = json.dumps(result)
    assert '"backup": "true"' not in raw
    assert '"protected": "yes"' not in raw


def test_direct_workload_reference_is_context_not_backup_evidence():
    result = build_backup_assurance_foundation(
        _snapshot(),
        _topology(),
        now=NOW,
    )
    asset = _asset(result, "prometheus-data")

    assert asset["workload_context"]["status"] == "DIRECT_CONTROLLER_REFERENCES_OBSERVED"
    assert asset["workload_context"]["related_workloads_total"] == 1
    assert asset["workload_context"]["related_workloads"] == [
        {
            "subject": "StatefulSet/monitoring/prometheus",
            "basis": "OBSERVED_REFERENCE",
            "evidence_ids": ["ev-sts-prom", "ev-pvc-prom"],
        }
    ]
    assert asset["assurance"]["protection_status"] == "UNKNOWN"


def test_no_direct_relation_is_not_classified_as_orphan():
    result = build_backup_assurance_foundation(
        _snapshot(),
        _topology(),
        now=NOW,
    )
    asset = _asset(result, "unlinked-data")

    assert asset["workload_context"]["status"] == "NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED"
    assert asset["workload_context"]["related_workloads"] == []
    assert "not an orphan classification" in asset["workload_context"]["caveat"]


def test_incomplete_workload_collection_keeps_assets_but_marks_relationship_scope_partial():
    snapshot = _snapshot()
    snapshot["evidence"] = [
        item
        for item in snapshot["evidence"]
        if item["subject"]["kind"] != "StatefulSetCollection"
    ]
    snapshot["evidence"].append(
        _collection("StatefulSet", "ev-sts-failed", status="FAILED_TO_OBSERVE")
    )

    result = build_backup_assurance_foundation(
        snapshot,
        _topology(),
        now=NOW,
    )

    assert result["source_status"]["overall"] == "PARTIAL"
    assert result["source_status"]["workload_pvc_relationships"] == "PARTIAL"
    assert result["summary"]["assets_total"] == 2
    assert all(
        item["workload_context"]["status"] == "RELATION_SCOPE_INCOMPLETE"
        for item in result["assets"]
    )
    assert any(
        item["code"] == "KUBERNETES_WORKLOAD_PVC_RELATION_SCOPE_INCOMPLETE"
        for item in result["unknowns"]
    )
    assert all(
        item["assurance"]["protection_status"] == "UNKNOWN"
        for item in result["assets"]
    )


def test_failed_pvc_collection_is_failed_to_observe_not_zero_assets_claim():
    snapshot = _snapshot()
    snapshot["evidence"] = [
        item
        for item in snapshot["evidence"]
        if item["subject"]["kind"] not in {
            "PersistentVolumeClaimCollection",
            "PersistentVolumeClaim",
        }
    ]
    snapshot["evidence"].append(
        _collection(
            "PersistentVolumeClaim",
            "ev-pvc-failed",
            status="FAILED_TO_OBSERVE",
        )
    )

    result = build_backup_assurance_foundation(
        snapshot,
        _topology(),
        now=NOW,
    )

    assert result["source_status"]["overall"] == "FAILED_TO_OBSERVE"
    assert result["summary"]["assets_total"] == 0
    assert result["assets"] == []
    assert any(
        item["code"] == "KUBERNETES_PVC_COLLECTION_FAILED_TO_OBSERVE"
        for item in result["unknowns"]
    )

    text = render_backup_assurance_markdown(result)
    assert "asset existence is UNKNOWN" in text


def test_stale_pvc_is_preserved_as_stale_observed_asset():
    snapshot = _snapshot()
    for item in snapshot["evidence"]:
        if item["subject"]["kind"] == "PersistentVolumeClaim" and item["subject"]["name"] == "unlinked-data":
            item["expires_at"] = "2026-08-15T14:59:30Z"

    result = build_backup_assurance_foundation(
        snapshot,
        _topology(),
        now=NOW,
    )

    assert _asset(result, "unlinked-data")["freshness"] == "STALE"
    assert result["summary"]["assets_stale"] == 1


def test_cluster_mismatch_is_rejected():
    topology = _topology()
    topology["cluster_id"] = "other"

    try:
        build_backup_assurance_foundation(
            _snapshot(),
            topology,
            now=NOW,
        )
    except ValueError as exc:
        assert "same cluster" in str(exc)
    else:
        raise AssertionError("cluster mismatch should fail")


def test_schema_accepts_foundation_artifact():
    result = build_backup_assurance_foundation(
        _snapshot(),
        _topology(),
        now=NOW,
    )
    schema = json.loads(
        (ROOT / "schemas" / "backup-assurance-foundation.schema.json").read_text()
    )
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(result)


def test_markdown_keeps_unknown_distinct_from_unprotected():
    result = build_backup_assurance_foundation(
        _snapshot(),
        _topology(),
        now=NOW,
    )
    text = render_backup_assurance_markdown(result)

    assert "Protection UNKNOWN: 2" in text
    assert "UNPROTECTED claims: 0" in text
    assert "UNKNOWN is not UNPROTECTED" in text
    assert "StatefulSet/monitoring/prometheus" in text
