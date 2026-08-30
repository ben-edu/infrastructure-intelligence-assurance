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

Installed runtime remains:

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

The exact incomplete incident source domain was not printed by the allowlisted probe and must not be guessed.

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

Prepared integrated scope:

```text
KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

The integration fails closed on cluster mismatch, unaccepted operator scope, or `mutation_allowed != false`. It appends compact incident attention/live-verification entries while preserving accepted Kubernetes and backup evidence/trust fields.

Raw alert/Event payloads, related workload details, field-level change/drift details, rationales, logs, secrets, raw Terraform state, and raw Kubernetes Secret values are not projected.

## Initial focused gate — FAILED AND PRESERVED

Executed on `mgmt-automation`:

```text
1 failed, 5 passed, 1 warning in 0.10s
```

Failure:

```text
test_combined_totals_survive_projection_truncation
expected required_live_verification_total: 11
observed: 10
```

This was a real implementation bug, not a stale test. Final `max_items=2` was incorrectly reused as the incident-adapter verification cap, so three incident verification entries were truncated to two before calculating the combined total.

The expected total of 11 remains authoritative for the fixture.

## Corrective change — PREPARED

Corrected behavior:

```text
existing required verification total: 8
incident verification entries before final projection truncation: 3
combined total: 11
final projected list at max_items=2: 2
required_live_verification_truncated: True
```

The integration no longer passes final `max_items` into the incident adapter verification bound. Final projection truncation and total-count semantics are separated, consistent with the accepted Kubernetes+backup integration pattern.

The regex deprecation warning was also fixed using a raw regex string; no test assertion was weakened or removed.

## Mutation boundary

This slice remains repository-only plus a later read-only in-memory probe. It does NOT change:

```text
systemd
installed /opt runtime
collector service/timer
Kubernetes RBAC/kubeconfig
filesystem permissions
datastores
infrastructure
```

No deployment authorization is requested or implied.

## Exact next gate — CORRECTIVE FOCUSED TESTS

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-incident-operator-integration-contract
python3 -m pytest -q tests/test_operator_attention_incident.py
```

Do not use strict interactive shell mode.

If this passes, run only the safe no-write integration probe. Do not deploy or replace the installed operator-attention runtime in this slice.

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
