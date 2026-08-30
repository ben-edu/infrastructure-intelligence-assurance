from __future__ import annotations

import json
from pathlib import Path

from infra_assurance.operator_attention import load_json_artifact
from infra_assurance.operator_attention_incident import build_operator_attention_with_incidents

OPERATOR_SOURCE = Path("/var/lib/infra-assurance/evidence/operator-attention.json")
INCIDENT_SOURCE = Path("/var/lib/infra-assurance/evidence/incident-candidates.json")
MAX_PRINTED = 12


def _safe(value: object) -> str:
    if value is None:
        return "-"
    return str(value).replace("\n", " ")[:180]


def main() -> int:
    print("===== M7 INCIDENT OPERATOR INTEGRATION CONTRACT PROBE =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("live_infrastructure_query_performed: False")
    print("source_artifacts_written: False")
    print("systemd_modified: False")
    print("installed_runtime_modified: False")
    print("candidate_promoted_to_confirmed_incident: False")
    print("root_cause_claimed: False")

    try:
        operator = load_json_artifact(OPERATOR_SOURCE)
        incidents = load_json_artifact(INCIDENT_SOURCE)
        projection = build_operator_attention_with_incidents(operator, incidents)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print()
        print("===== SOURCE STATUS =====")
        print("source_status: FAILED_TO_OBSERVE")
        print("failure_category:", type(exc).__name__)
        print("No integrated operator conclusion is allowed from this failed observation.")
        return 2

    summary = projection["summary"]
    incident = projection["incident_candidates"]

    print()
    print("===== CONTRACT =====")
    print("source_status: COMPLETE")
    print("cluster_id:", projection["cluster_id"])
    print("scope:", projection["scope"])
    print("mutation_allowed:", projection["mutation_allowed"])
    print("incident_source_status:", incident["source_status"])
    print("source_artifacts:", ",".join(projection["source_artifacts"]))

    print()
    print("===== COMBINED SUMMARY =====")
    for key in (
        "workloads_total",
        "workloads_with_attention",
        "attention_now_total",
        "recent_changes_total",
        "unknowns_total",
        "required_live_verification_total",
        "backup_assets_total",
        "backup_protection_unknown",
        "backup_restore_verification_unknown",
        "backup_unprotected_claims",
        "incident_candidates_total",
        "incident_active_candidates",
        "incident_suppressed_candidates",
        "incident_unknown_candidates",
        "incident_candidates_with_related_warning_events",
        "incident_candidates_requiring_live_verification",
    ):
        print(f"{key}:", summary.get(key))

    print()
    print("===== INCIDENT ATTENTION =====")
    items = [item for item in projection["attention_now"] if item.get("source") == "incident_candidates"]
    if items:
        for index, item in enumerate(items[:MAX_PRINTED], start=1):
            print(
                f"item={index} code={_safe(item.get('code'))} severity={_safe(item.get('severity'))} "
                f"count={_safe(item.get('count'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== INCIDENT CANDIDATE GROUPS =====")
    candidates = incident.get("candidates", [])
    if candidates:
        for index, item in enumerate(candidates[:MAX_PRINTED], start=1):
            scope = item.get("scope", {})
            print(
                f"item={index} state={_safe(item.get('state'))} scope_type={_safe(scope.get('type'))} "
                f"subject={_safe(scope.get('subject'))} alerts={_safe(item.get('alert_count'))} "
                f"events={_safe(item.get('related_warning_events_count'))} checks={_safe(item.get('recommended_checks_count'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== INCIDENT REQUIRED LIVE VERIFICATION =====")
    required = [
        item
        for item in projection["required_live_verification"]
        if item.get("source") == "incident_candidates"
    ]
    if required:
        for index, item in enumerate(required[:MAX_PRINTED], start=1):
            print(
                f"item={index} code={_safe(item.get('code'))} target={_safe(item.get('target'))} "
                f"live_verification_required={_safe(item.get('live_verification_required'))}"
            )
    else:
        print("NONE_OBSERVED")

    print()
    print("===== TRUST =====")
    trust = incident["trust"]
    print("candidate_is_confirmed_incident:", trust["candidate_is_confirmed_incident"])
    print("candidate_is_root_cause:", trust["candidate_is_root_cause"])
    print("suppressed_means_resolved:", trust["suppressed_means_resolved"])
    print("live_verification_required_before_action:", trust["live_verification_required_before_action"])

    print()
    print("===== TRUNCATION =====")
    truncation = projection["truncation"]
    print("attention_now_truncated:", truncation["attention_now_truncated"])
    print("required_live_verification_truncated:", truncation["required_live_verification_truncated"])
    print("incident_candidates_truncated:", truncation["incident_candidates_truncated"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
