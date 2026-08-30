# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only the transition/report documents named below.

## Current execution checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
current accepted main at M8 branch point: b63bed9704832d1e3701ea87dea50e135f2b1f64
Milestone 7: COMPLETE WITHIN ACCEPTED READ-ONLY SCOPE
Milestone 8: ACTIVE — FIRST READ-ONLY BASELINE SLICE ACCEPTED; MERGE PENDING
active implementation branch: agent/m8-runtime-hardening-baseline
active pull request: #90 (draft; content accepted; ready-state transition pending)
open project PRs at branch creation: none
broader infrastructure mutation authorized: false
management host: mgmt-automation
cluster: k3s-main
```

The M8 branch was created directly from current accepted `main`. No unresolved M7 pull request existed at branch creation.

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

## Accepted M8 first slice

Read:

```text
docs/M8_START_HERE.md
docs/reports/2026-08-30-m8-runtime-hardening-baseline.md
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

Current repository state:

```text
probe: scripts/discovery/m8_runtime_hardening_baseline_probe.py
tests: tests/test_m8_runtime_hardening_baseline.py
probe contract: version 0.2 with candidate-specific recommendation evidence
report status: ACCEPTED — LIVE READ-ONLY GATE PASSED
pull request: #90 DRAFT — CONTENT ACCEPTED; READY-STATE TRANSITION PENDING
focused validation: 11 passed in 0.09s
full repository suite: 463 passed in 1.04s
management-host focused validation: 11 passed in 0.22s
accepted live gate: COMPLETE at 2026-08-30T15:24:44.027806Z
accepted live-gate commit: 42c3dcfbb6f07f206073a22f086cb8df1bdd74a9
accepted probe_rc: 0
FAILED_TO_OBSERVE: 0
management-host mutation performed: false
```

Repository declarations currently show the dedicated identity, strict sandbox, five-minute oneshot timer, 12 runtime entrypoints, and atomic per-file writes. They do not declare an explicit start timeout, restart policy, `OnFailure`, or process/history writer lock. These are declarations, not effective installed-state claims.

The first live attempt returned `probe_rc=0` and no observation failures, but probe version 0.1 selected `RECONCILE_INSTALLED_RUNTIME_MODULES` for an observed `__init__.py` mismatch while attaching unrelated timeout evidence. That internally inconsistent recommendation payload remains rejected for acceptance.

The corrected version 0.2 rerun is accepted. It confirms matching service/timer fragments, runtime identity, systemd sandbox, and state ownership/modes; root-owned installed code with no POSIX write access for the runtime identity; and exactly one installed-module mismatch, `__init__.py`. Backup status, external failure visibility, historical overlap/missed activations, and ACL/capability/MAC effects remain explicitly `UNKNOWN`.

Exactly one smallest justified next change is `RECONCILE_INSTALLED_RUNTIME_MODULES`. It must reconcile installed `__init__.py` through a separate reviewed and explicitly authorized change. No hardening control is implemented in this baseline.

## Exact next step

1. Mark PR `#90` ready in GitHub, then review and merge it after its accepted report and exact four-file scope are verified. The automated ready-state transition was attempted but the GitHub connector returned a GraphQL response-schema error; the PR remains Draft.
2. Start the next M8 slice from the resulting accepted `main`; do not extend the baseline PR with the hardening mutation.
3. Re-observe the repository/installed `__init__.py` mismatch without projecting source contents or secrets, and identify the bounded installation/deployment step responsible for it.
4. Propose the smallest reviewed reconciliation and its rollback/verification procedure.
5. Obtain explicit authorization before changing installed code or any management-host unit, permission, schedule, backup, RBAC, or infrastructure state.
6. After an authorized reconciliation, rerun the focused tests, installed-runtime hash comparison, and full repository suite before accepting the next slice.

Do not change the unit, permissions, schedule, backup, RBAC, installed code, or infrastructure during this baseline gate. Do not reconstruct M7 from chat memory.
