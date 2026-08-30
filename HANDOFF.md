# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only the transition/report documents named below.

## Accepted milestone boundary

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted functional main before M7 closure docs: b236c2e74960327ca70239a9ffcf15f9e52cfa63
Milestone 7: COMPLETE WITHIN ACCEPTED READ-ONLY SCOPE
Milestone 8: NEXT
active implementation branch: none after closure merge
broader infrastructure mutation authorized: false
management host: mgmt-automation
cluster: k3s-main
```

At this milestone boundary, verify current `main` directly after the closure PR is merged. Do not create a self-referential documentation-only SHA update loop.

## M7 closure

Read:

```text
docs/reports/2026-08-30-m7-closure.md
```

M7 accepted the read-only operational-intelligence layer answering, with explicit evidence boundaries:

```text
what needs attention now
what changed
what is unknown/stale
what backup/recovery state is unsupported or unknown
where drift is observed
which signals form incident candidates
what must be verified before a change
what the safest next action is
```

The installed five-minute operator runtime remains:

```text
runtime identity: infra-assurance
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
mutation_allowed: False
prometheus_rule_context_integration < backup_assurance_foundation < operator_attention_backup < operator_attention_incident
```

Last accepted installed operator snapshot before closure:

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

These counts are observations, not invariants.

The final M7 repository functional slice added operator context to the existing task-scoped planning preflight. Accepted validation:

```text
focused tests: 7 passed in 0.08s; repeat 7 passed in 0.04s
safe no-write protected-artifact probe: ACCEPTED
full repository suite: 452 passed in 2.44s
```

Accepted planning behavior includes:

```text
base preflight preserved
matching cluster/operator scope required
ACTIVE target/platform candidate -> verification, not incident/root-cause claim
unrelated namespace candidates not promoted into task risk
SUPPRESSED != RESOLVED
backup UNKNOWN != UNPROTECTED
stateful post-change verification requires authoritative backup evidence before stronger protection claims
safest_next_action is deterministic and non-executable
mutation_allowed=false
```

The additive operator-aware planning adapter is accepted repository functionality. It was validated against protected current evidence without deployment. Do not treat its repository acceptance as authorization for a management-host installation change.

## Preserved UNKNOWN / deferred states

Do not reopen these with weak probes.

Backup/recovery:

```text
physical failure-domain independence: UNKNOWN
retention effectiveness: UNKNOWN
accepted RPO/RTO evaluation: UNKNOWN
restore verification: UNKNOWN
integrity verification: UNKNOWN
application/database-consistent backup evidence: UNKNOWN
```

IaC governance:

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Incident evidence:

```text
last accepted incident source coverage: PARTIAL
candidate absence under incomplete coverage != negative evidence
```

## Trust invariants

Preserve across M8:

```text
DECLARED != OBSERVED
NONE_OBSERVED_IN_BOUNDED_SOURCE != universal absence
FAILED_TO_OBSERVE != negative evidence
UNKNOWN != false
backup UNKNOWN != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
incident candidate != confirmed incident
incident candidate != root cause
SUPPRESSED != RESOLVED
recommendation != approval
mutation_allowed=false unless separately reviewed and explicitly authorized
```

Never expose secrets, tokens, passwords, private keys, raw Kubernetes Secret values, sensitive Terraform state, complete sensitive connection strings, raw backup contents, or unnecessary sensitive configuration.

## M8 bootstrap

Read:

```text
docs/M8_START_HERE.md
```

First M8 slice:

```text
branch: agent/m8-runtime-hardening-baseline
goal: evidence-backed read-only reliability and least-privilege baseline for the existing infra-assurance collector runtime
```

Inspect before changing anything:

```text
systemd service/timer identity and sandbox
writable paths and artifact ownership
timer cadence and overlap behavior
timeout/restart/failure semantics
failure visibility
installed runtime/code boundaries
atomic-write assumptions
platform evidence/history backup status
```

The baseline must distinguish:

```text
DECLARED
OBSERVED
UNKNOWN
FAILED_TO_OBSERVE
INFERENCE
REQUIRES_CHANGE
```

It should identify one smallest justified hardening change. Do not apply unit, permission, scheduling, backup, RBAC, or infrastructure mutations in the baseline slice.

## Exact next step for a fresh M8 session

1. Read all Project Sources.
2. Read `docs/PROJECT_CONTINUITY.md`.
3. Read this `HANDOFF.md` from current `main`.
4. Read `docs/reports/2026-08-30-m7-closure.md` and `docs/M8_START_HERE.md`.
5. Verify current `main` and confirm there is no unresolved M7 PR.
6. Create `agent/m8-runtime-hardening-baseline` from current accepted `main`.
7. Inspect existing repository systemd/runtime declarations before writing the smallest read-only baseline probe.

Do not reconstruct M7 from chat memory and do not repeat completed discovery solely because a new tab has started.
