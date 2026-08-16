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
accepted main checkpoint after PR #48: 460f72320071291c3eeecd95a89c99cc5e1fe656
active branch: feature/m5-mariadb-infrastructure-recovery-context
package on active branch: 0.26.0
Milestone 5: active
mutation_allowed: false
management host: mgmt-automation
Kubernetes cluster: k3s-main
PVE source: pve-bm2 / delfan
```

The MariaDB infrastructure recovery context slice is implemented but not accepted until the full repository suite and manual live gate pass.

Active files:

```text
src/infra_assurance/mariadb_infrastructure_recovery_context.py
schemas/mariadb-infrastructure-recovery-context.schema.json
tests/test_mariadb_infrastructure_recovery_context.py
tests/test_mariadb_infrastructure_recovery_context_wiring.py
scripts/live_gates/m5_mariadb_infrastructure_recovery_context.py
docs/milestone-5-mariadb-infrastructure-recovery-context.md
docs/reports/2026-08-16-m5-mariadb-infrastructure-recovery-context-live-test-gate.md
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

### Accepted PVE storage relationship

All 12 selected VMs resolved primary storage ID `local` and selected backup storage ID `local`.

This is logical storage-ID evidence only. Physical failure-domain independence remains `UNKNOWN`.

## Accepted PostgreSQL context

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
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

The management-host PostgreSQL instance is related to PVE VMID 109 with accepted strict VM last-successful-backup evidence. PR #47 merged at:

```text
cc0b8f36bc889a86cdd0181b90f48f8b21bc1da2
```

PostgreSQL database-aware backup mechanism, execution/result, artifact location, retention, restore, integrity, RPO, and RTO remain unknown.

## Accepted MariaDB/MySQL-compatible discovery

PR #48 merged at:

```text
460f72320071291c3eeecd95a89c99cc5e1fe656
```

Report:

```text
docs/reports/2026-08-16-m5-mariadb-backup-recovery-source-discovery.md
```

Accepted discovery state:

```text
bookstack/Deployment/mariadb
  persistence: OBSERVED
  storage node: k3s-worker-02
  VMID: 108

misp/Deployment/mariadb
  persistence: OBSERVED
  storage node: k3s-master-01
  VMID: 106

misp/Deployment/mariadb-v2
  persistence: UNKNOWN
  infrastructure recovery: UNKNOWN

moodle/StatefulSet/moodle-mariadb
  persistence: OBSERVED
  storage node: k3s-worker-02
  VMID: 108
```

Bounded backup signals:

```text
matching MariaDB/backup CronJobs: 0
matching MariaDB/backup Jobs: 0
```

The zero matches are bounded negative evidence only and are not `UNPROTECTED` claims.

Accepted VM recovery evidence relevant to persistent MariaDB candidates:

```text
VMID 106 -> LAST_SUCCESSFUL_BACKUP=OBSERVED -> 2026-08-14T16:39:53Z
VMID 108 -> LAST_SUCCESSFUL_BACKUP=OBSERVED -> 2026-04-15T12:36:38Z
```

MariaDB database-aware protection, backup mechanism, execution/result, artifact location, retention, restore verification, integrity verification, RPO, and RTO remain unknown.

## Active slice — MariaDB infrastructure recovery context v0.1

The implementation is pure derivation. It adds no runtime/systemd wiring and no database connection.

Promotion rule:

```text
MariaDB-compatible workload OBSERVED
+ persistent PVC OBSERVED
+ PV storage node OBSERVED
+ Kubernetes node -> PVE VMID OBSERVED
+ accepted VM LAST_SUCCESSFUL_BACKUP OBSERVED
+ STRICT_SUCCESS_TASK_MATCH evidence
= infrastructure_recovery OBSERVED
```

Missing persistence remains `UNKNOWN`, not `UNPROTECTED`.

The strict schema fixes MariaDB-specific assurance to:

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

## Exact next action — live acceptance gate

Run the full repository suite and the manual bounded gate on `mgmt-automation`:

```text
scripts/live_gates/m5_mariadb_infrastructure_recovery_context.py
```

Expected counters if live state remains unchanged:

```text
instances_total: 4
persistence_observed: 3
persistence_unknown: 1
persistence_failed_to_observe: 0
infrastructure_recovery_observed: 3
infrastructure_recovery_unknown: 1
infrastructure_recovery_failed_to_observe: 0
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
schema: PASS
```

Do not force these values if live evidence differs. Fail closed and review the observed change.

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
