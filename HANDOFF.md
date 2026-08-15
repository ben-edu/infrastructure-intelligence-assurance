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
- current main HEAD before PR #38 merge: `e1fd2832f7f93a2b38b6c5d30ab57855444ea6cf`
- accepted PR #30 foundation merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- accepted PR #32 discovery merge: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
- accepted PR #33 PVE recovery-point adapter merge: `58dca4289a3c302ef9098564da59b7d312aae71e`
- accepted PR #35 VM assurance merge: `59924eb93cbed0ecfef6c2dc6ffbd98af031c547`
- post-PR35 Handoff merge: `fc1e22d0ab9fc380caf10c6e9598e59874860b67`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- PVE collectors remain manual-only; no systemd credential wiring

A connector housekeeping mistake briefly created `__do_not_create__` on `main` and immediately deleted it. Current `main` therefore advanced to `e1fd283...` with no net project-content change from that add/delete pair. No runtime or infrastructure state was affected.

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
PVE: 9.1.9
node: delfan / ONLINE
source status: COMPLETE
current guests: 12
storage: local / dir / backup-enabled
retention projection: keep-all=1
PBS backend: false
cluster backup jobs: 0
recovery points: 12
VMIDs with recovery points: 100,101,106,107,108,109
VMIDs with no recovery point in complete local scope: 102,103,104,105,110,9000
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

Archive presence alone does not satisfy `LAST_SUCCESSFUL_BACKUP`.

The existing BM2 token is broad/admin-like, env file mode `0644`, TLS verification false, and remains discovery-only. Runtime PVE collection is blocked until a separate least-privilege observer identity and trusted TLS path are accepted.

Operator confirms there is no PBS today. Future PBS compatibility remains mandatory through separate source adapters with explicit provenance and common assurance dimensions.

## Active accepted work — PR #38 bounded PVE backup task results

- PR: `#38 Milestone 5 observe bounded PVE backup task results`
- branch: `feature/m5-pve-backup-task-results`
- base main: `e1fd2832f7f93a2b38b6c5d30ab57855444ea6cf`
- package: `0.22.0`
- artifact: `pve_backup_task_results_version=0.1`
- status: repository/manual live accepted; ready for squash merge
- RBAC change: none
- systemd change: none
- runtime credential wiring: none
- infrastructure mutation: none

Relevant files:

```text
src/infra_assurance/proxmox_ve_backup_task_results.py
schemas/proxmox-ve-backup-task-results.schema.json
tests/test_proxmox_ve_backup_task_results.py
tests/test_proxmox_ve_backup_task_results_wiring.py
docs/decisions/0023-observe-bounded-pve-vzdump-task-results.md
docs/milestone-5-pve-backup-task-results.md
docs/reports/2026-08-15-m5-pve-backup-task-results-live-test-gate.md
```

Accepted repository/live gate:

```text
249 passed in 1.61s
source recovery-point artifact unchanged: true
source status: COMPLETE
operation: GET_BOUNDED_VZDUMP_TASK_RESULTS
request mode: SERVER_FILTERED_VZDUMP
HTTP status: 200
rows returned: 22
successful task results: 22
strict recovery-point/task matches: 9
recovery points without strict match in returned history: 3
limit: 500
limit saturated: false
historical completeness: NOT_ESTABLISHED
runtime credential approved: false
credential file mode secure: false
TLS verification: false
discovery override used: true
forbidden projected keys: none
raw URL markers: false
credential material projection: none
restore/integrity/RPO/RTO promotion: none
```

Safe task projection is limited to:

```text
task_result_id
task_type=VZDUMP
node
vmid
start_time
end_time
result
```

Strict recovery-point/task correlation is accepted only when:

```text
same VMID
successful VZDUMP task
absolute(recovery_point.created_at - task.start_time) <= 2 seconds
```

Current strict matches have deltas of 0 or 1 second.

The three older retained recovery points remain unmatched:

```text
VMID 106 -> 2025-11-24T08:50:52Z
VMID 107 -> 2025-11-21T10:19:36Z
VMID 108 -> 2025-11-21T10:29:32Z
```

They are `NO_STRICT_MATCH_IN_RETURNED_HISTORY`, not failed-backup evidence. No nearest-task heuristic is allowed outside the threshold.

`SUCCESS` means only that the returned PVE `vzdump` task record completed with normalized source status `OK`. It does not establish restore verification, integrity verification, RPO, RTO, or universal protection.

## Exact next step after PR #38 merge — derived LAST_SUCCESSFUL_BACKUP integration

Build a derived-only VM assurance integration that consumes local accepted artifacts:

```text
VM Backup Assurance v0.1
PVE Backup Task Results v0.1
```

No new Proxmox query, credential access, RBAC change, systemd wiring, or infrastructure mutation is allowed.

The integration should strengthen only `LAST_SUCCESSFUL_BACKUP` where current VM assurance recovery-point evidence is backed by `STRICT_SUCCESS_TASK_MATCH`.

Required semantics:

1. join only exact source identity + VMID + recovery-point identity already correlated by the accepted task-result artifact;
2. do not recalculate a looser time heuristic in the derived layer;
3. for a VM with one or more strict matched successful retained recovery points, set `last_successful_backup_status=OBSERVED` and expose the latest strictly supported successful backup timestamp plus bounded evidence IDs;
4. if a VM has recovery points but none with strict task-result support, leave `last_successful_backup_status=UNKNOWN`;
5. complete selected-source negative recovery-point evidence remains scoped negative for recovery points only and must not become `UNPROTECTED`;
6. unmatched historical task evidence is not a failed backup;
7. `protection_status` remains `UNKNOWN` for all VMs in this slice;
8. restore verification, integrity verification, failure domain, scheduled protection, RPO, and RTO remain unchanged/unknown;
9. `LAST_SUCCESSFUL_BACKUP` required-evidence dimension may become `OBSERVED` only for strictly supported VMs;
10. source artifact freshness remains explicit; do not invent TTL/currentness;
11. Kubernetes PVC assurance remains untouched;
12. future PBS evidence must be able to satisfy the same common dimension without redesigning VM assurance.

Implement this as a separate derived artifact/versioned integration first. Do not wire runtime PVE collection until least-privilege identity and trusted TLS are accepted.

## Milestone 5 roadmap coverage still open

```text
PostgreSQL
MariaDB
PVC assurance beyond foundation
VM last-successful-backup integration
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
- network timeout is not absence unless observation scope is known complete;
- no secrets, tokens, private keys, raw Kubernetes Secret values, Terraform state, raw sensitive Proxmox configuration, complete sensitive connection strings, or raw task logs enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
