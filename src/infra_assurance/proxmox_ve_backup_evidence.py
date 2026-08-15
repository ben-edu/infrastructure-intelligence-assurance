from __future__ import annotations

import argparse
import json
import re
import ssl
import stat
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

from .io_utils import atomic_write_json, atomic_write_text

PVE_BACKUP_EVIDENCE_VERSION = "0.1"
DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_STORAGE_IDS = ("local",)
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")
GetJSON = Callable[[str, dict[str, str] | None], tuple[int | None, Any, str | None]]


def _rfc3339_from_epoch(value: Any) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError, ValueError):
        return None


def _rfc3339_now(now: datetime | None = None) -> str:
    value = now or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_id(value: Any, *, fallback: str = "") -> str:
    if not isinstance(value, str):
        return fallback
    value = value.strip()
    if not _SAFE_ID.fullmatch(value):
        return fallback
    return value


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _parse_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        result[key] = value
    return result


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError("invalid boolean configuration")


def _credential_mode_secure(path: Path) -> bool:
    mode = stat.S_IMODE(path.stat().st_mode)
    return (mode & 0o077) == 0


def build_getter_from_env(
    path: Path,
    *,
    allow_discovery_credential: bool = False,
    allow_insecure_tls_discovery: bool = False,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[GetJSON, dict[str, Any]]:
    values = _parse_env(path)
    required = ("PROXMOX_BASE_URL", "PROXMOX_TOKEN_ID", "PROXMOX_TOKEN_SECRET")
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise ValueError(f"missing required Proxmox variables: {','.join(missing)}")

    mode_secure = _credential_mode_secure(path)
    if not mode_secure and not allow_discovery_credential:
        raise PermissionError("credential file is group/world accessible; runtime use is refused")

    parsed = urlparse(values["PROXMOX_BASE_URL"])
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Proxmox base URL must be HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("embedded URL credentials are not allowed")

    verify_tls = _parse_bool(values.get("PROXMOX_VERIFY_TLS"), default=True)
    if not verify_tls and not allow_insecure_tls_discovery:
        raise ssl.SSLError("TLS verification is disabled; runtime use is refused")

    if verify_tls:
        context = ssl.create_default_context(cafile=values.get("PROXMOX_CA_BUNDLE") or None)
    else:
        context = ssl._create_unverified_context()

    origin = f"{parsed.scheme}://{parsed.netloc}"
    authorization = "PVEAPIToken=" + values["PROXMOX_TOKEN_ID"] + "=" + values["PROXMOX_TOKEN_SECRET"]
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=context))

    def get_json(api_path: str, params: dict[str, str] | None = None) -> tuple[int | None, Any, str | None]:
        path_with_query = api_path
        if params:
            path_with_query += "?" + urlencode(params)
        request = Request(
            origin + path_with_query,
            headers={"Authorization": authorization, "Accept": "application/json"},
            method="GET",
        )
        try:
            with opener.open(request, timeout=timeout_seconds) as response:
                payload = json.loads(response.read())
                return response.status, payload.get("data"), None
        except HTTPError as exc:
            return exc.code, None, "HTTP_ERROR"
        except URLError as exc:
            return None, None, type(exc.reason).__name__
        except Exception as exc:
            return None, None, type(exc).__name__

    return get_json, {
        "credential_file_mode_secure": mode_secure,
        "tls_verification": verify_tls,
        "runtime_credential_approved": False,
        "discovery_override_used": bool(allow_discovery_credential or allow_insecure_tls_discovery),
    }


def _observation(*, operation: str, status_code: int | None, error_class: str | None) -> dict[str, Any]:
    return {
        "operation": operation,
        "status": "COMPLETE" if status_code == 200 else "FAILED_TO_OBSERVE",
        "http_status": status_code,
        "error_class": error_class,
    }


