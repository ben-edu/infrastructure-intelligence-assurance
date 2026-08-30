# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #84: abd8fe56832f1868e09e1cd26afbbc40046d9965
active branch: agent/m7-incident-operator-adapter
Milestone 7: ACTIVE
management host: mgmt-automation
broader infrastructure mutation authorized: false
```

## Accepted cross-domain runtime baseline

Accepted report:

```text
docs/reports/2026-08-30-m7-cross-domain-runtime-integration.md
```

Installed runtime state:

```text
runtime identity: infra-assurance
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
prometheus_rule_context_integration < backup_assurance_foundation < operator_attention_backup
final suite: 429 passed in 2.15s
```

Current accepted operator evidence:

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

## Active slice — incident operator adapter

Report:

```text
docs/reports/2026-08-30-m7-incident-operator-adapter.md
```

Goal:

```text
Project existing incident-candidates.json into compact operator-facing evidence for grouped current signals without promoting candidates to confirmed incidents or root-cause conclusions.
```

Exact intended branch scope:

```text
HANDOFF.md
docs/reports/2026-08-30-m7-incident-operator-adapter.md
scripts/discovery/m7_incident_operator_adapter_probe.py
src/infra_assurance/incident_operator_adapter.py
tests/test_incident_operator_adapter.py
```

Source artifact:

```text
/var/lib/infra-assurance/evidence/incident-candidates.json
```

Adapter scope:

```text
INCIDENT_CANDIDATES_EXISTING_EVIDENCE_ONLY
```

Trust contract:

```text
mutation_allowed: False
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
```

Raw alert/Event payloads, related workload details, field-level change/drift details, rationales, logs, secrets, raw Terraform state, and raw Kubernetes Secret values are not projected.

## Focused validation — ACCEPTED

```text
6 passed in 0.05s
6 passed in 0.04s
```

## Safe live read-only probe — ACCEPTED

Artifact read/adapter execution:

```text
source_status: COMPLETE
incident_source_status: PARTIAL
cluster_id: k3s-main
scope: INCIDENT_CANDIDATES_EXISTING_EVIDENCE_ONLY
```

Current compact summary:

```text
incident_candidates: 4
active_candidates: 4
suppressed_candidates: 0
unknown_candidates: 0
candidates_with_related_warning_events: 1
candidates_with_exact_recent_change: 0
candidates_with_exact_drift: 0
candidates_requiring_live_verification: 4
attention_total: 2
required_verification_categories_total: 6
projected_candidates: 4
```

Current attention:

```text
INCIDENT_SOURCE_INCOMPLETE / UNKNOWN / count=1
ACTIVE_INCIDENT_CANDIDATES / SIGNAL / count=4
```

Current candidate groups:

```text
Namespace/keycloak / ACTIVE / alerts=2 / events=0 / changes=0 / drift=0 / checks=1
Namespace/monitoring / ACTIVE / alerts=5 / events=0 / changes=0 / drift=0 / checks=1
Namespace/moodle / ACTIVE / alerts=2 / events=1 / changes=0 / drift=0 / checks=2
Platform/k3s-main / ACTIVE / alerts=2 / events=0 / changes=0 / drift=0 / checks=2
```

Current required live verification entries:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_RELATED_EVENT_OBJECT_STATE -> KUBERNETES_OBJECT
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PROMETHEUS_RULE_INPUTS -> PROMETHEUS_RULE_INPUTS
```

Trust/truncation:

```text
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
candidate_groups_truncated: False
required_live_verification_truncated: False
```

Interpretation:

```text
four active candidate groupings observed: true
confirmed incidents observed by this adapter: false
root cause established: false
one candidate has related Warning Event context: true
exact recent-change association observed: false
exact drift association observed: false
source completeness: PARTIAL
```

The zero exact-change/drift counts are bounded to the current source artifact and are not universal absence claims. The exact incomplete source domain was not printed by the allowlisted probe and must not be guessed.

## Full repository suite — ACCEPTED

```text
435 passed in 2.24s
```

## Mutation boundary

This slice is repository-only plus a read-only evidence probe. It does NOT change systemd, installed `/opt` runtime, collector service/timer, Kubernetes RBAC/kubeconfig, filesystem permissions, datastores, or infrastructure.

No deployment authorization is requested or implied.

## Merge gate — READY

Before merge:

1. compare branch against accepted main `abd8fe56832f1868e09e1cd26afbbc40046d9965`;
2. verify exactly the five intended files listed above;
3. ensure no temporary/debug/placeholder files exist;
4. create a non-draft PR;
5. verify changed filenames and mergeability;
6. squash-merge;
7. carry the new accepted main SHA forward.

Do not integrate this adapter into installed operator attention until this slice is merged and a later runtime-integration slice is separately reviewed.

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
