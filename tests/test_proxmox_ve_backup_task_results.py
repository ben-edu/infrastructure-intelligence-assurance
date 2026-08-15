from datetime import datetime, timezone

from infra_assurance.proxmox_ve_backup_task_results import collect_pve_backup_task_results


def source_artifact():
    return {
        "proxmox_ve_backup_evidence_version": "0.1",
        "mutation_allowed": False,
        "source": {"source_id": "pve-bm2", "node": "delfan"},
        "guests": [
            {"vmid": 100},
            {"vmid": 106},
        ],
        "recovery_points": [
            {
                "recovery_point_id": "rp-100-current",
                "vmid": 100,
                "created_at": "2026-05-08T06:13:59Z",
            },
            {
                "recovery_point_id": "rp-106-current",
                "vmid": 106,
                "created_at": "2026-08-14T16:13:14Z",
            },
            {
                "recovery_point_id": "rp-106-old",
                "vmid": 106,
                "created_at": "2025-11-24T08:50:52Z",
            },
        ],
    }


def credential_context():
    return {
        "credential_file_mode_secure": False,
        "tls_verification": False,
        "runtime_credential_approved": False,
        "discovery_override_used": True,
    }


def test_complete_task_history_projects_safe_results_and_strict_correlations():
    rows = [
        {
            "type": "vzdump",
            "id": "100",
            "starttime": 1778220839,
            "endtime": 1778220918,
            "status": "OK",
            "upid": "must-not-project",
            "user": "must-not-project",
        },
        {
            "type": "vzdump",
            "id": 106,
            "starttime": 1786723993,
            "endtime": 1786725593,
            "status": "OK",
            "upid": "must-not-project",
            "user": "must-not-project",
        },
    ]

    def get_json(path, params):
        assert path == "/api2/json/nodes/delfan/tasks"
        assert params == {"typefilter": "vzdump", "limit": "500"}
        return 200, rows, None

    artifact = collect_pve_backup_task_results(
        source_artifact(),
        get_json,
        source_id="pve-bm2",
        node="delfan",
        credential_context=credential_context(),
        now=datetime(2026, 8, 15, 18, 30, tzinfo=timezone.utc),
    )

    assert artifact["source"]["status"] == "COMPLETE"
    assert artifact["source"]["runtime_credential_approved"] is False
    assert artifact["mutation_allowed"] is False
    assert all(set(item) == {"task_result_id", "task_type", "node", "vmid", "start_time", "end_time", "result"} for item in artifact["task_results"])

    correlations = {item["recovery_point_id"]: item for item in artifact["recovery_point_correlations"]}
    assert correlations["rp-100-current"]["status"] == "STRICT_SUCCESS_TASK_MATCH"
    assert correlations["rp-100-current"]["start_delta_seconds"] == 0
    assert correlations["rp-106-current"]["status"] == "STRICT_SUCCESS_TASK_MATCH"
    assert correlations["rp-106-current"]["start_delta_seconds"] <= 2
    assert correlations["rp-106-old"]["status"] == "NO_STRICT_MATCH_IN_RETURNED_HISTORY"
    assert correlations["rp-106-old"]["task_result_id"] is None


def test_far_nearest_success_is_not_promoted_to_strict_match():
    def get_json(path, params):
        return 200, [
            {
                "type": "vzdump",
                "id": 106,
                "starttime": 1773134685,
                "endtime": 1773135059,
                "status": "OK",
            }
        ], None

    artifact = collect_pve_backup_task_results(
        source_artifact(),
        get_json,
        source_id="pve-bm2",
        node="delfan",
        credential_context=credential_context(),
    )

    old = next(item for item in artifact["recovery_point_correlations"] if item["recovery_point_id"] == "rp-106-old")
    assert old["status"] == "NO_STRICT_MATCH_IN_RETURNED_HISTORY"
    assert old["start_delta_seconds"] is None


def test_failed_observation_does_not_emit_task_absence():
    def get_json(path, params):
        return 403, None, "HTTP_ERROR"

    artifact = collect_pve_backup_task_results(
        source_artifact(),
        get_json,
        source_id="pve-bm2",
        node="delfan",
        credential_context=credential_context(),
    )

    assert artifact["source"]["status"] == "FAILED_TO_OBSERVE"
    assert artifact["task_results"] == []
    assert artifact["recovery_point_correlations"] == []
    assert "TASK_HISTORY_FAILED_TO_OBSERVE" in {item["code"] for item in artifact["unknowns"]}


def test_400_server_filter_falls_back_to_bounded_local_filter():
    calls = []

    def get_json(path, params):
        calls.append(params)
        if len(calls) == 1:
            return 400, None, "HTTP_ERROR"
        return 200, [{"type": "other", "id": 100}, {"type": "vzdump", "id": 100, "starttime": 1778220839, "endtime": 1778220918, "status": "OK"}], None

    artifact = collect_pve_backup_task_results(
        source_artifact(),
        get_json,
        source_id="pve-bm2",
        node="delfan",
        credential_context=credential_context(),
    )

    assert artifact["source"]["request_mode"] == "BOUNDED_LOCAL_TYPE_FILTER"
    assert len(artifact["task_results"]) == 1
    assert calls[1] == {"limit": "500"}


def test_limit_saturation_is_explicit_partial_history_unknown():
    rows = [
        {"type": "vzdump", "id": 100, "starttime": 1778220839 + i, "endtime": 1778220918 + i, "status": "OK"}
        for i in range(2)
    ]

    def get_json(path, params):
        return 200, rows, None

    artifact = collect_pve_backup_task_results(
        source_artifact(),
        get_json,
        source_id="pve-bm2",
        node="delfan",
        credential_context=credential_context(),
        task_limit=2,
    )

    assert artifact["source"]["limit_saturated"] is True
    assert "TASK_RESULT_LIMIT_SATURATED" in {item["code"] for item in artifact["unknowns"]}
