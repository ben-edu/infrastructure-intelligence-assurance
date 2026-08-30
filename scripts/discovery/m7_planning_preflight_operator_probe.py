from __future__ import annotations

import json
from pathlib import Path

from infra_assurance.operator_attention import load_json_artifact
from infra_assurance.planning_preflight_operator import build_deployment_preflight_with_operator_context

EVIDENCE = Path("/var/lib/infra-assurance/evidence/kubernetes.json")
CONTEXT = Path("/var/lib/infra-assurance/evidence/context.json")
TOPOLOGY = Path("/var/lib/infra-assurance/evidence/topology.json")
OPERATOR = Path("/var/lib/infra-assurance/evidence/operator-attention.json")
REQUEST = Path("examples/requests/hypothetical-app-deployment.json")


def main() -> int:
    print("===== M7 PLANNING PREFLIGHT OPERATOR CONTEXT PROBE =====")
    print()
    print("===== SAFETY =====")
    print("mutation_allowed: False")
    print("live_infrastructure_query_performed: False")
    print("source_artifacts_written: False")
    print("installed_runtime_modified: False")
    print("candidate_promoted_to_confirmed_incident: False")
    print("root_cause_claimed: False")
    print("suppressed_means_resolved: False")
    print("backup_unknown_promoted_to_unprotected: False")

    try:
        request = json.loads(REQUEST.read_text(encoding="utf-8"))
        result = build_deployment_preflight_with_operator_context(
            load_json_artifact(EVIDENCE),
            load_json_artifact(CONTEXT),
            load_json_artifact(TOPOLOGY),
            load_json_artifact(OPERATOR),
            request,
        )
    except Exception as exc:  # bounded probe: print category only
        print()
        print("===== SOURCE STATUS =====")
        print("source_status: FAILED_TO_OBSERVE")
        print(f"failure_category: {type(exc).__name__}")
        print("integrated_preflight_conclusion_allowed: False")
        return 2

    operator = result["operator_context"]
    summary = operator["summary"]
    trust = operator["trust"]
    action = result["safest_next_action"]

    print()
    print("===== CONTRACT =====")
    print("source_status: COMPLETE")
    print("cluster_id:", result["cluster_id"])
    print("target_namespace:", result["request"]["namespace"])
    print("scope:", result["scope"])
    print("mutation_allowed:", result["mutation_allowed"])
    print("base_readiness:", result["readiness"])
    print("operator_source_scope:", operator["source_scope"])
    print("incident_source_status:", operator["incident_source_status"])

    print()
    print("===== OPERATOR CONTEXT =====")
    print("attention_now_total:", summary["attention_now_total"])
    print("recent_changes_total:", summary["recent_changes_total"])
    print("unknowns_total:", summary["unknowns_total"])
    print("operator_required_live_verification_total:", summary["required_live_verification_total"])
    print("relevant_attention:", len(operator["relevant_attention"]))
    print("relevant_recent_changes:", len(operator["relevant_recent_changes"]))
    print("relevant_unknowns:", len(operator["relevant_unknowns"]))
    print("relevant_incident_candidates:", len(operator["relevant_incident_candidates"]))
    print("backup_assets_total:", summary["backup_assets_total"])
    print("backup_protection_unknown:", summary["backup_protection_unknown"])
    print("backup_restore_verification_unknown:", summary["backup_restore_verification_unknown"])
    print("backup_unprotected_claims:", summary["backup_unprotected_claims"])
    print("incident_candidates_total:", summary["incident_candidates_total"])
    print("incident_active_candidates:", summary["incident_active_candidates"])
    print("incident_suppressed_candidates:", summary["incident_suppressed_candidates"])

    print()
    print("===== RELEVANT INCIDENT CANDIDATES =====")
    candidates = operator["relevant_incident_candidates"]
    if not candidates:
        print("none")
    for index, item in enumerate(candidates, start=1):
        print(
            f"item={index} state={item['state']} scope_type={item['scope_type']} "
            f"subject={item['subject']} alerts={item['alert_count']} checks={item['recommended_checks_count']}"
        )

    print()
    print("===== PREFLIGHT VERIFICATION =====")
    print("required_live_verification_total:", len(result["required_live_verification"]))
    for index, item in enumerate(result["required_live_verification"], start=1):
        print(f"item={index} code={item.get('code')} check={item.get('check')}")

    print()
    print("===== POST-CHANGE VERIFICATION =====")
    print("post_change_verification_total:", len(result["post_change_verification"]))
    for index, item in enumerate(result["post_change_verification"], start=1):
        print(f"item={index} code={item.get('code')}")

    print()
    print("===== SAFEST NEXT ACTION =====")
    print("code:", action["code"])
    print("live_verification_required:", action["live_verification_required"])
    print("mutation_allowed:", action["mutation_allowed"])
    print("action:", action["action"])

    print()
    print("===== TRUST =====")
    print("candidate_is_confirmed_incident:", trust["candidate_is_confirmed_incident"])
    print("candidate_is_root_cause:", trust["candidate_is_root_cause"])
    print("suppressed_means_resolved:", trust["suppressed_means_resolved"])
    print("live_verification_required_before_action:", trust["live_verification_required_before_action"])
    print("backup_unknown_is_not_unprotected:", trust["backup_unknown_is_not_unprotected"])
    print("recovery_test_overdue_claimed:", trust["recovery_test_overdue_claimed"])

    truncation = operator["truncation"]
    print()
    print("===== TRUNCATION =====")
    print("attention_now_truncated:", truncation.get("attention_now_truncated"))
    print("recent_changes_truncated:", truncation.get("recent_changes_truncated"))
    print("unknowns_truncated:", truncation.get("unknowns_truncated"))
    print("required_live_verification_truncated:", truncation.get("required_live_verification_truncated"))
    print("incident_candidates_truncated:", truncation.get("incident_candidates_truncated"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
