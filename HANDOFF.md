# Project Handoff

This is the compact continuation checkpoint for the Infrastructure Intelligence & Assurance Platform. Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable checkpoint

- repository: `ben-edu/infrastructure-intelligence-assurance`
- stable branch: `main`
- current main HEAD: `7a86faffa33c4cbe6d8fc46695f6d4c032e95d5b`
- accepted PR #30 foundation merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- accepted PR #32 discovery merge: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
- accepted PR #33 PVE recovery-point adapter merge: `58dca4289a3c302ef9098564da59b7d312aae71e`
- accepted PR #35 VM assurance merge: `59924eb93cbed0ecfef6c2dc6ffbd98af031c547`
- accepted PR #38 PVE task-result merge: `f33506ba59281dac31485616c439126d7b41c30d`
- post-PR38 Handoff merge: `7a86faffa33c4cbe6d8fc46695f6d4c032e95d5b`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- PVE collectors remain manual-only; no systemd credential wiring

A prior connector housekeeping sentinel add/delete produced no net project-content or runtime change.

Milestones 0–3 are live validated. Milestone 4 evidence-first vertical path is accepted and sufficiently complete. Milestone 5 is active.

## Stable Milestone 5 evidence

Kubernetes PVC foundation remains separate:

```text
backup_assurance_version: 0.1
PVC assets: 37
protection UNKNOWN: 37
unprotected_claims: 0
```

Accepted BM2 PVE recovery-point source from PR #33:

```text
proxmox_ve_backup_evidence_version: 0.1
source: pve-bm2
current guests: 12
recovery points: 12
VMIDs with recovery points: 100,101,106,107,108,109
VMIDs with no recovery point in complete local scope: 102,103,104,105,110,9000
PBS backend: false
credential_runtime_approved: false
```

Accepted VM Backup Assurance from PR #35:

```text
vm_backup_assurance_version: 0.1
VM assets: 12
recovery-point observed: 6
complete selected-scope negative: 6
protection unknown: 12
restore/integrity/RPO/RTO unknown: 12
unprotected claims: 0
Kubernetes PVC assets modified: 0
```

Accepted PVE task-result evidence from PR #38:

```text
package: 0.22.0
pve_backup_task_results_version: 0.1
source: pve-bm2
source status: COMPLETE
rows returned: 22
successful task results: 22
strict recovery-point/task matches: 9
recovery points without strict match in returned history: 3
limit saturated: false
historical completeness: NOT_ESTABLISHED
runtime credential approved: false
```

Strict correlation contract is same VMID + successful VZDUMP + recovery-point/task-start delta <=2 seconds. Current strict deltas are 0 or 1 second.

The three old retained points that remain unmatched are:

```text
VMID 106 -> 2025-11-24T08:50:52Z
VMID 107 -> 2025-11-21T10:19:36Z
VMID 108 -> 2025-11-21T10:29:32Z
```

Missing historical task evidence is not failed-backup evidence.

The existing BM2 token remains discovery-only: broad/admin-like, env file mode `0644`, TLS verification false. Runtime PVE collection remains blocked until a separate least-privilege observer identity and trusted TLS path are accepted.

Operator confirms there is no PBS today. Future PBS compatibility remains mandatory through separate source adapters with explicit provenance and common assurance dimensions.

## Active implementation — PR #41 VM LAST_SUCCESSFUL_BACKUP integration

- PR: `#41 Milestone 5 integrate last successful VM backup evidence`
- branch: `feature/m5-vm-last-successful-backup`
- base main: `7a86faffa33c4cbe6d8fc46695f6d4c032e95d5b`
- package: `0.23.0`
- output: `vm_backup_assurance_version=0.2`
- integration: `last_successful_backup_integration.version=0.1`
- mode: `STRICT_CORRELATION_ONLY`
- status: Draft; repository/manual-derived gate pending
- network/Proxmox query: none
- credential access: none
- RBAC change: none
- systemd change: none
- infrastructure mutation: none
- Kubernetes PVC mutation: none

Relevant files:

