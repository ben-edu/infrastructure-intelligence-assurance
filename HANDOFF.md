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

The accepted five-minute collector now produces the final operator projection under the existing `infra-assurance` identity.

```text
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
mutation_allowed: False
runtime identity: infra-assurance
prometheus_rule_context_integration < backup_assurance_foundation < operator_attention_backup < operator_attention_incident
final runtime-integration suite: 445 passed in 2.87s
```

Last accepted installed evidence snapshot:

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

Trust semantics remain:

```text
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
UNKNOWN backup protection != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
```

Counts are observed evidence and may change; they are not hard runtime invariants.

## Existing planning-preflight architecture

Do not create a second pre-change pack implementation. The repository already has the accepted task-scoped planning preflight:

```text
docs/decisions/0004-task-scoped-planning-preflight.md
src/infra_assurance/planning_preflight.py
tests/test_planning_preflight.py
schemas/deployment-preflight.schema.json
```

ADR 0004 already requires a deterministic read-only preflight that separates evidence-backed facts, conflicts, inferences/attention, unknowns, required live verification, a non-executable candidate plan, and post-change verification. `mutation_allowed` remains false.

## Active slice — enrich planning preflight with operator context

Goal:

```text
Use the accepted operator-attention artifact as an additional compact input to the existing task-scoped deployment planning preflight so current observability, backup-assurance, and incident-candidate context can influence pre-change verification without duplicating the preflight architecture or authorizing execution.
```

Expected source artifact:

```text
/var/lib/infra-assurance/evidence/operator-attention.json
```

Required accepted operator scope:

```text
KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

Trust boundary:

```text
mutation_allowed: False
operator attention does not replace source evidence
incident candidates are not confirmed incidents or root cause
SUPPRESSED != RESOLVED
backup UNKNOWN != UNPROTECTED
partial/incomplete operator evidence must not become negative evidence
preflight remains non-executable
```

## Exact next step

Inspect `planning_preflight.py`, `tests/test_planning_preflight.py`, and the deployment-preflight schema on this branch. Design the smallest backward-compatible integration contract for optional operator-attention input.

Prefer an additive, task-scoped projection. Do not rewrite the existing preflight model, do not add a new service/timer, do not query live infrastructure, and do not introduce AI-provider or remediation execution in this slice.

After the contract is prepared, run focused repository tests before any protected-artifact probe.

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
- derived projections do not replace source evidence;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the planning projection;
- no remediation or infrastructure mutation is implied;
- generated operational semantics keep `mutation_allowed=false`.
