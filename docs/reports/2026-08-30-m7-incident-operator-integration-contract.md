# Milestone 7 — Incident Operator Integration Contract

Date: 2026-08-30
Status: LIVE NO-WRITE PROBE ACCEPTED / FULL-SUITE PENDING
Mode: repository-only integration over existing operator-attention and incident-candidate artifacts

## Goal

Combine the accepted Kubernetes+backup operator-attention artifact with the accepted compact incident-candidate projection so grouped current signals can appear in one operator-facing contract without promoting candidates to confirmed incidents or root-cause conclusions.

## Inputs

```text
/var/lib/infra-assurance/evidence/operator-attention.json
/var/lib/infra-assurance/evidence/incident-candidates.json
```

Required existing operator scope:

```text
KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
```

New integration scope:

```text
KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

## Implementation

```text
src/infra_assurance/operator_attention_incident.py
```

The integration:

- accepts only the previously accepted Kubernetes+backup operator scope;
- fails closed on cluster mismatch or `mutation_allowed != false`;
- appends compact incident attention and live-verification checks;
- preserves existing Kubernetes and backup summary/trust fields;
- adds compact incident summary, candidate groups, source status, trust, and truncation metadata;
- discards raw alert/Event payloads, impact entity details, and field-level change/drift details through the accepted incident adapter;
- provides an executable file-writing CLI contract for later separately reviewed runtime integration.

## Trust semantics

The integrated output preserves:

```text
mutation_allowed: False
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
UNKNOWN backup protection != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
```

Incident source incompleteness remains explicit. Candidate absence under partial source coverage is not negative evidence.

## Initial focused validation — FAILED AND PRESERVED

Executed on `mgmt-automation`:

```text
1 failed, 5 passed, 1 warning in 0.10s
```

Failing test:

```text
tests/test_operator_attention_incident.py::test_combined_totals_survive_projection_truncation
```

Observed mismatch:

```text
expected required_live_verification_total: 11
observed required_live_verification_total: 10
```

The test exposed a real implementation bug. The integration incorrectly passed final `max_items=2` into the incident adapter as its verification cap. That truncated three incident verification entries to two before the combined total was calculated. The test expectation was not weakened.

## Corrective focused validation — ACCEPTED

Projection truncation was separated from pre-truncation totals. Corrected fixture semantics:

```text
existing required verification total: 8
incident verification entries before final projection truncation: 3
combined required_live_verification_total: 11
final projected list with max_items=2: 2
required_live_verification_truncated: True
```

Corrective focused result:

```text
6 passed in 0.06s
```

The regex deprecation warning was also removed with a raw regex string. No assertion was weakened or removed.

## Safe live no-write integration probe — ACCEPTED

Executed with bounded privilege only to read the protected derived artifacts. The probe performed no live infrastructure query and wrote nothing.

Accepted safety:

```text
mutation_allowed: False
live_infrastructure_query_performed: False
source_artifacts_written: False
systemd_modified: False
installed_runtime_modified: False
candidate_promoted_to_confirmed_incident: False
root_cause_claimed: False
```

Accepted contract:

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

Incident attention added to the accepted operator projection:

```text
INCIDENT_SOURCE_INCOMPLETE / UNKNOWN / count=1
ACTIVE_INCIDENT_CANDIDATES / SIGNAL / count=4
```

Current compact incident candidate groups:

```text
Namespace/keycloak / ACTIVE / alerts=2 / events=0 / checks=1
Namespace/monitoring / ACTIVE / alerts=5 / events=0 / checks=1
Namespace/moodle / ACTIVE / alerts=2 / events=1 / checks=2
Platform/k3s-main / ACTIVE / alerts=2 / events=0 / checks=2
```

Incident live-verification entries added by the integration:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_RELATED_EVENT_OBJECT_STATE -> KUBERNETES_OBJECT
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PROMETHEUS_RULE_INPUTS -> PROMETHEUS_RULE_INPUTS
```

The combined total of 14 is the accepted existing operator total of 8 plus six current incident verification entries. Repeated alert-condition checks are candidate-scoped and are not evidence that verification has already occurred.

Accepted trust/truncation:

```text
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
attention_now_truncated: False
required_live_verification_truncated: False
incident_candidates_truncated: False
```

## Interpretation

The integrated contract currently surfaces seven operator-attention items and fourteen required live-verification entries across the accepted Kubernetes, backup-assurance, and incident-candidate evidence. Four incident candidates are ACTIVE, one has related Warning Event context, and the incident source remains PARTIAL.

These candidate groupings are not confirmed incidents or root-cause conclusions. The partial incident source means the current candidate set is not a universal absence statement about other possible incidents or signals.

## Mutation boundary

This slice does NOT change systemd, installed `/opt` runtime, collector service/timer, Kubernetes RBAC/kubeconfig, filesystem permissions, datastores, or infrastructure. No deployment authorization is requested or implied.

## Remaining gate

Run the full repository regression suite on the current branch head. PR/merge is permitted only if the suite passes and exact branch scope remains the five intended files.

Do not deploy or replace the installed operator-attention runtime in this slice.
