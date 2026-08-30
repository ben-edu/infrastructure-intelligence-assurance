# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #85: 1898072ef33a554dc1d4d86d82aa9030fd17b019
active branch: agent/m7-incident-operator-integration-contract
Milestone 7: ACTIVE
management host: mgmt-automation
broader infrastructure mutation authorized: false
```

## Accepted installed operator baseline

Installed runtime remains unchanged in this slice:

```text
runtime identity: infra-assurance
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
prometheus_rule_context_integration < backup_assurance_foundation < operator_attention_backup
final suite at accepted runtime integration: 429 passed in 2.15s
```

Accepted operator evidence:

```text
cluster_id: k3s-main
attention_now_total: 5
required_live_verification_total: 8
backup_assets_total: 37
backup_protection_unknown: 37
backup_restore_verification_unknown: 37
backup_unprotected_claims: 0
```

Preserve:

```text
UNKNOWN protection != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
```

## Accepted incident operator adapter

Accepted main after PR #85 includes the compact read-only incident adapter.

Accepted validation:

```text
focused tests: 6 passed in 0.05s; repeat 6 passed in 0.04s
live read-only probe: source_status=COMPLETE
incident_source_status=PARTIAL
full suite: 435 passed in 2.24s
```

Accepted current incident evidence:

```text
incident_candidates: 4
active_candidates: 4
suppressed_candidates: 0
unknown_candidates: 0
candidates_with_related_warning_events: 1
attention_total: 2
required_verification_categories_total: 6
candidate_groups_truncated: False
required_live_verification_truncated: False
```

Trust semantics:

```text
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
```

The exact incomplete incident source domain was not printed by the allowlisted adapter probe and must not be guessed.

## Active slice — incident operator integration contract

Report:

```text
docs/reports/2026-08-30-m7-incident-operator-integration-contract.md
```

Goal:

```text
Combine the accepted Kubernetes+backup operator-attention artifact with the accepted compact incident-candidate projection into one operator-facing contract without changing the installed runtime yet.
```

Exact intended branch scope:

```text
HANDOFF.md
docs/reports/2026-08-30-m7-incident-operator-integration-contract.md
scripts/discovery/m7_incident_operator_integration_probe.py
src/infra_assurance/operator_attention_incident.py
tests/test_operator_attention_incident.py
```

Inputs:

```text
/var/lib/infra-assurance/evidence/operator-attention.json
/var/lib/infra-assurance/evidence/incident-candidates.json
```

Required accepted input scope:

```text
KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
```

Integrated scope:

```text
KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

## Initial focused gate — FAILED AND PRESERVED

```text
1 failed, 5 passed, 1 warning in 0.10s
```

Failure:

```text
test_combined_totals_survive_projection_truncation
expected required_live_verification_total: 11
observed: 10
```

Root cause: final `max_items=2` was incorrectly reused as the incident-adapter verification cap, truncating three incident verification entries to two before calculating the combined total. This was an implementation bug; the test was not weakened.

## Corrective focused gate — ACCEPTED

Corrected fixture semantics:

```text
existing required verification total: 8
incident verification entries before final projection truncation: 3
combined required_live_verification_total: 11
final projected list at max_items=2: 2
required_live_verification_truncated: True
```

Corrective focused result:

```text
6 passed in 0.06s
```

The regex warning was also removed with a raw regex string. No assertion was weakened or removed.

## Safe no-write integration probe — ACCEPTED

The probe read only the protected current `operator-attention.json` and `incident-candidates.json`, performed no live infrastructure query, and wrote nothing.

Safety:

```text
mutation_allowed: False
live_infrastructure_query_performed: False
source_artifacts_written: False
systemd_modified: False
installed_runtime_modified: False
candidate_promoted_to_confirmed_incident: False
root_cause_claimed: False
```

Integrated contract:

```text
source_status: COMPLETE
cluster_id: k3s-main
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
mutation_allowed: False
incident_source_status: PARTIAL
source_artifacts: inventory.json,context.json,change-context.json,backup-assurance.json,incident-candidates.json
```

Current combined summary:

```text
workloads_total: 68
workloads_with_attention: 3
attention_now_total: 7
recent_changes_total: 0
unknowns_total: 0
required_live_verification_total: 14
backup_assets_total: 37
backup_protection_unknown: 37
backup_restore_verification_unknown: 37
backup_unprotected_claims: 0
incident_candidates_total: 4
incident_active_candidates: 4
incident_suppressed_candidates: 0
incident_unknown_candidates: 0
incident_candidates_with_related_warning_events: 1
incident_candidates_requiring_live_verification: 4
```

Incident attention added:

```text
INCIDENT_SOURCE_INCOMPLETE / UNKNOWN / count=1
ACTIVE_INCIDENT_CANDIDATES / SIGNAL / count=4
```

Current incident groups:

```text
Namespace/keycloak / ACTIVE / alerts=2 / events=0 / checks=1
Namespace/monitoring / ACTIVE / alerts=5 / events=0 / checks=1
Namespace/moodle / ACTIVE / alerts=2 / events=1 / checks=2
Platform/k3s-main / ACTIVE / alerts=2 / events=0 / checks=2
```

Incident live-verification entries:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_RELATED_EVENT_OBJECT_STATE -> KUBERNETES_OBJECT
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PROMETHEUS_RULE_INPUTS -> PROMETHEUS_RULE_INPUTS
```

The combined total of 14 is the accepted existing operator total of 8 plus six current incident verification entries. Repeated alert-condition checks are candidate-scoped, not proof of completed verification.

Trust/truncation:

```text
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
attention_now_truncated: False
required_live_verification_truncated: False
incident_candidates_truncated: False
```

The incident source remains PARTIAL. Four active candidate groupings are observed, but they are not confirmed incidents or root-cause conclusions, and the current set is not a universal absence statement about other possible incidents or signals.

## Mutation boundary

This slice remains repository-only plus a safe read-only in-memory probe. It does NOT change systemd, installed `/opt` runtime, collector service/timer, Kubernetes RBAC/kubeconfig, filesystem permissions, datastores, or infrastructure. No deployment authorization is requested or implied.

## Exact next gate — FULL REPOSITORY SUITE

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-incident-operator-integration-contract
python3 -m pytest -q
```

Do not use strict interactive shell mode.

If the full suite passes:

1. record exact pass count/time;
2. verify exact five-file branch scope and no temporary/debug files;
3. create/inspect a non-draft PR;
4. verify changed filenames and mergeability;
5. squash-merge and carry the new accepted main SHA forward.

Do not deploy or replace installed operator attention in this slice.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- infrastructure observation remains read-only except separately authorized bounded management-host deployments already accepted;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- incident candidates are not confirmed incidents;
- incident candidates are not root-cause conclusions;
- suppressed alerts/candidates are not treated as resolved conditions;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied;
- generated operational semantics keep `mutation_allowed=false`.
