# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only the transition/report documents named below.

## Current execution checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
current accepted main: 9ef418b9af6fcdd42a82c2b936a40c4428394924
Milestone 7: COMPLETE WITHIN ACCEPTED READ-ONLY SCOPE
Milestone 8: ACTIVE — INSTALLED RUNTIME RECONCILIATION PREPARED
active implementation branch: agent/m8-installed-runtime-reconciliation
active pull request: pending creation
accepted M8 baseline pull request: #91 (merged; replaces closed Draft PR #90)
open project PRs at reconciliation branch creation: none
scoped installed __init__.py reconciliation authorized: true
broader infrastructure mutation authorized: false
management host: mgmt-automation
cluster: k3s-main
```

The first M8 baseline was squash-merged as `9ef418b9af6fcdd42a82c2b936a40c4428394924`. The reconciliation branch was created directly from that accepted `main`, with no other open project pull request.

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
pull request: #91 MERGED — REPLACES CLOSED DRAFT PR #90
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

## Active M8 installed runtime reconciliation

Read:

```text
docs/reports/2026-08-30-m8-installed-runtime-reconciliation.md
```

Current slice:

```text
branch: agent/m8-installed-runtime-reconciliation
branch point: 9ef418b9af6fcdd42a82c2b936a40c4428394924
helper: scripts/reconcile-installed-runtime-module.py
tests: tests/test_m8_installed_runtime_reconciliation.py
report status: PREPARED — REVIEWED LIVE APPLY GATE PENDING
focused repository validation: 15 passed in 0.09s
full repository suite: 471 passed in 1.42s
management-host mutation performed in this slice: false
```

Repository inspection established that `bootstrap-observer.sh` installs the full source tree, while the later bounded operator-runtime deployment helper used an explicit module list that omitted `__init__.py`. The omission is an observed recurrence mechanism consistent with the one-file drift, not confirmed historical root cause because prior execution history remains `UNKNOWN`.

The prepared change:

- adds `__init__.py` to future bounded operator-runtime deployment sets;
- plans by hash and metadata without mutation or content projection;
- applies only the one installed `__init__.py` through a dedicated root-only mode;
- stores a root-only, hash-addressed rollback copy;
- uses compile-check, same-directory atomic replacement, file/directory `fsync`, and post-install hash/owner/group/mode verification;
- automatically restores the previous bytes if post-install verification fails;
- performs no systemd action, service start, unit/timer change, permission broadening, Kubernetes/RBAC, scheduler, backup-platform, Terraform, Ansible, or infrastructure mutation.

The user explicitly authorized proceeding to this next step on 2026-08-30. That authorization is bounded to the reviewed installed `__init__.py` reconciliation and its verification; it is not broader mutation authority.

## Exact next step

1. Review the active reconciliation PR once its number is recorded here; do not extend its mutation boundary.
2. On `mgmt-automation`, pull `agent/m8-installed-runtime-reconciliation` and run the focused test from the reconciliation report.
3. Run the helper without arguments and confirm `CHANGE_REQUIRED`, `mutation_allowed=false`, and the exact `__init__.py` scope.
4. Run the authorized `--apply` command from the report and retain its `rollback_token`.
5. Run the M8 baseline probe again and require installed runtime/repository match with zero observation failures.
6. Run the full repository suite and update the report/HANDOFF with accepted live evidence before merging the slice.
7. If verification fails, use only the emitted rollback token, rerun the baseline, and record the failure; do not continue to the timeout change.

Only the exact installed `__init__.py` reconciliation described above is authorized in this slice. Do not change the unit, service/timer state, broader permissions, schedule, backup, RBAC, or infrastructure. Do not reconstruct M7 from chat memory.
