from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

ADAPTER_VERSION = "0.1"
MAX_REQUIRED_VERIFICATIONS = 20


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(value, 0)
    return 0


def _compact_required_verification(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for asset in artifact.get("assets", []):
        if not isinstance(asset, dict):
            continue
        for item in asset.get("required_evidence", []):
            if not isinstance(item, dict):
                continue
            code = item.get("code") if isinstance(item.get("code"), str) else "BACKUP_VERIFICATION_REQUIRED"
            target = item.get("target") if isinstance(item.get("target"), str) else "UNKNOWN"
            check = item.get("check") if isinstance(item.get("check"), str) else "Authoritative backup evidence is required."
            key = (code, target, check)
            if key in seen:
                continue
            seen.add(key)
            result.append(
                {
                    "source": "backup_assurance",
                    "code": code,
                    "target": target,
                    "check": check,
                    "authoritative_source_required": bool(item.get("authoritative_source_required", True)),
                }
            )
            if len(result) >= MAX_REQUIRED_VERIFICATIONS:
                return result
    return result


def build_backup_operator_adapter(
    artifact: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Project compact operator-facing backup/recovery assurance gaps without overclaiming protection."""
    cluster_id = artifact.get("cluster_id")
    if not isinstance(cluster_id, str) or not cluster_id:
        raise ValueError("backup assurance artifact must identify a cluster")

    summary = artifact.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("backup assurance artifact must contain a summary object")

    source_status = artifact.get("source_status")
    if not isinstance(source_status, dict):
        raise ValueError("backup assurance artifact must contain source_status")

    overall_status = source_status.get("overall")
    if not isinstance(overall_status, str) or not overall_status:
        raise ValueError("backup assurance source_status must identify overall status")

    assets_total = _safe_int(summary.get("assets_total"))
    assets_stale = _safe_int(summary.get("assets_stale"))
    assets_freshness_unknown = _safe_int(summary.get("assets_freshness_unknown"))
    protection_unknown = _safe_int(summary.get("protection_unknown"))
    restore_verification_unknown = _safe_int(summary.get("restore_verification_unknown"))
    unprotected_claims = _safe_int(summary.get("unprotected_claims"))
    authoritative_sources = _safe_int(summary.get("authoritative_backup_sources_integrated"))

    attention: list[dict[str, Any]] = []
    if overall_status != "COMPLETE":
        attention.append(
            {
                "source": "backup_assurance",
                "code": "BACKUP_ASSURANCE_SOURCE_INCOMPLETE",
                "severity": "UNKNOWN",
                "statement": "Backup-assurance source coverage is incomplete; absence of protection findings is not negative evidence.",
            }
        )
    if assets_stale:
        attention.append(
            {
                "source": "backup_assurance",
                "code": "BACKUP_ASSET_EVIDENCE_STALE",
                "severity": "UNKNOWN",
                "count": assets_stale,
                "statement": "One or more backup-assurance asset observations are stale.",
            }
        )
    if assets_freshness_unknown:
        attention.append(
            {
                "source": "backup_assurance",
                "code": "BACKUP_ASSET_FRESHNESS_UNKNOWN",
                "severity": "UNKNOWN",
                "count": assets_freshness_unknown,
                "statement": "One or more backup-assurance asset freshness states are unknown.",
            }
        )
    if protection_unknown:
        attention.append(
            {
                "source": "backup_assurance",
                "code": "BACKUP_PROTECTION_UNKNOWN",
                "severity": "UNKNOWN",
                "count": protection_unknown,
                "statement": "Backup protection status is unknown for observed assets; UNKNOWN is not UNPROTECTED.",
            }
        )
    if restore_verification_unknown:
        attention.append(
            {
                "source": "backup_assurance",
                "code": "RESTORE_VERIFICATION_UNKNOWN",
                "severity": "UNKNOWN",
                "count": restore_verification_unknown,
                "statement": "Restore verification status is unknown for observed assets.",
            }
        )
    if authoritative_sources == 0:
        attention.append(
            {
                "source": "backup_assurance",
                "code": "AUTHORITATIVE_BACKUP_SOURCE_NOT_INTEGRATED",
                "severity": "UNKNOWN",
                "statement": "No authoritative backup-system source is integrated in the current backup-assurance artifact.",
            }
        )
    if unprotected_claims:
        attention.append(
            {
                "source": "backup_assurance",
                "code": "UNPROTECTED_CLAIMS_OBSERVED",
                "severity": "RISK",
                "count": unprotected_claims,
                "statement": "Authoritative backup-assurance evidence contains one or more unprotected claims.",
            }
        )

    required = _compact_required_verification(artifact)
    now = now or datetime.now(timezone.utc)
    return {
        "backup_operator_adapter_version": ADAPTER_VERSION,
        "generated_at": _rfc3339(now),
        "cluster_id": cluster_id,
        "mutation_allowed": False,
        "scope": "BACKUP_ASSURANCE_EXISTING_EVIDENCE_ONLY",
        "source_status": overall_status,
        "summary": {
            "assets_total": assets_total,
            "assets_stale": assets_stale,
            "assets_freshness_unknown": assets_freshness_unknown,
            "protection_unknown": protection_unknown,
            "restore_verification_unknown": restore_verification_unknown,
            "unprotected_claims": unprotected_claims,
            "authoritative_backup_sources_integrated": authoritative_sources,
            "attention_total": len(attention),
            "required_verification_categories_total": len(required),
        },
        "attention": attention,
        "required_live_verification": required,
        "source_artifacts": ["backup-assurance.json"],
        "trust": {
            "unknown_is_not_unprotected": True,
            "recovery_test_overdue_claimed": False,
            "authoritative_backup_evidence_required_for_unprotected": True,
        },
    }
