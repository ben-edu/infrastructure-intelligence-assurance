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
accepted main after PR #55: f0b97871d4fa60551d45c65a3883ccee72ca6b7c
active branch: agent/m5-mariadb-database-backup-source-discovery
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

```text
VM assets: 12
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
protection UNKNOWN: 12
restore/integrity/failure-domain/RPO/RTO: UNKNOWN
unprotected_claims: 0
```

Accepted strict last-success timestamps:

```text
100 -> 2026-05-08T06:15:18Z
101 -> 2026-05-08T10:38:50Z
106 -> 2026-08-14T16:39:53Z
107 -> 2026-08-14T17:39:32Z
108 -> 2026-04-15T12:36:38Z
109 -> 2026-04-13T10:36:41Z
```

Accepted source hashes:

```text
/tmp/vm-backup-assurance.json
14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a

/tmp/proxmox-ve-backup-task-results.json
18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
```

### PVC Infrastructure Recovery Context v0.1

PR #51 merged at `e41d3efaabdeaec1dd5861e786b1f3946d426e00`.

```text
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

This is infrastructure recovery context only, not application/database-consistent protection.

### Database infrastructure recovery

```text
PostgreSQL Kubernetes instances: 8
PostgreSQL infrastructure_recovery_observed: 8
PostgreSQL protection_unknown: 8

Management-host PostgreSQL -> PVE VMID 109
local PostgreSQL infrastructure recovery: OBSERVED

MariaDB candidates: 4
MariaDB persistence_observed: 3
MariaDB persistence_unknown: 1
MariaDB infrastructure_recovery_observed: 3
MariaDB infrastructure_recovery_unknown: 1
MariaDB protection_unknown: 4
```

### PVE policy, provenance, and retention

```text
current declared PVE backup jobs: 0
selected VMIDs without declared job scope: 12/12
historical strict successful VZDUMP tasks: 9
historical execution provenance: PROVENANCE_NOT_EXPLICITLY_RETURNED 9/9
accepted recovery-point storage target: local
storage type: dir
backup content enabled: true
storage retention declaration: prune-backups=keep-all=1
retention effectiveness: UNKNOWN
```

Current job absence does not invalidate historical successful VZDUMP evidence.

### PostgreSQL database-aware backup source discovery

Report:

```text
docs/reports/2026-08-17-m5-postgresql-database-backup-source-discovery.md
```

Accepted result:

```text
Kubernetes PostgreSQL workloads observed: 8/8
declared backup signal: 0/8
matching Kubernetes backup CronJobs/Jobs: 0
management-host pg_basebackup/pg_dump/pg_dumpall: PRESENT
management-host configured PostgreSQL backup mechanism: UNKNOWN
Kubernetes PostgreSQL database backup mechanism: UNKNOWN 8/8
successful database-aware backup claims: 0
unprotected_claims: 0
rpo_violation_claims: 0
```

### MariaDB database-aware backup source discovery

Report:

```text
docs/reports/2026-08-17-m5-mariadb-database-backup-source-discovery.md
```

Accepted live result:

```text
safety regression tests: 2 passed
expected_kubernetes_mariadb_candidates: 4
kubernetes_candidates_observed: 4
kubernetes_candidates_failed_to_observe: 0
kubernetes_candidates_with_declared_backup_signal: 0
kubernetes_candidates_database_backup_mechanism_unknown: 4
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

No MariaDB/MySQL-compatible backup tools, matching systemd units/timers, cron filenames, backup sidecars/init containers, backup-oriented ConfigMap signals, or matching CronJobs/Jobs were observed in the bounded safe source scope.

Accepted state:

```text
MariaDB database-aware backup mechanism: UNKNOWN 4/4
successful database-aware backup execution: UNKNOWN
artifact validity: UNKNOWN
retention effectiveness: UNKNOWN
restore verification: UNKNOWN
RPO/RTO: UNKNOWN
```

Bounded signal absence is not `UNPROTECTED`.

## Milestone 5 status

Milestone 5 is **not complete** against the Project Source roadmap. The current read-only source-discovery lanes for PostgreSQL and MariaDB are closed at `DATABASE_BACKUP_MECHANISM_UNKNOWN`; stronger conclusions would require new authoritative evidence or crossing a currently prohibited boundary.

Open roadmap items remain:

```text
PBS / external backup targets beyond current observed PVE local storage scope
failure-domain assurance beyond same-PVE-storage relationship
retention effectiveness
accepted RPO/RTO targets and evaluation
restore tests / verified recovery exercises
```

Restore tests and any controlled recovery exercise are intentionally deferred while the infrastructure boundary remains read-only.

## Exact next step

Create a bounded Milestone 5 read-only checkpoint/gap register from accepted evidence. Do not declare the milestone complete.

The checkpoint must state:

```text
what is OBSERVED
what is DECLARED
what remains UNKNOWN
what was NOT_OBSERVED_IN_BOUNDED_SCOPE
what requires live verification
what requires future controlled mutation
```

Then choose the next smallest read-only evidence slice. Prefer recovery-objective declaration discovery (RPO/RTO targets) or external-backup-target discovery only if an authoritative source can be inspected without secrets or mutation.

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance remain separate;
- declared backup policy is not observed backup success;
- storage retention declaration is not retention effectiveness;
- infrastructure recovery evidence is not application/database-consistent backup evidence;
- source-scoped negative evidence is not universal absence;
- tool presence is capability, not configured backup execution;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- stale/current/unknown semantics remain explicit;
- no RPO violation is inferred without an accepted target;
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, dump data, or WAL contents enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
