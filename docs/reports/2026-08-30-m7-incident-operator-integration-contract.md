# Milestone 7 — Incident Operator Integration Contract

Date: 2026-08-30
Status: CORRECTIVE FOCUSED VALIDATION ACCEPTED / LIVE NO-WRITE PROBE PENDING
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

The integrated output must preserve:

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

The test exposed a real implementation bug. The integration incorrectly passed final `max_items=2` into the incident adapter as its verification cap. That truncated three incident verification entries to two before the combined total was calculated.

The test expectation was not weakened.

## Corrective decision

Projection truncation must not alter the pre-truncation combined total.

The incident adapter now uses its independent accepted verification bound, while the integration layer applies `max_items` only to the final projected list. This follows the same separation already used by the Kubernetes+backup integration.

Corrected semantics for the failing fixture:

```text
existing required verification total: 8
incident verification entries before final projection truncation: 3
combined required_live_verification_total: 11
final projected list with max_items=2: 2
required_live_verification_truncated: True
```

The non-blocking Python regex warning was also corrected by using a raw regex string. No contract assertion was removed.

## Corrective focused validation — ACCEPTED

Executed on `mgmt-automation` after pulling the corrective branch head:

```text
6 passed in 0.06s
```

Accepted interpretation:

```text
combined totals preserved before final projection truncation: true
required_live_verification_total fixture value: 11
final max_items truncation remains independent: true
unaccepted scope and mutation semantics still fail closed: true
cluster mismatch still fails closed: true
incident trust language preserved: true
regex deprecation warning observed: false
```

No deployment, systemd change, installed-runtime change, or infrastructure mutation occurred during this corrective validation.

## Safe no-write live probe

```text
scripts/discovery/m7_incident_operator_integration_probe.py
```

The probe reads only the two existing derived artifacts, calls the integration builder in memory, prints allowlisted compact fields, writes nothing, and performs no live infrastructure query.

A failed read, invalid scope, cluster mismatch, or failed builder execution must remain an observation/contract failure and must not be converted into zero counts or absence evidence.

## Mutation boundary

This slice does NOT change:

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

## Next gate

Run only the safe no-write integration probe against the current protected `operator-attention.json` and `incident-candidates.json` artifacts. Do not deploy or replace the installed operator-attention runtime in this slice.
