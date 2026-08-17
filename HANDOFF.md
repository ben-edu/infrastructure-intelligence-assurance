# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #56: 1a056f0adb98a05dab5c7795ded70439861c4f6e
active branch: docs/m5-read-only-checkpoint-gap-register
package on accepted main: 0.27.0
Milestone 5: ACTIVE — NOT COMPLETE
mutation_allowed: false
management host: mgmt-automation
Kubernetes cluster: k3s-main
PVE source: pve-bm2 / delfan
```

PVE collection remains manual-only. Existing PVE credentials remain discovery-only and `runtime_credential_approved=false`.

## Stable Milestone 5 evidence

### VM / PVE

```text
VM assets: 12
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
strict successful VZDUMP task correlations: 9
historical execution provenance: PROVENANCE_NOT_EXPLICITLY_RETURNED 9/9
current declared PVE backup jobs: 0
accepted recovery-point storage target: local
storage type: dir
backup content enabled: true
retention declaration: prune-backups=keep-all=1
protection: UNKNOWN
retention effectiveness: UNKNOWN
failure-domain independence: UNKNOWN
restore/integrity/RPO/RTO: UNKNOWN
unprotected_claims: 0
```

Accepted source hashes:

```text
/tmp/vm-backup-assurance.json
14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a

/tmp/proxmox-ve-backup-task-results.json
18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
```

### PVC

PR #51 merged at `e41d3efaabdeaec1dd5861e786b1f3946d426e00`.

```text
repository tests: 328 passed
PVC assets: 37
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
```

PVC recovery is infrastructure recovery context only, not application/database-consistent protection.

### PostgreSQL

```text
Kubernetes PostgreSQL instances: 8
infrastructure_recovery_observed: 8
Kubernetes database-aware backup mechanism: UNKNOWN 8/8
management-host PostgreSQL -> PVE VMID 109
management-host infrastructure recovery: OBSERVED
management-host pg_basebackup/pg_dump/pg_dumpall: PRESENT
management-host configured PostgreSQL backup mechanism: UNKNOWN
matching Kubernetes PostgreSQL backup CronJobs/Jobs: 0
successful database-aware backup claims: 0
unprotected_claims: 0
rpo_violation_claims: 0
```

Report:
`docs/reports/2026-08-17-m5-postgresql-database-backup-source-discovery.md`

### MariaDB

```text
accepted candidates: 4
persistence_observed: 3
persistence_unknown: 1
infrastructure_recovery_observed: 3
infrastructure_recovery_unknown: 1
database-aware backup mechanism: UNKNOWN 4/4
matching Kubernetes MariaDB backup CronJobs/Jobs: 0
management-host configured MariaDB backup mechanism: UNKNOWN
successful database-aware backup claims: 0
unprotected_claims: 0
rpo_violation_claims: 0
```

Report:
`docs/reports/2026-08-17-m5-mariadb-database-backup-source-discovery.md`

## Milestone 5 read-only checkpoint

Checkpoint report on the active branch:

```text
docs/reports/2026-08-17-m5-read-only-checkpoint-gap-register.md
```

The checkpoint distinguishes:

```text
OBSERVED
DECLARED
NOT_OBSERVED_IN_BOUNDED_SCOPE
UNKNOWN
REQUIRED LIVE VERIFICATION
REQUIRES FUTURE CONTROLLED MUTATION
```

Milestone 5 is not complete against the Project Source roadmap.

Open roadmap items:

```text
PBS / external backup targets beyond current observed PVE local storage scope
failure-domain assurance beyond same-PVE-storage relationship
retention effectiveness
accepted RPO/RTO targets and evaluation
restore tests / verified recovery exercises
```

Restore tests and recovery exercises are intentionally deferred while infrastructure interaction remains read-only.

## Exact next step

Start bounded **recovery-objective declaration discovery**.

Goal: find an authoritative declared-state source for explicit RPO/RTO targets without reading secrets or mutating infrastructure.

Do not evaluate backup age against an assumed target.

If no authoritative RPO/RTO declaration is found in the bounded safe source scope:

```text
RPO target: UNKNOWN
RTO target: UNKNOWN
RPO result: UNKNOWN
RTO result: UNKNOWN
```

Then move to bounded external-backup-target discovery.

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
