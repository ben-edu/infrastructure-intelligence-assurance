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
- current main HEAD before PR #38: `e1fd2832f7f93a2b38b6c5d30ab57855444ea6cf`
- accepted PR #30 foundation merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- accepted PR #32 discovery merge: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
- accepted PR #33 PVE source adapter merge: `58dca4289a3c302ef9098564da59b7d312aae71e`
- accepted PR #35 VM assurance merge: `59924eb93cbed0ecfef6c2dc6ffbd98af031c547`
- post-PR35 Handoff merge: `fc1e22d0ab9fc380caf10c6e9598e59874860b67`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- PVE collectors remain manual-only; no systemd credential wiring

A connector housekeeping mistake briefly created `__do_not_create__` on `main` and immediately deleted it in the next commit. Current `main` therefore advanced to `e1fd283...` with no net project-content diff from that sentinel add/delete pair. No runtime or infrastructure state was affected.

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

Latest observed retained recovery points:

```text
100 -> 2026-05-08T06:13:59Z
101 -> 2026-05-08T10:36:12Z
106 -> 2026-08-14T16:13:14Z
107 -> 2026-08-14T16:40:35Z
108 -> 2026-04-15T12:30:02Z
109 -> 2026-04-13T10:34:52Z
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

Archive presence does not satisfy `LAST_SUCCESSFUL_BACKUP` task-result semantics.

The existing BM2 token is broad/admin-like, env file mode `0644`, TLS verification false, and remains discovery-only. Runtime PVE collection is blocked until a separate least-privilege observer identity and trusted TLS path are accepted.

Operator confirms there is no PBS today. Future PBS compatibility remains mandatory through separate source adapters with explicit provenance and common assurance dimensions.

## Accepted task-result preflight — 2026-08-15

A bounded manual GET-only BM2 task-history preflight proved a safe next source path.

Observed returned scope:

```text
request mode: SERVER_FILTERED_VZDUMP
HTTP status: 200
rows returned: 22
vzdump rows selected: 22
limit: 500
limit saturated: false
historical completeness: NOT_ESTABLISHED
normalized SUCCESS: 22
tasks with numeric VMID: 22
returned timestamp range: 2026-02-24T10:36:47Z .. 2026-08-14T17:39:32Z
```

Recovery-point correlation preflight:

```text
retained recovery points evaluated: 12
strict same-VMID candidates within 0-1 seconds: 9
old points outside returned task history: 3
```

The three old retained points that must not be nearest-task matched are:

```text
VMID 106 -> 2025-11-24T08:50:52Z
VMID 107 -> 2025-11-21T10:19:36Z
VMID 108 -> 2025-11-21T10:29:32Z
```

A successful returned task is authoritative evidence that the PVE `vzdump` task record completed `OK`. It is not restore or integrity verification.

## Active implementation — PR #38 bounded PVE backup task results

- PR: `#38 Milestone 5 observe bounded PVE backup task results`
- branch: `feature/m5-pve-backup-task-results`
- base main: `e1fd2832f7f93a2b38b6c5d30ab57855444ea6cf`
- package: `0.22.0`
- output contract: `pve_backup_task_results_version=0.1`
- status: Draft; repository/manual live gate pending
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

### Query boundary

Preferred:

```text
GET /api2/json/nodes/<node>/tasks?typefilter=vzdump&limit=<bounded>
```

Only if that returns HTTP 400:

```text
GET /api2/json/nodes/<node>/tasks?limit=<bounded>
```

and filter locally.

No task-log endpoint is allowed.

### Safe task projection

Persist only:

```text
task_result_id
task_type=VZDUMP
node
vmid
start_time
end_time
result
```

Never persist complete UPIDs, raw task logs, user/token identity, raw status/error strings, command lines, URLs, raw payloads, or credentials.

### Strict recovery-point correlation

A retained recovery point may become `STRICT_SUCCESS_TASK_MATCH` only when:

```text
same VMID
successful VZDUMP result
absolute(recovery_point.created_at - task.start_time) <= 2 seconds
```

Basis:

```text
VMID
RECOVERY_POINT_CREATED_AT
VZDUMP_START_TIME
```

Anything outside that threshold is `NO_STRICT_MATCH_IN_RETURNED_HISTORY`.

Do not use nearest-task heuristics outside the threshold. Missing historical matches are not failed-backup evidence because `historical_completeness=NOT_ESTABLISHED`.

### Credential boundary

Normal collector execution still rejects group/world-readable credential files and disabled TLS verification. Manual live acceptance may use the existing discovery credential only with explicit override flags.

`runtime_credential_approved=false` is invariant in this artifact.

## Exact acceptance requirements for PR #38

1. full pytest passes;
2. package version `0.22.0` and task-results CLI are present;
3. no RBAC/systemd diff;
4. source recovery-point artifact validates and remains unchanged during collection;
5. task query is GET-only and bounded;
6. current BM2 source returns COMPLETE task observation;
7. output validates against schema;
8. no complete UPID, task log, user/token identity, raw error/status, command line, URL, credential, or raw payload is projected;
9. current 12 retained recovery points produce strict matches only within the 2-second contract;
10. the three pre-2026 returned-history points remain unmatched, not attached to distant tasks;
11. task-history completeness remains `NOT_ESTABLISHED`;
12. no restore/integrity/RPO/RTO claim is created;
13. runtime credential remains unapproved and unwired.

On PASS: mark ADR 0023/report Accepted, update Handoff, ready and squash-merge PR #38.

On FAIL: diagnose the exact implementation defect and rerun only the focused failed gate when safe.

## Exact next step after PR #38 acceptance

If the task-result source is accepted, build a **derived-only VM assurance integration** that consumes local accepted VM assurance + task-result artifacts and strengthens only `LAST_SUCCESSFUL_BACKUP` where authoritative successful task evidence exists.

Do not strengthen restore, integrity, RPO or RTO. Do not treat unmatched historical points as failures. Do not add new PVE queries in that derived integration.

## Milestone 5 roadmap coverage still open

```text
PostgreSQL
MariaDB
PVC assurance beyond foundation
VM backup task-result integration
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
