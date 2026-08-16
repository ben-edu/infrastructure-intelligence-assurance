# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live/discovery report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Active execution checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main checkpoint after PR #45: 9653c4077040f102d4d7388608db9b346f826209
active branch: feature/m5-postgresql-infrastructure-recovery-context
package on active branch: 0.25.0
Milestone 5: active
mutation_allowed: false
```

The active slice is not accepted yet. Repository and live gates are pending.

Active files:

```text
src/infra_assurance/postgresql_infrastructure_recovery_context.py
schemas/postgresql-infrastructure-recovery-context.schema.json
tests/test_postgresql_infrastructure_recovery_context.py
tests/test_postgresql_infrastructure_recovery_context_wiring.py
docs/milestone-5-postgresql-infrastructure-recovery-context.md
docs/reports/2026-08-16-m5-postgresql-infrastructure-recovery-context-live-test-gate.md
```

Trust decision:

```text
docs/decisions/0026-distinguish-postgresql-infrastructure-recovery-from-database-backup.md
```

## Stable Milestone 5 evidence

### Kubernetes PVC foundation

```text
backup_assurance_version: 0.1
PVC assets: 37
protection UNKNOWN: 37
unprotected_claims: 0
```

### Accepted PVE recovery-point source

```text
source: pve-bm2
node: delfan
current guests: 12
recovery points: 12
with recovery points: 100,101,106,107,108,109
no recovery point in complete selected local scope: 102,103,104,105,110,9000
PBS backend: false
runtime credential approved: false
```

### Accepted PVE task-result evidence

```text
rows returned: 22
successful task results: 22
strict recovery-point/task matches: 9
unmatched retained recovery points: 3
historical completeness: NOT_ESTABLISHED
```

### Accepted VM Backup Assurance v0.2

Accepted PR #41 implementation merge:

```text
d0c9d28711aecb19150988dbf53003a98aa91ff8
```

State:

```text
assets: 12
mode: STRICT_CORRELATION_ONLY
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
protection UNKNOWN: 12
restore/integrity/failure-domain/RPO/RTO: UNKNOWN
unprotected_claims: 0
```

Observed VMIDs:

```text
100,101,106,107,108,109
```

Relevant accepted timestamps:

```text
106 -> 2026-08-14T16:39:53Z
107 -> 2026-08-14T17:39:32Z
108 -> 2026-04-15T12:36:38Z
```

Accepted source artifacts used by the VM derivation gate:

```text
/tmp/vm-backup-assurance.json
sha256: 14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a

