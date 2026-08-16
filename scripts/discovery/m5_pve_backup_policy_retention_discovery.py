from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from infra_assurance.proxmox_ve_backup_evidence import build_getter_from_env

ENV_FILE = Path(
    "/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env"
)

SELECTED_VMIDS = {
    100,
    101,
    102,
    103,
    104,
    105,
    106,
    107,
    108,
    109,
    110,
    9000,
}

RETENTION_KEYS = (
    "keep-last",
    "keep-hourly",
    "keep-daily",
    "keep-weekly",
    "keep-monthly",
    "keep-yearly",
)


def _truthy(value: Any) -> bool | None:
    if value in (True, 1, "1", "true", "yes", "on"):
        return True
    if value in (False, 0, "0", "false", "no", "off"):
        return False
    return None


def _parse_vmid_list(value: Any) -> list[int]:
    if not isinstance(value, str):
        return []
    result: list[int] = []
    for token in value.replace(";", ",").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            vmid = int(token)
        except ValueError:
            continue
        if vmid > 0 and vmid not in result:
            result.append(vmid)
    return sorted(result)


def _safe_retention(job: dict[str, Any]) -> dict[str, Any]:
    projected: dict[str, Any] = {
        key.replace("-", "_"): None for key in RETENTION_KEYS
    }
    projected["legacy_maxfiles"] = None
    projected["source"] = "NOT_EXPLICITLY_RETURNED"
    projected["unparsed_fields_present"] = False

    raw = job.get("prune-backups")
    if isinstance(raw, str) and raw.strip():
        projected["source"] = "PRUNE_BACKUPS"
        seen: set[str] = set()
        normalized = raw.replace(",", " ")
        for token in normalized.split():
            if "=" not in token:
                projected["unparsed_fields_present"] = True
                continue
            key, value = token.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key not in RETENTION_KEYS:
                projected["unparsed_fields_present"] = True
                continue
            seen.add(key)
            try:
                count = int(value)
            except ValueError:
                projected["unparsed_fields_present"] = True
                continue
            if count < 0:
                projected["unparsed_fields_present"] = True
                continue
            projected[key.replace("-", "_")] = count
        if not seen and not projected["unparsed_fields_present"]:
            projected["unparsed_fields_present"] = True
        return projected

    legacy = job.get("maxfiles")
    if isinstance(legacy, int) and not isinstance(legacy, bool) and legacy >= 0:
        projected["source"] = "LEGACY_MAXFILES"
        projected["legacy_maxfiles"] = legacy

    return projected


def _scope(job: dict[str, Any]) -> tuple[str, list[int], list[int]]:
    explicit = _parse_vmid_list(job.get("vmid"))
    excluded = _parse_vmid_list(job.get("exclude"))
    all_flag = _truthy(job.get("all"))

    if all_flag is True:
        return "ALL_GUESTS", explicit, excluded
    if explicit:
        return "EXPLICIT_VMIDS", explicit, excluded
    if isinstance(job.get("pool"), str) and job.get("pool"):
        return "POOL", explicit, excluded
    return "UNKNOWN", explicit, excluded


def _selected_declared_coverage(
    job: dict[str, Any],
    guest_index: dict[int, dict[str, Any]],
) -> tuple[str, list[int]]:
    scope, explicit, excluded = _scope(job)
    pool = job.get("pool")
    node = job.get("node")

    if isinstance(pool, str) and pool:
        return "UNKNOWN_POOL_MEMBERSHIP_NOT_OBSERVED", []

    if scope == "EXPLICIT_VMIDS":
        candidates = SELECTED_VMIDS.intersection(explicit)
    elif scope == "ALL_GUESTS":
        candidates = set(SELECTED_VMIDS)
    else:
        return "UNKNOWN_SCOPE", []

    candidates.difference_update(excluded)

    if isinstance(node, str) and node:
        candidates = {
            vmid
            for vmid in candidates
            if guest_index.get(vmid, {}).get("node") == node
        }

    return "DECLARED_SCOPE_OBSERVED", sorted(candidates)


def _safe_job_id(value: Any, index: int) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return f"UNIDENTIFIED_JOB_{index}"