```text
src/infra_assurance/vm_last_successful_backup_integration.py
schemas/vm-last-successful-backup-integration.schema.json
tests/test_vm_last_successful_backup_integration.py
tests/test_vm_last_successful_backup_integration_wiring.py
docs/decisions/0024-integrate-strict-backup-task-success-into-vm-assurance.md
docs/milestone-5-vm-last-successful-backup-integration.md
docs/reports/2026-08-15-m5-vm-last-successful-backup-integration-live-test-gate.md
```

### Input boundary

Consume only accepted local artifacts:

```text
/tmp/vm-backup-assurance.json
/tmp/proxmox-ve-backup-task-results.json
```

Do not rerun any PVE collector in the PR #41 gate.

### Derived join contract

The integration does not recalculate time correlation. It accepts only existing `STRICT_SUCCESS_TASK_MATCH` records and validates:

```text
matching accepted source identity
recovery-point identity owned by the target VM
task-result identity exists
task type = VZDUMP
task result = SUCCESS
task VMID = correlation VMID
```

Contract mismatch fails the integration.

### Positive semantics

For a VM with one or more valid strict matches:

```text
last_successful_backup_status: OBSERVED
last_successful_backup_at: latest matched successful task end_time
LAST_SUCCESSFUL_BACKUP dimension: OBSERVED
```

Bounded evidence contains only:

```text
source_type: PROXMOX_VE_VZDUMP_TASK_RESULT
source_id
recovery_point_id
task_result_id
basis: [STRICT_SUCCESS_TASK_MATCH]
```

### Unknown semantics

Without strict support:

```text
last_successful_backup_status: UNKNOWN
last_successful_backup_at: null
LAST_SUCCESSFUL_BACKUP dimension: REQUIRED
```

An unmatched old recovery point is not backup failure. A VM may still have observed latest success if a newer retained recovery point has strict successful-task support.

### Unchanged dimensions

Every VM must preserve:

```text
protection_status: UNKNOWN
integrity_verification_status: UNKNOWN
restore_verification_status: UNKNOWN
failure_domain_status: UNKNOWN
scheduled_protection_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

Recovery-point status, backup mechanism, retention context and Kubernetes PVC assurance must not be recomputed or changed.

Task-result source freshness remains `UNKNOWN`. Historical completeness remains `NOT_ESTABLISHED`.

## Exact acceptance requirements for PR #41

1. full pytest passes;
2. package `0.23.0` and CLI `iia-vm-last-successful-backup` are present;
3. no RBAC/systemd diff;
4. integration contains no network/query/control/credential client markers;
5. both input artifacts validate and remain byte-identical during derivation;
6. output validates against the v0.2 integration schema;
7. VM asset set remains exactly unchanged;
8. current accepted artifacts produce observed latest success only for VMIDs with strict matches;
9. latest success timestamp is the latest matched task completion time, not archive creation time;
10. exactly the accepted strict evidence is consumed; no loose time heuristic is introduced;
11. unsupported VMs remain UNKNOWN;
12. old unmatched recovery points remain history limitations, not failures;
13. `protection_status` remains UNKNOWN for all VMs;
14. restore/integrity/failure-domain/scheduled-protection/RPO/RTO remain unchanged/unknown;
15. `unprotected_claims=0` and `kubernetes_pvc_assets_modified=0`;
16. no unsafe task/source/credential fields or URLs enter output.

On PASS: mark ADR 0024/report Accepted, update Handoff, ready and squash-merge PR #41.

On FAIL: diagnose the exact implementation defect and rerun only the focused failed gate when safe.

## Milestone 5 roadmap coverage still open

```text
PostgreSQL
MariaDB
PVC assurance beyond foundation
PBS (future; not present today)
external backup targets
failure-domain evidence
retention effectiveness
RPO/RTO
restore tests
```

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance remain separate evidence layers;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- historical task incompleteness is not backup failure;
- observation credentials remain separate from control credentials;
- stale/current/unknown semantics remain explicit;
- no secrets, tokens, private keys, raw Kubernetes Secret values, Terraform state, raw sensitive Proxmox configuration, complete sensitive connection strings, or raw task logs enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
