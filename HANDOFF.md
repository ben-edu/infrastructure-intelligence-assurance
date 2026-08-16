# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live/discovery report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Stable checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
main after accepted PR #47: cc0b8f36bc889a86cdd0181b90f48f8b21bc1da2
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

VM Backup Assurance v0.2 remains `STRICT_CORRELATION_ONLY` and accepts only `STRICT_SUCCESS_TASK_MATCH` evidence.

```text
assets: 12
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
protection UNKNOWN: 12
restore/integrity/failure-domain/RPO/RTO: UNKNOWN
unprotected_claims: 0
```

Relevant accepted VM timestamps:

```text
106 -> 2026-08-14T16:39:53Z
107 -> 2026-08-14T17:39:32Z
108 -> 2026-04-15T12:36:38Z
109 -> 2026-04-13T10:36:41Z
```

Accepted input artifacts:

```text
/tmp/vm-backup-assurance.json
sha256: 14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a

/tmp/proxmox-ve-backup-task-results.json
sha256: 18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
```

### Accepted PVE storage relationship

All 12 selected VMs resolved primary storage ID `local` and selected backup storage ID `local`.

This is logical storage-ID evidence only. Physical failure-domain independence remains `UNKNOWN`.

## Accepted PostgreSQL context

ADR:

```text
docs/decisions/0026-distinguish-postgresql-infrastructure-recovery-from-database-backup.md
```

PR #46 merged at:

```text
74a3c270e411a3823bd692abeb66e9fb3b6b6c04
```

Eight Kubernetes PostgreSQL workloads have accepted infrastructure recovery context:

```text
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
```

The management-host PostgreSQL instance on `mgmt-automation` is also related by in-memory DMI/SMBIOS UUID correlation to:

```text
PVE guest: mgmt-automation-01
VMID: 109
PVE node: delfan
VM LAST_SUCCESSFUL_BACKUP: OBSERVED
latest: 2026-04-13T10:36:41Z
strict_success_task_evidence: true
local_postgresql_infrastructure_recovery_status: OBSERVED
```

PR #47 merged at:

```text
cc0b8f36bc889a86cdd0181b90f48f8b21bc1da2
```

PostgreSQL database-aware protection, mechanism, execution/result, artifact location, retention, restore, integrity, RPO, and RTO remain unknown.

## Accepted MariaDB/MySQL-compatible source discovery

Report:

```text
docs/reports/2026-08-16-m5-mariadb-backup-recovery-source-discovery.md
```

Observed Kubernetes candidates:

```text
bookstack/Deployment/mariadb
  image: mariadb:10.11
  PVC: mariadb-data / Bound / local-path
  storage node: k3s-worker-02

misp/Deployment/mariadb
  image: mariadb:10.5
  PVC: mariadb-pvc / Bound / local-path
  storage node: k3s-master-01

misp/Deployment/mariadb-v2
  image: mariadb:10.5
  PVC: NONE_OBSERVED
  persistence status: UNKNOWN in inspected safe scope

moodle/StatefulSet/moodle-mariadb
  image: docker.io/bitnamilegacy/mariadb:12.0.2-debian-12-r0
  PVC: data-moodle-mariadb-0 / Bound / local-path
  storage node: k3s-worker-02
```

Summary:

```text
candidate workloads: 4
persistence observed: 3
persistence unknown: 1
matching backup/MariaDB CronJobs: 0
matching backup/MariaDB Jobs: 0
```

The zero CronJob/Job matches are bounded negative evidence only and are not `UNPROTECTED` claims.

Accepted infrastructure mappings relevant to persistent MariaDB candidates:

```text
k3s-master-01 -> VMID 106 -> VM LAST_SUCCESSFUL_BACKUP=OBSERVED -> 2026-08-14T16:39:53Z
k3s-worker-02 -> VMID 108 -> VM LAST_SUCCESSFUL_BACKUP=OBSERVED -> 2026-04-15T12:36:38Z
```

Therefore bounded infrastructure-level recovery context is available for:

```text
misp/Deployment/mariadb -> VMID 106
bookstack/Deployment/mariadb -> VMID 108
moodle/StatefulSet/moodle-mariadb -> VMID 108
```

No infrastructure-recovery promotion is accepted for `misp/Deployment/mariadb-v2` because no persistent PVC relationship was observed.

Management-host discovery found no local MariaDB/MySQL server or backup tooling in the inspected scope.

MariaDB-consistent backup, backup mechanism, execution/result, artifact location, retention, restore verification, integrity verification, RPO, and RTO remain unknown.

## Exact next step — MariaDB infrastructure recovery context v0.1

Implement a pure derived, read-only context for all four observed Kubernetes MariaDB-compatible candidates.

Do not add a new live database collector or runtime/systemd wiring.

Expected conservative semantics if live state is unchanged:

```text
instances_total: 4
persistence_observed: 3
persistence_unknown: 1
infrastructure_recovery_observed: 3
infrastructure_recovery_unknown: 1
underlying_vm_last_successful_backup_observed: 3
mariadb_protection_unknown: 4
mariadb_backup_mechanism_unknown: 4
mariadb_backup_execution_unknown: 4
mariadb_restore_verification_unknown: 4
mariadb_integrity_verification_unknown: 4
mariadb_rpo_unknown: 4
mariadb_rto_unknown: 4
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

`misp/mariadb-v2` must remain `UNKNOWN`, not `UNPROTECTED`, unless a separate authoritative source proves absence of required protection.

A VM backup timestamp must not be interpreted as MariaDB-consistent backup, stale backup, or RPO violation without a MariaDB-specific authoritative mechanism and accepted policy target.

## Milestone 5 gaps still open

```text
PostgreSQL database-aware backup evidence
MariaDB database-aware backup evidence
PVC assurance beyond foundation
PBS (future)
external backup targets
failure-domain assurance beyond storage-ID relationship
retention effectiveness
RPO/RTO
restore tests
```

## Later roadmap

After Milestone 5:

```text
Milestone 6: IaC Governance
Milestone 7: Operational Intelligence Layer
Milestone 8: Reliability and Hardening
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
