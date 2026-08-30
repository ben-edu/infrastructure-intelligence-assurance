# Milestone 7 — Planning Preflight Operator Context

Date: 2026-08-30
Status: SAFE PROBE ACCEPTED / FULL SUITE PENDING
Mode: repository-only integration over existing evidence; no live infrastructure query or runtime deployment

## Goal

Enrich the already-accepted task-scoped Kubernetes deployment planning preflight with the accepted cross-domain operator-attention artifact so current observability, backup-assurance, and incident-candidate context can influence pre-change verification and the safest next action.

This slice does not create a second pre-change architecture. It wraps the accepted `planning_preflight.py` contract and preserves its existing evidence/conflict/unknown/readiness/candidate-plan/post-change semantics.

## Accepted baseline

Accepted main checkpoint:

```text
292b8da942f2445d7bdb061f5c778b6861b6cd6f
```

Accepted installed operator scope:

```text
KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

Existing planning contract:

```text
src/infra_assurance/planning_preflight.py
docs/decisions/0004-task-scoped-planning-preflight.md
```

The base preflight remains non-executable and keeps `mutation_allowed: False`.

## Prepared integration

New module:

```text
src/infra_assurance/planning_preflight_operator.py
```

The adapter:

- calls the existing `build_deployment_preflight` implementation;
- requires matching cluster identity;
- requires the accepted Kubernetes+backup+incident operator scope;
- fails closed if either input violates `mutation_allowed=false`;
- keeps incident candidates distinct from confirmed incidents and root causes;
- keeps `SUPPRESSED` distinct from `RESOLVED`;
- keeps backup UNKNOWN distinct from UNPROTECTED;
- projects only target-namespace or platform incident candidates into task context;
- ignores unrelated namespace incident candidates for task-scoped change risk;
- adds relevant target-namespace operator attention, recent changes, and unknowns;
- adds pre-change live verification for overlapping ACTIVE incident candidates and target-scope unknowns;
- adds post-change regeneration of operator attention;
- for stateful requests, requires authoritative backup/recovery evidence after the future change before describing the new state as protected or recoverable;
- adds one deterministic `safest_next_action` without executing it.

Safest-next-action precedence:

```text
1. unknown/stale/failed/mismatched base evidence
2. observed current-state conflict
3. ACTIVE incident candidate overlapping platform or target namespace
4. relevant target-namespace operator attention
5. existing required pre-change live verification
6. review the non-executable candidate plan
```

Every returned action retains `mutation_allowed: False`.

## Focused validation — ACCEPTED

Executed without `sudo` on `mgmt-automation`:

```text
7 passed in 0.08s
7 passed in 0.04s
```

## Safe protected-artifact probe — ACCEPTED

Executed with privilege scoped only to reading protected existing evidence artifacts. The probe performed no live infrastructure query, wrote no artifacts, and modified no installed runtime.

Observed safety:

```text
mutation_allowed: False
live_infrastructure_query_performed: False
source_artifacts_written: False
installed_runtime_modified: False
candidate_promoted_to_confirmed_incident: False
root_cause_claimed: False
suppressed_means_resolved: False
backup_unknown_promoted_to_unprotected: False
```

Observed contract:

```text
source_status: COMPLETE
cluster_id: k3s-main
target_namespace: validation
scope: KUBERNETES_DEPLOYMENT_PREFLIGHT_WITH_OPERATOR_CONTEXT
mutation_allowed: False
base_readiness: PLAN_WITH_LIVE_VERIFICATION
operator_source_scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
incident_source_status: PARTIAL
```

Observed operator context:

```text
attention_now_total: 7
recent_changes_total: 0
unknowns_total: 0
operator_required_live_verification_total: 11
relevant_attention: 1
relevant_recent_changes: 0
relevant_unknowns: 0
relevant_incident_candidates: 1
backup_assets_total: 37
backup_protection_unknown: 37
backup_restore_verification_unknown: 37
backup_unprotected_claims: 0
incident_candidates_total: 4
incident_active_candidates: 1
incident_suppressed_candidates: 3
```

The one task-relevant incident candidate was platform scoped:

```text
state=ACTIVE
scope_type=PLATFORM
subject=Platform/k3s-main
alerts=2
checks=2
```

The enriched preflight emitted seven required live-verification items. Six are existing base planning checks; the seventh is the accepted operator-context gate:

```text
VERIFY_ACTIVE_INCIDENT_CONTEXT_BEFORE_CHANGE
```

Observed post-change verification count: 7. The two additive checks are:

```text
VERIFY_OPERATOR_ATTENTION_AFTER_CHANGE
VERIFY_BACKUP_PROTECTION_EVIDENCE_AFTER_CHANGE
```

Observed safest next action:

```text
code: VERIFY_ACTIVE_INCIDENT_CONTEXT
live_verification_required: True
mutation_allowed: False
action: Verify the active incident-candidate condition for Platform/k3s-main is current and understood before approving the change.
```

Observed trust:

```text
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
backup_unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
```

Observed truncation:

```text
attention_now_truncated: False
recent_changes_truncated: False
unknowns_truncated: False
required_live_verification_truncated: False
incident_candidates_truncated: False
```

Interpretation: the operator context changes planning priority, but it does not convert a candidate into a confirmed incident/root cause, does not treat suppressed candidates as resolved, does not convert backup UNKNOWN into UNPROTECTED, and does not authorize mutation.

## Intended branch scope

```text
HANDOFF.md
docs/reports/2026-08-30-m7-planning-preflight-operator-context.md
scripts/discovery/m7_planning_preflight_operator_probe.py
src/infra_assurance/planning_preflight_operator.py
tests/test_planning_preflight_operator.py
```

No systemd, timer, RBAC, kubeconfig, filesystem-permission, datastore, runtime deployment, remediation, or AI-provider change is included.

## Exact next gate

Run the full repository suite without `sudo`:

```bash
python3 -m pytest -q
```

If it passes, mark this slice merge-ready, verify exact five-file scope, create a non-draft PR, verify mergeability, and squash-merge. Do not deploy this module in this slice.
