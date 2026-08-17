# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live/discovery report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #54: 2bf0dc829f819eec728bd2b45ee9912d34e24cfe
active branch: agent/m5-postgresql-database-backup-source-discovery
package on accepted main: 0.27.0
Milestone 5: active
mutation_allowed: false
management host: mgmt-automation
Kubernetes cluster: k3s-main
PVE source: pve-bm2 / delfan
```

PVE collection remains manual-only. Existing PVE credentials remain discovery-only and `runtime_credential_approved=false`.

## Stable Milestone 5 evidence

### VM recovery evidence

VM Backup Assurance last-success integration remains `STRICT_CORRELATION_ONLY` and accepts only `STRICT_SUCCESS_TASK_MATCH` evidence.

```text
assets: 12
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
protection UNKNOWN: 12
restore/integrity/failure-domain/RPO/RTO: UNKNOWN
unprotected_claims: 0
```

Accepted last-success timestamps:

```text
100 -> 2026-05-08T06:15:18Z
101 -> 2026-05-08T10:38:50Z
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

### PVC Infrastructure Recovery Context v0.1

PR #51 merged at `e41d3efaabdeaec1dd5861e786b1f3946d426e00`.

```text
package: 0.27.0
repository tests: 328 passed
assets_total: 37
infrastructure_recovery_observed: 37
underlying_vm_last_successful_backup_observed: 37
protection_unknown: 37
retention_effectiveness_unknown: 37
failure_domain_unknown: 37
restore_verification_unknown: 37
rpo_unknown: 37
rto_unknown: 37
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
gate_rc: 0
```

This remains infrastructure recovery context only, not application/database-consistent protection.

### Database infrastructure recovery contexts

```text
PostgreSQL Kubernetes instances_total: 8
PostgreSQL infrastructure_recovery_observed: 8
PostgreSQL protection_unknown: 8

Management-host PostgreSQL: mgmt-automation -> PVE VMID 109
local PostgreSQL infrastructure recovery: OBSERVED

MariaDB instances_total: 4
MariaDB persistence_observed: 3
MariaDB persistence_unknown: 1
MariaDB infrastructure_recovery_observed: 3
MariaDB infrastructure_recovery_unknown: 1
MariaDB protection_unknown: 4
```

## Accepted PVE policy / provenance / retention discoveries

Current PVE `/cluster/backup` source is complete and returned zero declared backup jobs for the selected 12 VMIDs. Historical successful VZDUMP evidence remains valid.

Historical provenance discovery over the nine accepted strict successful tasks returned:

```text
PROVENANCE_NOT_EXPLICITLY_RETURNED: 9/9
scheduled/manual/external provenance observed: 0
failed_to_observe: 0
```

Storage-level retention discovery accepted:

```text
accepted recovery-point storage target: local
storage type: dir
backup content enabled: true
disabled: false
retention declaration: prune-backups=keep-all=1
retention effectiveness: UNKNOWN
restore verification: UNKNOWN
RPO/RTO: UNKNOWN
```

PR #54 merged at:

```text
2bf0dc829f819eec728bd2b45ee9912d34e24cfe
```

## Accepted PostgreSQL database-aware backup source discovery

Report:

```text
docs/reports/2026-08-17-m5-postgresql-database-backup-source-discovery.md
```

Accepted bounded live result:

```text
safety regression tests: 2 passed
expected_kubernetes_postgresql_workloads: 8
kubernetes_workloads_observed: 8
kubernetes_workloads_failed_to_observe: 0
kubernetes_workloads_with_declared_backup_signal: 0
kubernetes_workloads_database_backup_mechanism_unknown: 8
matching_kubernetes_cronjobs_jobs: 0
management_host_configured_backup_signal: 0
backup_execution_success_claims: 0
backup_artifact_validity_claims: 0
retention_effectiveness_claims: 0
restore_verification_claims: 0
unprotected_claims: 0
rpo_violation_claims: 0
discovery_rc: 0
```

For all eight accepted Kubernetes PostgreSQL workloads, safe metadata showed no backup sidecar/init/configmap signal. The complete bounded CronJob/Job source returned zero PostgreSQL backup matches.

Management-host PostgreSQL backup-capable tooling is observed:

```text
pg_basebackup: PRESENT
pg_dump: PRESENT
pg_dumpall: PRESENT
```

Specialized tooling was not observed in the inspected executable scope:

```text
pgBackRest: NOT_PRESENT
Barman: NOT_PRESENT
barman-cloud-backup: NOT_PRESENT
WAL-G / walg: NOT_PRESENT
```

Systemd source is complete and package/template units exist:

```text
pg_basebackup@.service
pg_basebackup@.timer
pg_dump@.service
pg_dump@.timer
```

But no instantiated matching unit, active matching timer, or matching cron filename was observed.

Accepted semantics:

```text
Kubernetes PostgreSQL database-aware backup mechanism: UNKNOWN for 8/8
management-host backup-capable tooling: OBSERVED
management-host configured PostgreSQL backup mechanism: UNKNOWN
successful database-aware backup execution: UNKNOWN
artifact validity: UNKNOWN
retention effectiveness: UNKNOWN
restore verification: UNKNOWN
RPO/RTO: UNKNOWN
```

Bounded signal absence is not `UNPROTECTED`.

## Exact next step — MariaDB database-aware backup source discovery

The PostgreSQL source-discovery lane has no stronger safe signal to pursue without crossing into database access, dump/WAL inspection, or configuration mutation. Close it at `DATABASE_BACKUP_MECHANISM_UNKNOWN` for the current read-only phase.

Next smallest Milestone 5 slice: perform equivalent bounded MariaDB/MySQL-compatible database-aware backup source discovery over the four already accepted MariaDB candidates.

Do not connect to MariaDB/MySQL, read database rows, create dumps, inspect backup contents, print Secret/env values, or mutate workloads/system state.

Bounded questions:

```text
For each of the 4 accepted MariaDB candidates, do current safe workload metadata expose backup sidecar/init containers or backup-oriented ConfigMap/PVC signals?
Do current Kubernetes CronJobs/Jobs expose MariaDB/MySQL-aware backup tooling or naming signals?
Is any configured database-aware mechanism observable without commands/args/env/Secret contents?
Which candidates remain DATABASE_BACKUP_MECHANISM_UNKNOWN?
```

Safe tooling/name signals may include `mariadb-dump`, `mysqldump`, `mariabackup`, `xtrabackup`, `mydumper`, and backup-oriented container/image names. Tool/name presence is mechanism metadata only, not execution success.

## Milestone 5 gaps still open

```text
MariaDB database-aware backup evidence
PBS (future)
external backup targets
failure-domain assurance beyond storage-ID relationship
retention effectiveness
RPO/RTO
restore tests
```

PostgreSQL database-aware mechanism remains unknown but its current bounded source-discovery path is closed for the read-only phase.

## Later roadmap

```text
Milestone 6: IaC Governance
Milestone 7: Operational Intelligence Layer
Milestone 8: Reliability and Hardening
```

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance remain separate;
- declared backup policy is not observed backup success;
- storage retention declaration is not retention effectiveness;
- current job absence does not determine historical execution provenance;
- task success does not establish provenance when provenance fields are absent;
- infrastructure recovery evidence is not application/database-consistent backup evidence;
- source-scoped negative evidence is not universal absence;
- tool presence is capability, not configured backup execution;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- observation credentials remain separate from control credentials;
- stale/current/unknown semantics remain explicit;
- no RPO violation is inferred without an accepted target;
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, dump data, or WAL contents enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
