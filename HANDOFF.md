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
- `main` before PR #43: `cf6fabc20e962e8b37a48c1962a9865aa66fe394`
- accepted PR #41 implementation merge: `d0c9d28711aecb19150988dbf53003a98aa91ff8`
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

Accepted BM2 PVE recovery-point source:

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

Accepted PVE task-result evidence:

```text
pve_backup_task_results_version: 0.1
rows returned: 22
successful task results: 22
strict recovery-point/task matches: 9
unmatched retained recovery points: 3
historical completeness: NOT_ESTABLISHED
```

Accepted VM Backup Assurance v0.2:

```text
package: 0.23.0
assets: 12
mode: STRICT_CORRELATION_ONLY
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
protection UNKNOWN: 12
restore/integrity/failure-domain/RPO/RTO: UNKNOWN
unprotected_claims: 0
```

Observed VMIDs for `LAST_SUCCESSFUL_BACKUP`:

```text
100,101,106,107,108,109
```

Unknown VMIDs:

```text
102,103,104,105,110,9000
```

## Accepted PR #43 gate — PVE VM storage relationship source

- PR: `#43 Milestone 5 add bounded PVE VM storage relationship evidence`
- branch: `agent/m5-pve-vm-storage-relationship`
- package: `0.24.0`
- source artifact: `pve_vm_storage_relationship_version=0.1`
- ADR: `docs/decisions/0025-observe-bounded-pve-vm-storage-relationships.md`
- milestone doc: `docs/milestone-5-pve-vm-storage-relationship.md`
- live report: `docs/reports/2026-08-16-m5-pve-vm-storage-relationship-live-test-gate.md`

Accepted gate on 2026-08-16:

```text
repository tests: 273 passed in 1.23s
schema: PASS
source status: COMPLETE
mutation_allowed: false
runtime credential approved: false
target_vms: 12
config_complete: 12
same_pve_storage_id_as_backup: 12
different_pve_storage_id_from_backup: 0
unknown: 0
failed_to_observe: 0
direct_or_unresolved_disks: 0
referenced_storage_ids: 1
```

Accepted VMIDs:

```text
100,101,102,103,104,105,106,107,108,109,110,9000
```

For all 12 selected VMs:

```text
primary storage ID: local
backup storage ID: local
relationship: SAME_PVE_STORAGE_ID_AS_BACKUP
```

Accepted storage metadata:

```text
local storage_type: dir
local shared_status: NOT_EXPLICITLY_RETURNED
local node restrictions: none returned
```

The first repository-gate attempt was rejected with `272 passed, 1 failed` due only to a stale test that froze package version `0.23.0`. It occurred before live collection. The test was corrected to enforce version synchronization rather than a frozen package version, and the accepted retry passed all 273 tests.

Trust interpretation:

- same PVE storage ID is accepted source evidence;
- it is not proof of the same physical disk/hardware/power failure domain;
- `local` + `dir` is not interpreted as node-local without authoritative explicit evidence;
- different storage IDs would not by themselves prove independent failure domains;
- `BACKUP_FAILURE_DOMAIN` remains `UNKNOWN`;
- no raw VM config, disk values, volids, paths, serials, cloud-init, network/MAC/IP data, credentials, snippets, or raw API payloads were persisted;
- collector remained HTTP GET only and manual-only;
- no infrastructure mutation occurred.

If PR #43 is still open, its acceptance gates are satisfied and it may be merged. Do not add stronger failure-domain claims during merge.

## Exact next step after PR #43

Do not keep extending the PVE failure-domain path from the current evidence. It has reached a bounded evidence limit because storage locality/physical failure-domain metadata is not authoritative enough for promotion.

The next smallest useful Milestone 5 slice is a read-only PostgreSQL backup/recovery source discovery.

Discovery goal:

```text
Identify current PostgreSQL instances in accepted infrastructure scope and determine, without mutation, what authoritative backup/recovery mechanisms and evidence sources exist for each instance.
```

Start with discovery only. Do not implement a collector until the discovery proves a safe authoritative evidence path.

Required questions:

```text
Which PostgreSQL instances are currently in scope?
What host/VM/Kubernetes workload owns each instance?
What backup mechanism is actually configured or used?
What authoritative source can prove backup execution/result?
Where are backup artifacts stored?
Is retention configuration observable?
Is restore/integrity verification observable?
What is unknown and what requires live verification?
```

Safe projection should prefer identifiers, versions, mechanism names, timestamps/statuses, and bounded provenance only.

Never project database passwords, connection-string credentials, raw `.pgpass`, secret environment values, Kubernetes Secret values, private keys, complete sensitive connection strings, raw dump contents, or database data.

Initial interaction remains read-only. No backup, restore, WAL manipulation, retention change, PostgreSQL configuration change, service restart, or infrastructure mutation is allowed.

## PVE credential/runtime boundary

The existing BM2 token remains discovery-only: broad/admin-like, env file mode `0644`, TLS verification false. Runtime PVE collection remains blocked until a separate least-privilege observer identity and trusted TLS path are accepted.

There is no PBS today. Future PBS compatibility remains mandatory through separate source adapters and common assurance dimensions.

## Milestone 5 gaps still open

```text
PostgreSQL
MariaDB
PVC assurance beyond foundation
PBS (future)
external backup targets
failure-domain assurance beyond storage-ID relationship
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
- no secrets, raw sensitive config/state, raw task logs, raw VM config, or database data enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
