# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #87: 292b8da942f2445d7bdb061f5c778b6861b6cd6f
active branch: agent/m7-planning-preflight-operator-context
Milestone 7: ACTIVE
management host: mgmt-automation
broader infrastructure mutation authorized: false
```

## Accepted installed operator runtime

The existing five-minute collector produces the accepted cross-domain operator projection under `infra-assurance`.

```text
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
mutation_allowed: False
runtime identity: infra-assurance
prometheus_rule_context_integration < backup_assurance_foundation < operator_attention_backup < operator_attention_incident
runtime-integration suite: 445 passed in 2.87s
```

Last accepted installed evidence before this slice included:

```text
cluster_id: k3s-main
attention_now_total: 7
required_live_verification_total: 11
backup_assets_total: 37
backup_protection_unknown: 37
backup_restore_verification_unknown: 37
backup_unprotected_claims: 0
incident_candidates_total: 4
incident_active_candidates: 1
incident_suppressed_candidates: 3
incident_source_status: PARTIAL
```

Counts are observed evidence and may change; they are not hard runtime invariants.

## Existing planning architecture

Do not create a second pre-change pack implementation. Accepted planning artifacts already exist:

```text
docs/decisions/0004-task-scoped-planning-preflight.md
src/infra_assurance/planning_preflight.py
tests/test_planning_preflight.py
schemas/deployment-preflight.schema.json
```

The base preflight already separates facts, conflicts, inferences, unknowns, required live verification, a non-executable candidate plan, and post-change verification. It keeps `mutation_allowed=false`.

## Active slice — planning preflight operator context

Report:

```text
docs/reports/2026-08-30-m7-planning-preflight-operator-context.md
```

Prepared module:

```text
src/infra_assurance/planning_preflight_operator.py
```

Accepted behavior:

```text
base build_deployment_preflight preserved
accepted operator scope required
cluster mismatch fails closed
mutation_allowed=false required on both inputs
target-namespace attention/change/unknown context projected
PLATFORM or target-namespace incident candidates are task-relevant
unrelated namespace incident candidates are not promoted into task risk
ACTIVE overlapping candidate -> live verification, not incident/root-cause claim
SUPPRESSED != RESOLVED
backup UNKNOWN != UNPROTECTED
stateful post-change plan requires authoritative backup/recovery evidence before stronger protection claims
one deterministic safest_next_action emitted, always mutation_allowed=false
```

Safest-next-action precedence:

```text
unknown/stale/failed/mismatched base evidence
> observed current-state conflict
> overlapping ACTIVE incident candidate
> relevant target-scope operator attention
> existing required live verification
> review non-executable candidate plan
```

## Focused validation — ACCEPTED

```text
7 passed in 0.08s
7 passed in 0.04s
```

## Safe no-write probe — ACCEPTED

Probe:

```text
scripts/discovery/m7_planning_preflight_operator_probe.py
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

Observed task context:

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

The one task-relevant candidate was `ACTIVE`, platform scoped to `Platform/k3s-main`, with two alerts and two recommended checks. It is not a confirmed incident or root-cause conclusion.

Enriched preflight:

```text
required_live_verification_total: 7
post_change_verification_total: 7
additive pre-change code: VERIFY_ACTIVE_INCIDENT_CONTEXT_BEFORE_CHANGE
additive post-change codes: VERIFY_OPERATOR_ATTENTION_AFTER_CHANGE, VERIFY_BACKUP_PROTECTION_EVIDENCE_AFTER_CHANGE
safest_next_action: VERIFY_ACTIVE_INCIDENT_CONTEXT
live_verification_required: True
mutation_allowed: False
```

Trust accepted:

```text
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
backup_unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
```

No truncation was observed. The probe performed no live infrastructure query, wrote nothing, and modified no installed runtime.

## Exact intended branch scope

```text
HANDOFF.md
docs/reports/2026-08-30-m7-planning-preflight-operator-context.md
scripts/discovery/m7_planning_preflight_operator_probe.py
src/infra_assurance/planning_preflight_operator.py
tests/test_planning_preflight_operator.py
```

No systemd, timer, runtime deployment, Kubernetes RBAC, kubeconfig, datastore, permission, AI-provider, remediation, or infrastructure mutation change is included.

## Exact next gate — FULL REPOSITORY SUITE

On `mgmt-automation`, without `sudo`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-planning-preflight-operator-context
python3 -m pytest -q
```

If the full suite passes, record the exact result, compare the branch against accepted main `292b8da942f2445d7bdb061f5c778b6861b6cd6f`, require exactly the five intended files, create a non-draft PR, verify mergeability, and squash-merge. Do not deploy this module in this slice.

After merge, reassess M7 against the roadmap. If no acceptance gap remains, perform an explicit M7 closure/handoff slice that updates repository continuity/status documentation and the Project Source files so a new tab can begin M8 without relying on chat memory.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- DECLARED != OBSERVED;
- NONE_OBSERVED_IN_BOUNDED_SOURCE != universal absence;
- FAILED_TO_OBSERVE != negative evidence;
- UNKNOWN != false;
- incident candidates are not confirmed incidents or root-cause conclusions;
- suppressed incident candidates are not resolved by implication;
- backup UNKNOWN protection is not UNPROTECTED;
- restore verification UNKNOWN is not a recovery-test-overdue claim;
- derived projections do not replace source evidence;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the planning projection;
- no remediation or infrastructure mutation is implied;
- generated operational semantics keep `mutation_allowed=false`.
