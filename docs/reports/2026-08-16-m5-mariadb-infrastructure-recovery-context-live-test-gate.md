# Milestone 5 MariaDB Infrastructure Recovery Context Live Test Gate — 2026-08-16

## Status

Pending live acceptance on `mgmt-automation`.

## Implementation under test

```text
branch: feature/m5-mariadb-infrastructure-recovery-context
package: 0.26.0
mariadb_infrastructure_recovery_context_version: 0.1
mutation_allowed: false
```

Files:

```text
src/infra_assurance/mariadb_infrastructure_recovery_context.py
schemas/mariadb-infrastructure-recovery-context.schema.json
tests/test_mariadb_infrastructure_recovery_context.py
tests/test_mariadb_infrastructure_recovery_context_wiring.py
scripts/live_gates/m5_mariadb_infrastructure_recovery_context.py
```

## Accepted discovery baseline

```text
candidate workloads: 4
persistent relationships observed: 3
persistent relationship unknown: 1
matching MariaDB/backup CronJobs: 0
matching MariaDB/backup Jobs: 0
```

Infrastructure mappings:

```text
misp/Deployment/mariadb -> k3s-master-01 -> VMID 106
bookstack/Deployment/mariadb -> k3s-worker-02 -> VMID 108
moodle/StatefulSet/moodle-mariadb -> k3s-worker-02 -> VMID 108
misp/Deployment/mariadb-v2 -> persistence UNKNOWN -> infrastructure recovery UNKNOWN
```

Accepted VM timestamps:

```text
106 -> 2026-08-14T16:39:53Z
108 -> 2026-04-15T12:36:38Z
```

## Acceptance criteria

The full repository suite must pass and the manual live gate must validate the strict schema.

Expected counters if live state is unchanged:

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
```

A changed live state must fail closed for review rather than being forced to these counters.

## Trust boundary

Even when infrastructure recovery is `OBSERVED`, this gate does not establish MariaDB-consistent backup, backup execution/result, retention, restore verification, integrity verification, RPO, or RTO.

The persistence-unknown `misp/mariadb-v2` candidate must not be classified `UNPROTECTED`.

Timestamp age alone must not produce `BACKUP_STALE` or `RPO_VIOLATION` without an accepted MariaDB-specific target.

## Safety

The gate is manual and read-only.

It must not project Kubernetes Secret values, environment values, container commands/args, PV backing paths, CSI handles, database data, dump contents, raw PVE VM config, disk/network details, or credentials.

No infrastructure mutation is allowed.

## Acceptance evidence

Pending live execution.
