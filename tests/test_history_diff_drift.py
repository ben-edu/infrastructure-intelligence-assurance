import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema

from infra_assurance.change_context import build_change_context
from infra_assurance.drift import build_drift_report, load_declared_records
from infra_assurance.history import SnapshotHistoryStore
from infra_assurance.snapshot_diff import _subject_key, build_snapshot_diff

NOW = datetime(2026, 8, 14, 17, 10, tzinfo=timezone.utc)


def _ts(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _api_group_for_kind(kind):
    if kind in {"Deployment", "StatefulSet", "DaemonSet"}:
        return "apps"
    if kind == "Ingress":
        return "networking.k8s.io"
    return ""


def _subject(kind, namespace, name, api_group=""):
    return {
        "system": "kubernetes",
        "cluster": "k3s-main",
        "api_group": api_group,
        "kind": kind,
        "namespace": namespace,
        "name": name,
    }


def _observed(evidence_id, kind, namespace, name, data, *, api_group="", at=NOW):
    return {
        "schema_version": "0.1",
        "evidence_id": evidence_id,
        "plane": "observed",
        "subject": _subject(kind, namespace, name, api_group),
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": _ts(at),
        "observed_at": _ts(at),
        "expires_at": _ts(at + timedelta(minutes=5)),
        "data": data,
        "provenance": {
            "source_type": "kubernetes_api",
            "source_id": "k3s-main",
            "collector": "test",
            "collector_version": "0.5.0",
            "operation": f"LIST {kind}",
        },
        "errors": [],
    }


def _collection(evidence_id, kind, count, *, at=NOW, status="COMPLETE", expires_at=None):
    record = _observed(
        evidence_id,
        f"{kind}Collection",
        None,
        "*",
        {"resource_kind": kind, "item_count": count, "scope": "cluster"},
        api_group=_api_group_for_kind(kind),
        at=at,
    )
    if expires_at is not None:
        record["expires_at"] = expires_at
    if status == "FAILED_TO_OBSERVE":
        record.update(
            {
                "existence": "UNKNOWN",
                "observation_status": "FAILED_TO_OBSERVE",
                "observed_at": None,
                "expires_at": None,
                "data": {},
                "errors": [{"code": "KUBERNETES_FORBIDDEN", "summary": "denied"}],
            }
        )
    return record


def _snapshot(generated_at, evidence):
    return {
        "snapshot_version": "0.1",
        "cluster_id": "k3s-main",
        "generated_at": _ts(generated_at),
        "evidence": evidence,
    }


def _declared(evidence_id="decl-1", *, replicas=2, image="example/api:v1", at=NOW):
    return {
        "schema_version": "0.1",
        "evidence_id": evidence_id,
        "plane": "declared",
        "subject": _subject("Deployment", "apps", "api", "apps"),
        "existence": "PRESENT",
        "observation_status": "COMPLETE",
        "attempted_at": _ts(at),
        "observed_at": _ts(at),
        "expires_at": _ts(at + timedelta(hours=1)),
        "data": {"desired_replicas": replicas, "image": image},
        "provenance": {
            "source_type": "git",
            "source_id": "github.com/example/platform-config",
            "collector": "git-observer",
            "collector_version": "0.5.0",
            "operation": "read manifests/apps/api.yaml",
            "revision": "abc1234",
        },
        "errors": [],
    }


def _observed_deployment_snapshot(*, replicas=2, image="example/api:v1", collection_status="COMPLETE"):
    evidence = [
        _collection("ev-deploy-c", "Deployment", 1, status=collection_status),
    ]
    if collection_status == "COMPLETE":
        evidence.append(
            _observed(
                "ev-deploy",
                "Deployment",
                "apps",
                "api",
                {"desired_replicas": replicas, "ready_replicas": replicas, "images": [image]},
                api_group="apps",
            )
        )
    return _snapshot(NOW, evidence)


def test_history_retention_keeps_latest_immutable_snapshots(tmp_path):
    store = SnapshotHistoryStore(tmp_path / "history", retention=2)
    snapshots = [
        _snapshot(NOW + timedelta(minutes=i), [_collection(f"ev-c-{i}", "Node", 3, at=NOW + timedelta(minutes=i))])
        for i in range(3)
    ]

    first = store.append(snapshots[0])
    first_path = store.root / first["entry"]["file"]
    assert first_path.exists()

    store.append(snapshots[1])
    store.append(snapshots[2])
    index = store.read_index()

    assert len(index["snapshots"]) == 2
    assert not first_path.exists()
    assert index["snapshots"][-1]["generated_at"] == snapshots[2]["generated_at"]

    schema = json.loads(
        (Path(__file__).parents[1] / "schemas" / "history-index.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    ).validate(index)


def test_diff_classifies_added_removed_and_modified_only_with_complete_current_collections():
    previous = _snapshot(
        NOW - timedelta(minutes=5),
        [
            _collection("prev-deploy-c", "Deployment", 1, at=NOW - timedelta(minutes=5)),
            _collection("prev-service-c", "Service", 1, at=NOW - timedelta(minutes=5)),
            _observed("prev-api", "Deployment", "apps", "api", {"desired_replicas": 1}, api_group="apps", at=NOW - timedelta(minutes=5)),
            _observed("prev-svc", "Service", "apps", "old", {"type": "ClusterIP"}, at=NOW - timedelta(minutes=5)),
        ],
    )
    current = _snapshot(
        NOW,
        [
            _collection("cur-deploy-c", "Deployment", 2),
            _collection("cur-service-c", "Service", 0),
            _observed("cur-api", "Deployment", "apps", "api", {"desired_replicas": 2}, api_group="apps"),
            _observed("cur-worker", "Deployment", "apps", "worker", {"desired_replicas": 1}, api_group="apps"),
        ],
    )

    diff = build_snapshot_diff(
        previous,
        current,
        previous_snapshot_id="prev",
        current_snapshot_id="cur",
        now=NOW,
    )

    assert diff["summary"]["modified"] == 1
    assert diff["summary"]["added"] == 1
    assert diff["summary"]["removed"] == 1
    assert {item["classification"] for item in diff["changes"]} == {"MODIFIED", "ADDED", "REMOVED"}


def test_failed_current_collection_never_becomes_false_removal():
    previous = _snapshot(
        NOW - timedelta(minutes=5),
        [
            _collection("prev-c", "Service", 1, at=NOW - timedelta(minutes=5)),
            _observed("prev-svc", "Service", "apps", "api", {"type": "ClusterIP"}, at=NOW - timedelta(minutes=5)),
        ],
    )
    current = _snapshot(NOW, [_collection("cur-c", "Service", 0, status="FAILED_TO_OBSERVE")])

    diff = build_snapshot_diff(previous, current, previous_snapshot_id="prev", current_snapshot_id="cur", now=NOW)

    assert diff["summary"]["removed"] == 0
    assert diff["summary"]["unknown_kinds"] == 1
    assert diff["collection_failures"][0]["resource_kind"] == "Service"
    assert not diff["changes"]


def test_stale_current_collection_never_becomes_false_removal():
    previous = _snapshot(
        NOW - timedelta(minutes=5),
        [
            _collection("prev-c", "Service", 1, at=NOW - timedelta(minutes=5)),
            _observed("prev-svc", "Service", "apps", "api", {"type": "ClusterIP"}, at=NOW - timedelta(minutes=5)),
        ],
    )
    current = _snapshot(
        NOW,
        [_collection("cur-c", "Service", 0, expires_at=_ts(NOW - timedelta(seconds=1)))],
    )

    diff = build_snapshot_diff(previous, current, previous_snapshot_id="prev", current_snapshot_id="cur", now=NOW)

    assert diff["summary"]["removed"] == 0
    assert diff["unknowns"][0]["code"] == "CURRENT_COLLECTION_STALE"


def test_subject_identity_includes_api_group():
    apps = _subject("Deployment", "apps", "api", "apps")
    other = _subject("Deployment", "apps", "api", "example.io")
    assert _subject_key(apps) != _subject_key(other)


def test_drift_reports_in_sync_and_field_mismatch():
    observed = _observed_deployment_snapshot()
    in_sync = build_drift_report(observed, {"status": "AVAILABLE", "records": [_declared()], "errors": []}, now=NOW)
    assert in_sync["summary"]["in_sync"] == 1
    assert in_sync["summary"]["drift"] == 0

    drifted = build_drift_report(
        observed,
        {"status": "AVAILABLE", "records": [_declared(replicas=3)], "errors": []},
        now=NOW,
    )
    assert drifted["summary"]["drift"] == 1
    assert drifted["results"][0]["field_mismatches"][0]["field"] == "desired_replicas"


def test_failed_observed_collection_makes_drift_unknown_not_absent():
    observed = _observed_deployment_snapshot(collection_status="FAILED_TO_OBSERVE")
    report = build_drift_report(observed, {"status": "AVAILABLE", "records": [_declared()], "errors": []}, now=NOW)

    assert report["summary"]["drift"] == 0
    assert report["summary"]["unknown"] == 1
    assert report["unknowns"][0]["code"] == "OBSERVED_COLLECTION_FAILED"


def test_unconfigured_declared_state_is_unknown_not_zero_drift():
    report = build_drift_report(
        _observed_deployment_snapshot(),
        {"status": "DECLARED_STATE_UNAVAILABLE", "records": [], "errors": []},
        now=NOW,
    )
    assert report["status"] == "DECLARED_STATE_UNAVAILABLE"
    assert report["summary"]["declared_records"] == 0
    assert report["unknowns"][0]["code"] == "DECLARED_STATE_UNAVAILABLE"


def test_declared_loader_requires_git_revision(tmp_path):
    declared_dir = tmp_path / "declared"
    declared_dir.mkdir()
    invalid = _declared()
    invalid["provenance"].pop("revision")
    (declared_dir / "invalid.json").write_text(json.dumps(invalid), encoding="utf-8")

    loaded = load_declared_records(declared_dir)
    assert loaded["status"] == "DECLARED_STATE_ERRORS"
    assert not loaded["records"]
    assert "revision" in loaded["errors"][0]["error"]


def test_change_context_is_compact_and_keeps_mutation_disabled():
    diff = build_snapshot_diff(
        None,
        _observed_deployment_snapshot(),
        previous_snapshot_id=None,
        current_snapshot_id="current",
        now=NOW,
    )
    drift = build_drift_report(
        _observed_deployment_snapshot(),
        {"status": "DECLARED_STATE_UNAVAILABLE", "records": [], "errors": []},
        now=NOW,
    )
    context = build_change_context(diff, drift, now=NOW)

    assert context["task"]["mutation_allowed"] is False
    assert context["drift"]["status"] == "DECLARED_STATE_UNAVAILABLE"
    assert not context["recent_changes"]


def test_m2_outputs_validate_against_schemas():
    root = Path(__file__).parents[1]
    observed = _observed_deployment_snapshot()
    diff = build_snapshot_diff(None, observed, previous_snapshot_id=None, current_snapshot_id="current", now=NOW)
    drift = build_drift_report(
        observed,
        {"status": "DECLARED_STATE_UNAVAILABLE", "records": [], "errors": []},
        now=NOW,
    )
    context = build_change_context(diff, drift, now=NOW)

    for filename, value in [
        ("snapshot-diff.schema.json", diff),
        ("drift-report.schema.json", drift),
        ("change-context.schema.json", context),
    ]:
        schema = json.loads((root / "schemas" / filename).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(value)
