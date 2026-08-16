# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live/discovery report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Stable checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
main after accepted PR #46: 74a3c270e411a3823bd692abeb66e9fb3b6b6c04
package: 0.25.0
Milestone 5: active
mutation_allowed: false
management host: mgmt-automation
Kubernetes cluster: k3s-main
PVE source: pve-bm2 / delfan
```

PVE collection remains manual-only. Existing PVE credentials remain discovery-only and `runtime_credential_approved=false`.

## Stable Milestone 5 evidence

### Kubernetes PVC foundation

```text
PVC assets: 37
protection UNKNOWN: 37
unprotected_claims: 0
```

### Accepted VM recovery evidence

Accepted VM Backup Assurance v0.2 uses `STRICT_CORRELATION_ONLY` and accepts only `STRICT_SUCCESS_TASK_MATCH` evidence.

```text
assets: 12
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
109 -> 2026-04-13T10:36:41Z
```

Accepted source inputs:

```text
/tmp/vm-backup-assurance.json
sha256: 14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a

/tmp/proxmox-ve-backup-task-results.json
sha256: 18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
```

### Accepted PVE VM storage relationship

All 12 selected VMs resolved primary storage ID `local` and selected backup storage ID `local`.

This is logical storage-ID evidence only. It does not establish physical failure-domain independence. `BACKUP_FAILURE_DOMAIN` remains `UNKNOWN`.

## Accepted PostgreSQL discovery and context

Trust decision:

```text
docs/decisions/0026-distinguish-postgresql-infrastructure-recovery-from-database-backup.md
```

### Kubernetes PostgreSQL

Eight persistent workloads are accepted in scope:

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

Accepted infrastructure relationships:

```text
keycloak              -> k3s-master-01 -> VMID 106
fastapi-platform      -> k3s-worker-01 -> VMID 107
fastapi-platform-dev  -> k3s-worker-01 -> VMID 107
openproject           -> k3s-worker-01 -> VMID 107
soria-prospecting     -> k3s-worker-01 -> VMID 107
toilettage            -> k3s-worker-01 -> VMID 107
drfarah-staging       -> k3s-worker-02 -> VMID 108
soria-academie        -> k3s-worker-02 -> VMID 108
```

PR #46 accepted PostgreSQL infrastructure recovery context v0.1 and merged at:

```text
74a3c270e411a3823bd692abeb66e9fb3b6b6c04
```

Accepted live gate:

```text
repository tests: 292 passed in 1.23s
instances_total: 8
infrastructure_recovery_observed: 8
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
gate_rc: 0
```

This is infrastructure recovery context only, not PostgreSQL-consistent backup evidence.

### Management-host PostgreSQL

Observed service/tooling:

```text
postgresql@15-main.service: active/running
pg_dump/pg_dumpall/pg_basebackup/pg_receivewal 15.19: present
pgBackRest/Barman/barman-cloud-backup/WAL-G: not observed in inspected command scope
configured pg_basebackup@ systemd instance: not observed
```

Accepted infrastructure identity discovery on 2026-08-16:

```text
local host: mgmt-automation
virtualization: kvm
local DMI UUID compared in memory only
bounded PVE QEMU candidates: 12
config_complete: 12
explicit SMBIOS UUID candidates: 12
uuid_matches: 1
identity_status: OBSERVED
identity_basis: LOCAL_DMI_UUID_EQUALS_PVE_SMBIOS_UUID
PVE guest: mgmt-automation-01
PVE VMID: 109
PVE node: delfan
runtime status: running
```

Accepted VM recovery correlation:

```text
vmid_in_accepted_vm_assurance: true
vm_last_successful_backup_status: OBSERVED
vm_last_successful_backup_at: 2026-04-13T10:36:41Z
strict_success_task_evidence: true
vm_protection_status: UNKNOWN
vm_restore_verification_status: UNKNOWN
vm_integrity_verification_status: UNKNOWN
vm_rpo_status: UNKNOWN
vm_rto_status: RTO_UNKNOWN
local_postgresql_infrastructure_recovery_status: OBSERVED
```

Report:

```text
docs/reports/2026-08-16-m5-management-postgresql-infrastructure-relationship-discovery.md
```

The DMI/SMBIOS values were not printed or persisted. Only GET requests were used against PVE. No PostgreSQL connection or database read occurred.

The 2026-04-13 VM backup timestamp is not classified as stale or an RPO violation because no accepted PostgreSQL freshness/RPO target exists.

Database-aware PostgreSQL backup mechanism, execution/result, artifact location, retention, restore, integrity, RPO, and RTO remain unknown.

## Exact next step — bounded MariaDB backup/recovery discovery

Start a new source family rather than further extending PostgreSQL infrastructure correlation.

Discovery first; do not implement a MariaDB assurance collector until authoritative evidence sources are identified.

Required questions:

```text
Which MariaDB/MySQL-compatible instances are actually in scope?
Which host, VM, or Kubernetes workload owns each instance?
What persistent storage relationship is observable?
What backup mechanism is declared or actually used?
What authoritative source proves execution/result?
Where are recovery artifacts stored?
Is retention observable?
Is restore/integrity verification observable?
Can infrastructure-level VM recovery evidence be joined without representing it as MariaDB-consistent backup?
What remains UNKNOWN or requires live verification?
```

Initial interactions remain read-only.

Do not expose database passwords, `.my.cnf` credentials, Kubernetes Secrets, raw environment values, connection strings, raw database rows, dump contents, private keys, raw PVE config, or sensitive storage paths.

Do not classify absence of a CronJob, Job, script, or tool as `UNPROTECTED`; keep source-scoped negative evidence bounded.

## Milestone 5 gaps still open

```text
PostgreSQL database-aware backup evidence
MariaDB backup/recovery evidence
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
