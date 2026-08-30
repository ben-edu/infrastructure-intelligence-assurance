from __future__ import annotations

import json
from pathlib import Path

from infra_assurance.incident_operator_adapter import build_incident_operator_adapter
from infra_assurance.operator_attention import load_json_artifact

SOURCE = Path("/var/lib/infra-assurance/evidence/incident-candidates.json")
MAX_PRINTED = 12


def _safe(value: object) -> str:
    if value is None:
        return "-"
    return str(value).replace("\n", " ")[:180]


def main() -> int:
    print("===== M7 INCIDENT OPERATOR ADAPTER PROBE =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("live_infrastructure_query_performed: False")
    print("source_artifact_written: False")
    print("raw_alert_details_projected: False")
    print("raw_event_details_projected: False")
    print("candidate_promoted_to_confirmed_incident: False")
    print("root_cause_claimed: False")

    try:
        artifact = load_json_artifact(SOURCE)
        projection = build_incident_operator_adapter(artifact)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print()
        print("===== SOURCE STATUS =====")
        print("source_status: FAILED_TO_OBSERVE")
        print("failure_category:", type(exc).__name__)
        print("No incident operator conclusion is allowed from this failed observation.")
        return 2

    summary = projection["summary"]
    print()
    print("===== SOURCE STATUS =====")
    print("source_status: COMPLETE")
    print("incident_source_status:", projection["source_status"])
    print("cluster_id:", projection["cluster_id"])
    print("scope:", projection["scope"])

    print()
    print("===== COMPACT INCIDENT SUMMARY =====")
    for key in (
        "incident_candidates",
        "active_candidates",
        "suppressed_candidates",
        "unknown_candidates",
        "candidates_with_related_warning_events",
        "candidates_with_exact_recent_change",
        "candidates_with_exact_drift",
        "candidates_requiring_live_verification",
        "attention_total",
        "required_verification_categories_total",
        "projected_candidates",
    ):
        print(f"{key}:", summary[key])

    print()
    print("===== ATTENTION =====")
    if projection["attention"]:
        for index, item in enumerate(projection["attention"][:MAX_PRINTED], start=1):
            print(
                f"item={index} code={_safe(item.get('code'))} severity={_safe(item.get('severity'))} "
                f"count={_safe(item.get('count'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== CANDIDATE GROUPS =====")
    if projection["candidates"]:
        for index, item in enumerate(projection["candidates"][:MAX_PRINTED], start=1):
            scope = item.get("scope") or {}
            print(
                f"item={index} state={_safe(item.get('state'))} "
                f"scope_type={_safe(scope.get('type'))} subject={_safe(scope.get('subject'))} "
                f"alerts={_safe(item.get('alert_count'))} events={_safe(item.get('related_warning_events_count'))} "
                f"changes={_safe(item.get('recent_changes_count'))} drift={_safe(item.get('drift_attention_count'))} "
                f"checks={_safe(item.get('recommended_checks_count'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== REQUIRED LIVE VERIFICATION =====")
    if projection["required_live_verification"]:
        for index, item in enumerate(projection["required_live_verification"][:MAX_PRINTED], start=1):
            print(
                f"item={index} code={_safe(item.get('code'))} target={_safe(item.get('target'))} "
                f"live_verification_required={_safe(item.get('live_verification_required'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== TRUST BOUNDARY =====")
    for key, value in projection["trust"].items():
        print(f"{key}:", value)
    print("candidate_groups_truncated:", projection["truncation"]["candidates_truncated"])
    print(
        "required_live_verification_truncated:",
        projection["truncation"]["required_live_verification_truncated"],
    )
    print("Only compact candidate metadata and deduplicated verification categories are projected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
