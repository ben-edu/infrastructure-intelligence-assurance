# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live/discovery report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable checkpoint

- repository: `ben-edu/infrastructure-intelligence-assurance`
- main checkpoint before the PostgreSQL discovery documentation slice: `7b72241676d479948e5c1f6437a9f0bfffb76dcd`
- accepted PR #41 VM last-successful-backup implementation merge: `d0c9d28711aecb19150988dbf53003a98aa91ff8`
- accepted PR #43 PVE VM storage relationship merge: `3fb60c23e8a885f9015f07d6c34270a425197189`
- PR #44 refreshed the handoff after PR #43
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

Current accepted successful task completion times relevant to Kubernetes nodes:

```text
106 -> 2026-08-14T16:39:53Z
107 -> 2026-08-14T17:39:32Z
108 -> 2026-04-15T12:36:38Z
```

Unknown VMIDs:

```text
102,103,104,105,110,9000
```

## Accepted PR #43 — PVE VM storage relationship source

- package: `0.24.0`
- source artifact: `pve_vm_storage_relationship_version=0.1`
- ADR: `docs/decisions/0025-observe-bounded-pve-vm-storage-relationships.md`
- milestone doc: `docs/milestone-5-pve-vm-storage-relationship.md`
- live report: `docs/reports/2026-08-16-m5-pve-vm-storage-relationship-live-test-gate.md`

Accepted gate:

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

All 12 selected VMs resolve primary storage ID `local` and backup storage ID `local`. This is storage-ID relationship evidence only. It does not establish a physical failure domain. `BACKUP_FAILURE_DOMAIN` remains `UNKNOWN`.

## PostgreSQL backup/recovery source discovery — 2026-08-16

Discovery report:

```text
docs/reports/2026-08-16-m5-postgresql-backup-recovery-source-discovery.md
```

Trust decision:

```text
docs/decisions/0026-distinguish-postgresql-infrastructure-recovery-from-database-backup.md
```

### Kubernetes PostgreSQL scope

Eight persistent PostgreSQL workload candidates are observed:

```text
drfarah-staging
fastapi-platform
fastapi-platform-dev
keycloak
openproject
soria-academie
soria-prospecting
toilettage
```

All eight have Bound `local-path` PVCs.

PV node affinity establishes:

```text
k3s-master-01: keycloak
k3s-worker-01: fastapi-platform, fastapi-platform-dev, openproject, soria-prospecting, toilettage
k3s-worker-02: drfarah-staging, soria-academie
```

Bounded Kubernetes backup-mechanism discovery found:

```text
matching PostgreSQL/backup CronJobs: 0
matching PostgreSQL/backup Jobs: 0
```

This is source-scoped negative evidence only, not universal absence.

### Kubernetes node to PVE VM mapping

Bounded read-only PVE observation established:

```text
k3s-master-01 -> VMID 106
k3s-worker-01 -> VMID 107
k3s-worker-02 -> VMID 108
```

The discovery-only PVE credential boundary remains unchanged:

```text
runtime_credential_approved: false
```

### Accepted VM recovery evidence join

The previously accepted source artifacts were byte-verified before in-memory derivation:

```text
/tmp/vm-backup-assurance.json
sha256: 14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a

/tmp/proxmox-ve-backup-task-results.json
sha256: 18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
```

For VMIDs 106, 107, and 108, `LAST_SUCCESSFUL_BACKUP=OBSERVED` with the timestamps listed above.

For all three:

```text
protection: UNKNOWN
restore: UNKNOWN
integrity: UNKNOWN
failure-domain: UNKNOWN
RPO: UNKNOWN
RTO: RTO_UNKNOWN
```

The PostgreSQL relationship currently proven is:

```text
PostgreSQL workload
-> Bound local-path PVC
-> explicit Kubernetes PV storage node
-> K3s VM
-> PVE VMID
-> accepted VM last-successful-backup evidence
```

This is infrastructure recovery context only. It is not PostgreSQL-consistent backup evidence.

Do not classify VMID 108 as stale or an RPO violation from timestamp age alone; no accepted RPO/freshness target exists yet.

### Management-host PostgreSQL

`mgmt-automation` has an observed running PostgreSQL 15 cluster:

```text
postgresql@15-main.service: active/running
```

Observed backup-capable tooling:

```text
pg_dump 15.19
pg_dumpall 15.19
pg_basebackup 15.19
pg_receivewal 15.19
```

Not observed in the inspected command scope:

```text
pgBackRest
Barman
barman-cloud-backup
WAL-G
```

A packaged weekly `pg_basebackup@` systemd template exists, but no configured instance symlink or loaded/known service/timer instance was observed and the timer template is disabled. Tool/template presence does not establish configured or successful PostgreSQL backup execution.

No PostgreSQL-specific cron file-name signal or local backup-script file-name signal was observed. `dpkg-db-backup.timer` is not PostgreSQL application-data backup evidence.

Current local PostgreSQL interpretation:

```text
instance: OBSERVED
backup-capable tooling: OBSERVED
configured PostgreSQL backup mechanism: UNKNOWN
scheduled execution: NOT_OBSERVED_IN_INSPECTED_LOCAL_SCOPE
last successful PostgreSQL backup: UNKNOWN
restore/integrity: UNKNOWN
```

`NOT_OBSERVED_IN_INSPECTED_LOCAL_SCOPE` is not `UNPROTECTED`.

## Exact next step — bounded PostgreSQL infrastructure-recovery context

Do not continue broad PostgreSQL backup discovery or implement a PostgreSQL backup-protection claim from the current evidence.

The next smallest useful Milestone 5 slice is a read-only derived context for the eight Kubernetes PostgreSQL instances only.

The implementation should join accepted/bounded evidence for:

```text
PostgreSQL workload identity
persistent PVC identity
explicit Kubernetes PV storage node
K3s node -> PVE VMID mapping
accepted VM LAST_SUCCESSFUL_BACKUP status/timestamp
```

It must preserve these PostgreSQL-specific dimensions as unknown until a database-aware authoritative source exists:

```text
backup mechanism
backup execution/result
artifact location
retention effectiveness
restore verification
integrity verification
RPO
RTO
```

Do not include the local `mgmt-automation` PostgreSQL instance in the first derived implementation unless an authoritative infrastructure-recovery relationship is separately established for it.

Start with a small versioned schema + pure derivation + tests. No new live collector is required unless an input relationship cannot be established from accepted evidence.

## PVE credential/runtime boundary

The existing BM2 token remains discovery-only: broad/admin-like, env file mode `0644`, TLS verification false. Runtime PVE collection remains blocked until a separate least-privilege observer identity and trusted TLS path are accepted.

There is no PBS today. Future PBS compatibility remains mandatory through separate source adapters and common assurance dimensions.

## Milestone 5 gaps still open

```text
PostgreSQL database-aware backup evidence
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
- infrastructure recovery evidence is not database-consistent backup evidence;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- observation credentials remain separate from control credentials;
- stale/current/unknown semantics remain explicit;
- no RPO violation is inferred without an accepted target;
- network timeout is not absence unless observation scope is known complete;
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, or raw dump contents enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
