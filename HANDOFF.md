# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable checkpoint

- repository: `ben-edu/infrastructure-intelligence-assurance`
- current main HEAD after PR #41 merge: `d0c9d28711aecb19150988dbf53003a98aa91ff8`
- accepted PR #30 foundation merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- accepted PR #32 discovery merge: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
- accepted PR #33 PVE recovery-point adapter merge: `58dca4289a3c302ef9098564da59b7d312aae71e`
- accepted PR #35 VM assurance merge: `59924eb93cbed0ecfef6c2dc6ffbd98af031c547`
- accepted PR #38 PVE task-result merge: `f33506ba59281dac31485616c439126d7b41c30d`
- accepted PR #41 VM last-successful-backup merge: `d0c9d28711aecb19150988dbf53003a98aa91ff8`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- PVE collectors remain manual-only; no systemd credential wiring

Milestones 0–3 are live validated. Milestone 4 evidence-first path is accepted and sufficiently complete. Milestone 5 is active.

## Stable Milestone 5 evidence

Kubernetes PVC foundation:

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
with recovery points: 100,101,106,107,108,109
no recovery point in complete local scope: 102,103,104,105,110,9000
PBS backend: false
runtime credential approved: false
```

Accepted PVE task-result evidence from PR #38:

```text
pve_backup_task_results_version: 0.1
rows returned: 22
successful task results: 22
strict recovery-point/task matches: 9
unmatched retained recovery points: 3
historical completeness: NOT_ESTABLISHED
```

Accepted VM Backup Assurance v0.2 from PR #41:

```text
package: 0.23.0
assets: 12
mode: STRICT_CORRELATION_ONLY
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
strict success correlations consumed: 9
unmatched historical recovery points: 3
protection UNKNOWN: 12
restore/integrity/failure-domain/RPO/RTO: UNKNOWN
unprotected_claims: 0
kubernetes_pvc_assets_modified: 0
```

Observed VMIDs for `LAST_SUCCESSFUL_BACKUP`:

```text
100,101,106,107,108,109
```

Unknown VMIDs:

```text
102,103,104,105,110,9000
```

Accepted PR #41 focused retry:

```text
262 passed in 1.32s
task ID contract alignment: PASS
input artifacts unchanged: true
output schema: PASS
sensitive/raw projection: none
```

The accepted task-result ID contract is `^pve-backup-task:[a-f0-9]{24}$`. The first PR #41 gate was rejected because its integration schema used a stale synthetic ID shape; the schema/fixtures/regression tests were corrected before acceptance.

Task success does not establish protection quality, restore verification, integrity, RPO, or RTO. Missing historical task evidence is not backup failure.

## PVE credential/runtime boundary

The existing BM2 token remains discovery-only: broad/admin-like, env file mode `0644`, TLS verification false. Runtime PVE collection is blocked until a separate least-privilege observer identity and trusted TLS path are accepted.

There is no PBS today. Future PBS compatibility remains mandatory through separate source adapters and common assurance dimensions.

## Exact next step — bounded VM primary-storage failure-domain preflight

The next smallest useful M5 gap is `BACKUP_FAILURE_DOMAIN`.

Current backup recovery points are on `pve-bm2 / delfan / local`. This does not prove whether backup copies share the same failure domain as VM primary disks.

Run one manual read-only BM2 preflight using the existing discovery-only credential. Do not persist or print raw VM config.

Safe projection only:

```text
vmid
node
primary storage IDs referenced by actual VM disk devices
storage shared/node-local status only when authoritative PVE metadata proves it
```

Current accepted VMIDs:

```text
100,101,102,103,104,105,106,107,108,109,110,9000
```

Never project raw disk strings, volids, paths, serials, cloud-init, networks, MAC/IP values, credentials, snippets, or raw VM config.

Trust rules:

1. same node alone is insufficient to classify failure-domain separation;
2. storage names/types are not enough unless authoritative metadata proves shared vs node-local scope;
3. same-node node-local primary and backup storage may become a bounded failure-domain candidate only after a separate source artifact is accepted;
4. incomplete/permission-limited evidence is UNKNOWN or FAILED_TO_OBSERVE, never absence or separation;
5. no VM/storage/backup/snapshot/schedule/ACL/token/infrastructure mutation;
6. broad discovery credentials must not enter runtime artifacts.

Only implement a new source artifact if this preflight proves a safe authoritative join.

## Milestone 5 roadmap gaps still open

```text
PostgreSQL
MariaDB
PVC assurance beyond foundation
PBS (future)
external backup targets
failure-domain evidence
retention effectiveness
RPO/RTO
restore tests
```

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance remain separate;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- observation credentials remain separate from control credentials;
- stale/current/unknown semantics remain explicit;
- network timeout is not absence unless observation scope is known complete;
- no secrets, raw sensitive config/state, raw task logs, or raw VM config enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