def _normalize_nodes(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        node = _safe_id(item.get("node"))
        if node:
            result.append({"node": node, "status": _safe_id(item.get("status"), fallback="UNKNOWN").upper()})
    return sorted(result, key=lambda item: item["node"])


def _normalize_guests(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        vmid = _safe_int(item.get("vmid"))
        if vmid is None:
            continue
        result.append(
            {
                "vmid": vmid,
                "guest_type": _safe_id(item.get("type"), fallback="UNKNOWN").upper(),
                "status": _safe_id(item.get("status"), fallback="UNKNOWN").upper(),
                "node": _safe_id(item.get("node"), fallback="UNKNOWN"),
            }
        )
    return sorted(result, key=lambda item: item["vmid"])


def _normalize_storage_config(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        storage_id = _safe_id(item.get("storage"))
        storage_type = _safe_id(item.get("type"))
        if not storage_id or not storage_type:
            continue
        raw_content = item.get("content")
        content_types = []
        if isinstance(raw_content, str):
            content_types = sorted(
                {part.strip() for part in raw_content.split(",") if _SAFE_ID.fullmatch(part.strip())}
            )
        retention = item.get("prune-backups")
        if not isinstance(retention, str) or len(retention) > 200:
            retention = None
        result.append(
            {
                "storage_id": storage_id,
                "storage_type": storage_type,
                "backup_content_enabled": "backup" in content_types,
                "disabled": bool(item.get("disable", 0)),
                "retention_policy": retention,
                "pbs_backend": storage_type == "pbs",
            }
        )
    return sorted(result, key=lambda item: item["storage_id"])


def _count_vmid_text(value: Any) -> int:
    if not isinstance(value, str):
        return 0
    return len([part for part in re.split(r"[,;\s]+", value.strip()) if part])


def _normalize_jobs(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        job_id = _safe_id(item.get("id"))
        if not job_id:
            continue
        schedule = item.get("schedule")
        if not isinstance(schedule, str) or len(schedule) > 200:
            schedule = None
        result.append(
            {
                "job_id": job_id,
                "enabled": bool(item.get("enabled")) if "enabled" in item else not bool(item.get("disable", 0)),
                "schedule": schedule,
                "storage_id": _safe_id(item.get("storage"), fallback="UNKNOWN"),
                "mode": _safe_id(item.get("mode"), fallback="UNKNOWN").upper(),
                "node": _safe_id(item.get("node"), fallback="ALL"),
                "selection": "ALL_GUESTS" if bool(item.get("all")) else "BOUNDED_SELECTION",
                "selected_vmid_count": _count_vmid_text(item.get("vmid")),
                "excluded_vmid_count": _count_vmid_text(item.get("exclude")),
            }
        )
    return sorted(result, key=lambda item: item["job_id"])


def _normalize_recovery_points(
    data: Any,
    *,
    source_id: str,
    node: str,
    storage_id: str,
) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    result = []
    seen = set()
    for item in data:
        if not isinstance(item, dict) or item.get("content") != "backup":
            continue
        vmid = _safe_int(item.get("vmid"))
        created_at = _rfc3339_from_epoch(item.get("ctime"))
        format_name = _safe_id(item.get("format"), fallback="UNKNOWN")
        size_bytes = _safe_int(item.get("size"))
        if vmid is None or created_at is None:
            continue
        stable_key = (source_id, node, storage_id, vmid, created_at, format_name, size_bytes)
        if stable_key in seen:
            continue
        seen.add(stable_key)
        result.append(
            {
                "recovery_point_id": "pve-rp-" + uuid.uuid5(
                    uuid.NAMESPACE_URL, ":".join(str(part) for part in stable_key)
                ).hex[:24],
                "vmid": vmid,
                "node": node,
                "storage_id": storage_id,
                "format": format_name,
                "created_at": created_at,
                "size_bytes": size_bytes,
                "archive_protection_flag": bool(item.get("protected", 0)),
                "basis": ["PVE_STORAGE_CONTENT_BACKUP_RECORD"],
            }
        )
    return sorted(result, key=lambda item: (item["vmid"], item["created_at"], item["recovery_point_id"]))


def _coverage(
    guests: list[dict[str, Any]],
    recovery_points: list[dict[str, Any]],
    *,
    content_scope_complete: bool,
    storage_id: str,
) -> list[dict[str, Any]]:
    by_vmid: dict[int, list[dict[str, Any]]] = {}
    for item in recovery_points:
        by_vmid.setdefault(item["vmid"], []).append(item)

    result = []
    for guest in guests:
        vmid = guest["vmid"]
        points = by_vmid.get(vmid, [])
        if points:
            status = "RECOVERY_POINT_OBSERVED"
            latest = max(item["created_at"] for item in points)
        elif content_scope_complete:
            status = "NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE"
            latest = None
        else:
            status = "UNKNOWN"
            latest = None
        result.append(
            {
                "vmid": vmid,
                "storage_id": storage_id,
                "local_recovery_point_status": status,
                "recovery_point_count": len(points),
                "latest_recovery_point_at": latest,
            }
        )
    return result


def build_proxmox_ve_backup_evidence(
    *,
    source_id: str,
    node: str,
    storage_ids: list[str],
    get_json: GetJSON,
    credential_metadata: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    source_id = _safe_id(source_id)
    node = _safe_id(node)
    safe_storage_ids = [_safe_id(item) for item in storage_ids]
    safe_storage_ids = [item for item in safe_storage_ids if item]
    if not source_id or not node or not safe_storage_ids:
        raise ValueError("source_id, node, and at least one safe storage ID are required")

    observations: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    def query(operation: str, path: str, params: dict[str, str] | None = None) -> Any:
        status_code, data, error_class = get_json(path, params)
        observation = _observation(operation=operation, status_code=status_code, error_class=error_class)
        observations.append(observation)
        if observation["status"] != "COMPLETE":
            errors.append(
                {
                    "code": "PVE_GET_FAILED",
                    "operation": operation,
                    "http_status": status_code,
                    "error_class": error_class,
                }
            )
        return data if observation["status"] == "COMPLETE" else None

    version_data = query("GET_VERSION", "/api2/json/version")
    nodes_data = query("GET_NODES", "/api2/json/nodes")
    guests_data = query("GET_GUEST_RESOURCES", "/api2/json/cluster/resources", {"type": "vm"})
    storage_data = query("GET_STORAGE_CONFIG", "/api2/json/storage")
    jobs_data = query("GET_CLUSTER_BACKUP_JOBS", "/api2/json/cluster/backup")

    version: dict[str, Any] = {}
    if isinstance(version_data, dict):
        for key in ("version", "release", "repoid"):
            value = version_data.get(key)
            if isinstance(value, (str, int, float, bool)):
                version[key] = value

    nodes = _normalize_nodes(nodes_data)
    guests = _normalize_guests(guests_data)
    storages = _normalize_storage_config(storage_data)
    jobs = _normalize_jobs(jobs_data)

    all_points: list[dict[str, Any]] = []
    coverage_records: list[dict[str, Any]] = []
    content_scopes: list[dict[str, Any]] = []

    for storage_id in safe_storage_ids:
        operation = f"GET_STORAGE_BACKUP_CONTENT:{storage_id}"
        data = query(
            operation,
            f"/api2/json/nodes/{node}/storage/{storage_id}/content",
            {"content": "backup"},
        )
        scope_complete = data is not None
        points = _normalize_recovery_points(data, source_id=source_id, node=node, storage_id=storage_id)
        all_points.extend(points)
        coverage_records.extend(
            _coverage(guests, points, content_scope_complete=scope_complete, storage_id=storage_id)
        )
        content_scopes.append(
            {
                "node": node,
                "storage_id": storage_id,
                "status": "COMPLETE" if scope_complete else "FAILED_TO_OBSERVE",
                "recovery_points_observed": len(points),
            }
        )

    if not observations or observations[0]["status"] != "COMPLETE":
        overall = "FAILED_TO_OBSERVE"
    elif all(item["status"] == "COMPLETE" for item in observations):
        overall = "COMPLETE"
    else:
        overall = "PARTIAL"

    coverage_counts = Counter(item["local_recovery_point_status"] for item in coverage_records)
    storage_backends = Counter(item["storage_type"] for item in storages)

    return {
        "proxmox_ve_backup_evidence_version": PVE_BACKUP_EVIDENCE_VERSION,
        "generated_at": _rfc3339_now(now),
        "mutation_allowed": False,
        "source": {
            "type": "proxmox_ve_api",
            "source_id": source_id,
            "node": node,
            "operation": "BOUNDED_HTTP_GET_BACKUP_EVIDENCE",
            "status": overall,
            "collector": "infra_assurance.proxmox_ve_backup_evidence",
            "collector_version": PVE_BACKUP_EVIDENCE_VERSION,
            "credential_runtime_approved": bool(credential_metadata.get("runtime_credential_approved", False)),
            "credential_file_mode_secure": bool(credential_metadata.get("credential_file_mode_secure", False)),
            "tls_verification": bool(credential_metadata.get("tls_verification", False)),
            "discovery_override_used": bool(credential_metadata.get("discovery_override_used", False)),
        },
        "pve_identity": version,
        "observations": observations,
        "nodes": nodes,
        "guests": guests,
        "storages": storages,
        "backup_jobs": jobs,
        "content_scopes": content_scopes,
        "recovery_points": all_points,
        "guest_storage_coverage": sorted(coverage_records, key=lambda item: (item["vmid"], item["storage_id"])),
        "summary": {
            "nodes_observed": len(nodes),
            "current_guests_observed": len(guests),
            "storages_observed": len(storages),
            "pbs_storages_configured": storage_backends["pbs"],
            "cluster_backup_jobs_observed": len(jobs),
            "recovery_points_observed": len(all_points),
            "guests_with_recovery_point_in_selected_scopes": len(
                {item["vmid"] for item in coverage_records if item["local_recovery_point_status"] == "RECOVERY_POINT_OBSERVED"}
            ),
            "guest_storage_scopes_without_recovery_point": coverage_counts[
                "NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE"
            ],
            "guest_storage_scopes_unknown": coverage_counts["UNKNOWN"],
        },
        "unknowns": [
            {
                "code": "RESTORE_VERIFICATION_NOT_OBSERVED",
                "statement": "Recovery-point artifact presence does not prove restore verification.",
            },
            {
                "code": "INTEGRITY_VERIFICATION_NOT_OBSERVED",
                "statement": "This adapter does not collect backup integrity verification evidence.",
            },
            {
                "code": "RPO_RTO_NOT_OBSERVED",
                "statement": "This adapter does not infer RPO or RTO targets/results from artifact timestamps.",
            },
            {
                "code": "SCHEDULED_PROTECTION_NOT_INFERRED",
                "statement": "Recovery-point artifacts are not interpreted as proof of a current scheduled protection mechanism.",
            },
        ],
        "errors": errors,
        "caveats": [
            "Proxmox archive protected=false is a source-native archive retention/protection flag and must never be mapped to platform assurance state UNPROTECTED.",
            "Complete empty storage-content scope proves only that no backup artifact was observed in that exact PVE node/storage scope.",
            "PVE-local evidence must not be projected onto BM1, external targets, or future PBS-native evidence.",
            "Raw volume IDs, raw API payloads, URLs, token material, guest names, storage server/path configuration, fingerprints, encryption-key references, and secret fields are not persisted.",
            "Future PBS support must remain a separate source adapter with explicit provenance behind the same common assurance dimensions.",
        ],
    }


def render_proxmox_ve_backup_evidence_markdown(artifact: dict[str, Any]) -> str:
    lines = [
        "# Proxmox VE Backup Evidence",
        "",
        f"Generated: `{artifact['generated_at']}`",
        f"Source: `{artifact['source']['source_id']}`",
        f"Node: `{artifact['source']['node']}`",
        f"Source status: `{artifact['source']['status']}`",
        f"Mutation allowed: `{str(artifact['mutation_allowed']).lower()}`",
        f"Runtime credential approved: `{str(artifact['source']['credential_runtime_approved']).lower()}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in artifact["summary"].items():
        lines.append(f"- {key}: {value}")

    lines += ["", "## Recovery point coverage", ""]
    if not artifact["guest_storage_coverage"]:
        lines.append("- No guest/storage coverage records were produced.")
    for item in artifact["guest_storage_coverage"]:
        lines.append(
            f"- VMID {item['vmid']} storage={item['storage_id']} "
            f"status={item['local_recovery_point_status']} "
            f"count={item['recovery_point_count']} "
            f"latest={item['latest_recovery_point_at'] or 'unknown'}"
        )

    lines += [
        "",
        "## Trust boundary",
        "",
        "Observed recovery-point artifacts are source evidence only. They do not establish restore verification, integrity verification, scheduled protection, RPO, or RTO.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect bounded read-only Proxmox VE backup evidence.")
    parser.add_argument("--credential-env-file", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--storage-id", action="append", dest="storage_ids")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path, required=True)
    parser.add_argument("--allow-discovery-credential", action="store_true")
    parser.add_argument("--allow-insecure-tls-discovery", action="store_true")
    args = parser.parse_args()

    getter, credential_metadata = build_getter_from_env(
        args.credential_env_file,
        allow_discovery_credential=args.allow_discovery_credential,
        allow_insecure_tls_discovery=args.allow_insecure_tls_discovery,
    )
    artifact = build_proxmox_ve_backup_evidence(
        source_id=args.source_id,
        node=args.node,
        storage_ids=args.storage_ids or list(DEFAULT_STORAGE_IDS),
        get_json=getter,
        credential_metadata=credential_metadata,
    )
    atomic_write_json(args.out, artifact)
    atomic_write_text(args.summary_out, render_proxmox_ve_backup_evidence_markdown(artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
