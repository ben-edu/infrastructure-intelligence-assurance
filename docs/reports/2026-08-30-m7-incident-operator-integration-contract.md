# Milestone 7 — Incident Operator Integration Contract

Date: 2026-08-30
Status: PREPARED / FOCUSED VALIDATION PENDING
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

## Prepared validation

Focused tests:

```text
tests/test_operator_attention_incident.py
```

Coverage includes:

- combined attention/verification totals;
- preservation of compact-only incident projection;
- explicit PARTIAL incident source semantics;
- cluster mismatch fail-closed behavior;
- rejection of unaccepted operator scope/mutation semantics;
- truncation while retaining total counts;
- Markdown trust language.

Safe no-write live probe:

```text
scripts/discovery/m7_incident_operator_integration_probe.py
```

The probe reads only the two existing derived artifacts, calls the integration builder in memory, prints allowlisted compact fields, writes nothing, and performs no live infrastructure query.

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

Run the focused integration tests. If they pass, run the safe no-write probe against the protected current artifacts. Do not deploy or replace the installed operator-attention runtime in this slice.