def main() -> int:
    print("===== PVE BACKUP POLICY / RETENTION SOURCE DISCOVERY =====")

    try:
        getter, trust = build_getter_from_env(
            ENV_FILE,
            allow_discovery_credential=True,
            allow_insecure_tls_discovery=True,
        )
    except Exception as exc:
        print("credential_boundary: FAILED_TO_OBSERVE")
        print("error_class:", type(exc).__name__)
        print("No mutation was performed.")
        return 0

    print()
    print("===== PVE GUEST IDENTITY SCOPE =====")
    guest_status, guest_data, guest_error = getter(
        "/api2/json/cluster/resources",
        {"type": "vm"},
    )
    print("operation: GET /cluster/resources?type=vm")
    print("http_status:", guest_status if guest_status is not None else "NONE")
    print("runtime_credential_approved:", trust["runtime_credential_approved"])

    guest_index: dict[int, dict[str, Any]] = {}
    if guest_status == 200 and isinstance(guest_data, list):
        for item in guest_data:
            if not isinstance(item, dict):
                continue
            vmid = item.get("vmid")
            if isinstance(vmid, bool) or not isinstance(vmid, int):
                continue
            if vmid not in SELECTED_VMIDS:
                continue
            guest_index[vmid] = {
                "node": item.get("node") if isinstance(item.get("node"), str) else None,
                "type": item.get("type") if isinstance(item.get("type"), str) else None,
            }
        print("selected_vmids_expected:", len(SELECTED_VMIDS))
        print("selected_vmids_observed:", len(guest_index))
    else:
        print("guest_identity_status: FAILED_TO_OBSERVE")
        print("error_class:", guest_error or "UNKNOWN")

    print()
    print("===== PVE DECLARED BACKUP JOBS =====")
    status, data, error = getter("/api2/json/cluster/backup")
    print("operation: GET /cluster/backup")
    print("http_status:", status if status is not None else "NONE")

    if status != 200 or not isinstance(data, list):
        print("backup_job_source_status: FAILED_TO_OBSERVE")
        print("error_class:", error or "UNKNOWN")
        print()
        print("===== TRUST BOUNDARY =====")
        print("No backup job, retention policy, storage, or infrastructure state was changed.")
        print("No raw backup-job configuration, notes, hooks, mail targets, or credentials were printed.")
        print("No mutation was performed.")
        return 0

    print("backup_job_source_status: COMPLETE")
    print("declared_jobs:", len(data))

    counters = Counter()
    selected_job_coverage: dict[int, list[str]] = {vmid: [] for vmid in SELECTED_VMIDS}

    for index, raw_job in enumerate(data, start=1):
        if not isinstance(raw_job, dict):
            counters["malformed"] += 1
            continue

        job_id = _safe_job_id(raw_job.get("id"), index)
        enabled = _truthy(raw_job.get("enabled"))
        scope, explicit_vmids, excluded_vmids = _scope(raw_job)
        coverage_status, covered = _selected_declared_coverage(raw_job, guest_index)
        retention = _safe_retention(raw_job)

        if enabled is True:
            counters["enabled_true"] += 1
        elif enabled is False:
            counters["enabled_false"] += 1
        else:
            counters["enabled_not_explicit"] += 1

        counters[f"scope_{scope}"] += 1
        counters[f"retention_{retention['source']}"] += 1

        if coverage_status == "DECLARED_SCOPE_OBSERVED":
            counters["selected_coverage_observed_jobs"] += 1
            if enabled is not False:
                for vmid in covered:
                    selected_job_coverage[vmid].append(job_id)

        schedule = raw_job.get("schedule")
        schedule_text = schedule if isinstance(schedule, str) and schedule else "NOT_EXPLICITLY_RETURNED"
        storage = raw_job.get("storage")
        storage_text = storage if isinstance(storage, str) and storage else "NOT_EXPLICITLY_RETURNED"
        node = raw_job.get("node")
        node_text = node if isinstance(node, str) and node else "NOT_EXPLICITLY_RETURNED"
        mode = raw_job.get("mode")
        mode_text = mode if isinstance(mode, str) and mode else "NOT_EXPLICITLY_RETURNED"
        compress = raw_job.get("compress")
        compress_text = compress if isinstance(compress, str) and compress else "NOT_EXPLICITLY_RETURNED"

        retention_parts = []
        for key in RETENTION_KEYS:
            value = retention[key.replace("-", "_")]
            if value is not None:
                retention_parts.append(f"{key}={value}")
        if retention["legacy_maxfiles"] is not None:
            retention_parts.append(f"maxfiles={retention['legacy_maxfiles']}")
        retention_text = ",".join(retention_parts) if retention_parts else "NONE_EXPLICITLY_PARSED"

        enabled_text = (
            "TRUE" if enabled is True else "FALSE" if enabled is False else "NOT_EXPLICITLY_RETURNED"
        )
        explicit_text = ",".join(str(vmid) for vmid in explicit_vmids) if explicit_vmids else "NONE"
        excluded_text = ",".join(str(vmid) for vmid in excluded_vmids) if excluded_vmids else "NONE"
        covered_text = ",".join(str(vmid) for vmid in covered) if covered else "NONE"

        print()
        print(f"job_id: {job_id}")
        print("enabled_explicit:", enabled_text)
        print("scope:", scope)
        print("explicit_vmids:", explicit_text)
        print("excluded_vmids:", excluded_text)
        print("node_restriction:", node_text)
        print("storage:", storage_text)
        print("schedule:", schedule_text)
        print("mode:", mode_text)
        print("compression:", compress_text)
        print("retention_source:", retention["source"])
        print("retention_safe_projection:", retention_text)
        print("retention_unparsed_fields_present:", retention["unparsed_fields_present"])
        print("selected_scope_coverage_status:", coverage_status)
        print("selected_scope_vmids:", covered_text)

    covered_selected = sorted(
        vmid for vmid, jobs in selected_job_coverage.items() if jobs
    )
    uncovered_selected = sorted(SELECTED_VMIDS.difference(covered_selected))

    print()
    print("===== SELECTED VM DECLARED POLICY COVERAGE =====")
    for vmid in sorted(SELECTED_VMIDS):
        jobs = selected_job_coverage[vmid]
        print(
            f"vmid={vmid} declared_enabled_or_unspecified_job_scope="
            + (",".join(jobs) if jobs else "NONE_OBSERVED")
        )

    print()
    print("===== SUMMARY =====")
    print("declared_jobs_total:", len(data))
    print("enabled_true:", counters["enabled_true"])
    print("enabled_false:", counters["enabled_false"])
    print("enabled_not_explicitly_returned:", counters["enabled_not_explicit"])
    print("scope_all_guests:", counters["scope_ALL_GUESTS"])
    print("scope_explicit_vmids:", counters["scope_EXPLICIT_VMIDS"])
    print("scope_pool:", counters["scope_POOL"])
    print("scope_unknown:", counters["scope_UNKNOWN"])
    print("retention_prune_backups:", counters["retention_PRUNE_BACKUPS"])
    print("retention_legacy_maxfiles:", counters["retention_LEGACY_MAXFILES"])
    print("retention_not_explicitly_returned:", counters["retention_NOT_EXPLICITLY_RETURNED"])
    print("selected_vmids_total:", len(SELECTED_VMIDS))
    print("selected_vmids_with_declared_job_scope:", len(covered_selected))
    print("selected_vmids_without_declared_job_scope_observed:", len(uncovered_selected))
    print("selected_vmids_without_declared_job_scope_list:", ",".join(map(str, uncovered_selected)) or "NONE")

    print()
    print("===== INTERPRETATION BOUNDARY =====")
    print("This source describes DECLARED PVE backup-job policy only.")
    print("A declared schedule or retention/prune setting does not prove that a backup ran successfully.")
    print("Declared retention is not retention effectiveness and does not prove the expected recovery points still exist.")
    print("Declared job scope is not a protection classification and is not restore verification.")
    print("No RPO or RTO result is inferred from schedule text or backup age.")

    print()
    print("===== TRUST BOUNDARY =====")
    print("Only GET/read-only PVE API calls were used.")
    print("No raw backup-job object was persisted or printed.")
    print("Free-form notes, hook scripts, mail targets, notification fields, credentials, and connection strings were not projected.")
    print("No backup job, retention policy, storage, schedule, or infrastructure state was changed.")
    print("No mutation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