/tmp/proxmox-ve-backup-task-results.json
sha256: 18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
```

### Accepted PVE VM storage relationship

PR #43 merge:

```text
3fb60c23e8a885f9015f07d6c34270a425197189
```

Accepted gate:

```text
package: 0.24.0
repository tests: 273 passed in 1.23s
schema: PASS
source status: COMPLETE
target_vms: 12
config_complete: 12
same_pve_storage_id_as_backup: 12
different_pve_storage_id_from_backup: 0
unknown: 0
failed_to_observe: 0
direct_or_unresolved_disks: 0
```

All selected VMs resolved primary storage ID `local` and backup storage ID `local`. This is logical storage-ID relationship evidence only, not physical failure-domain evidence. `BACKUP_FAILURE_DOMAIN` remains `UNKNOWN`.

## Accepted PostgreSQL source discovery

PR #45 merge:

```text
9653c4077040f102d4d7388608db9b346f826209
```

Discovery report:

```text
docs/reports/2026-08-16-m5-postgresql-backup-recovery-source-discovery.md
```

Eight persistent Kubernetes PostgreSQL workloads were observed:

```text
drfarah-staging       StatefulSet/drfarah-staging-postgres
fastapi-platform      Deployment/postgres
fastapi-platform-dev  Deployment/postgres
keycloak              StatefulSet/keycloak-postgresql
openproject           StatefulSet/openproject-postgresql
soria-academie        StatefulSet/academie-postgres
soria-prospecting     Deployment/soria-postgres
toilettage            StatefulSet/toilettage-postgres
```

All eight have Bound `local-path` PVCs.

PV node affinity establishes:

```text
k3s-master-01: keycloak
k3s-worker-01: fastapi-platform, fastapi-platform-dev, openproject, soria-prospecting, toilettage
k3s-worker-02: drfarah-staging, soria-academie
```

Bounded read-only PVE mapping establishes:

```text
k3s-master-01 -> VMID 106
k3s-worker-01 -> VMID 107
k3s-worker-02 -> VMID 108
```

Kubernetes backup-mechanism discovery in the inspected scope found:

```text
matching PostgreSQL/backup CronJobs: 0
matching PostgreSQL/backup Jobs: 0
```

This is bounded negative evidence only, not universal absence.

### Local management-host PostgreSQL

Observed on `mgmt-automation`:

```text
postgresql@15-main.service: active/running
pg_dump/pg_dumpall/pg_basebackup/pg_receivewal 15.19: present
pgBackRest/Barman/barman-cloud-backup/WAL-G: not observed in inspected command scope
configured pg_basebackup@ systemd instance: not observed
```

The packaged weekly `pg_basebackup@` template is capability/declaration evidence only. It does not establish configured or successful backup execution.

The management-host PostgreSQL instance remains outside the active derived implementation.

## Active slice — PostgreSQL infrastructure recovery context v0.1

Purpose:

```text
PostgreSQL workload
-> persistent PVC
-> explicit PV storage node
-> K3s node
-> PVE VMID
-> accepted VM LAST_SUCCESSFUL_BACKUP evidence
```

The implementation is pure derivation. It introduces no new live collector and no runtime/systemd wiring.

An infrastructure relationship may become `OBSERVED` only when:

```text
PostgreSQL workload observation = OBSERVED
persistence observation = OBSERVED
node-to-VM mapping = OBSERVED
relationship source scope = COMPLETE
VM assurance source scope = COMPLETE
PVE source identities match
VM last-successful-backup = OBSERVED
VM last-successful-backup evidence has accepted STRICT_SUCCESS_TASK_MATCH provenance
```

Malformed observed VM evidence fails closed.

PostgreSQL-specific assurance is structurally fixed to:

```text
protection: UNKNOWN
backup mechanism: UNKNOWN
backup execution/result: UNKNOWN
backup artifact location: UNKNOWN
retention effectiveness: UNKNOWN
restore verification: UNKNOWN
integrity verification: UNKNOWN
RPO: UNKNOWN
RTO: RTO_UNKNOWN
```

And:

```text
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

Do not classify VMID 108 as stale or an RPO violation from timestamp age alone. No accepted RPO/freshness target exists.

## Exact next action — live acceptance gate

Run the full repository suite and the bounded live gate on `mgmt-automation`.

The gate must:

1. verify the active branch/package;
2. run the full repository tests;
3. observe only the eight accepted Kubernetes PostgreSQL relationships and the three K3s node-to-PVE VM mappings;
4. never read Kubernetes Secret values, Pod env values, PV backing paths, CSI handles, VM config, database data, credentials, or raw backup contents;
5. byte-verify the two accepted VM source artifacts using their recorded SHA256 values;
6. derive VM Backup Assurance v0.2 from those accepted sources;
7. derive PostgreSQL infrastructure recovery context v0.1;
8. validate the output schema;
9. print only bounded safe summary fields.

Expected result if live state is unchanged:

```text
instances_total: 8
infrastructure_recovery_observed: 8
infrastructure_recovery_unknown: 0
infrastructure_recovery_failed_to_observe: 0
underlying_vm_last_successful_backup_observed: 8
postgresql_protection_unknown: 8
postgresql_backup_mechanism_unknown: 8
postgresql_backup_execution_unknown: 8
postgresql_restore_verification_unknown: 8
postgresql_integrity_verification_unknown: 8
postgresql_rpo_unknown: 8
postgresql_rto_unknown: 8
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
schema: PASS
```

Do not force expected values if live evidence differs.

## PVE credential/runtime boundary

The existing BM2 credential remains discovery-only: broad/admin-like, env file mode `0644`, TLS verification false. Runtime PVE collection remains blocked until a separate least-privilege observer identity and trusted TLS path are accepted.

PVE collection remains manual-only. There is no PBS today.

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
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, or raw dump contents enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
