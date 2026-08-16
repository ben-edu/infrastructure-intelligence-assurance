# Milestone 5 MariaDB Infrastructure Recovery Context Live Test Gate — 2026-08-16

## Status

Accepted on `mgmt-automation` after the manual read-only live gate.

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

## Repository gate

```text
305 passed in 1.16s
repository gate: PASS
```

## Live relationship evidence

```text
candidate_containers: 4
PVE GET /cluster/resources?type=vm: HTTP 200
runtime_credential_approved: false
```

Observed relationships:

```text
bookstack/Deployment/mariadb
  persistence: OBSERVED
  pvc: mariadb-data
  storage node: k3s-worker-02
  VMID: 108

misp/Deployment/mariadb
  persistence: OBSERVED
  pvc: mariadb-pvc
  storage node: k3s-master-01
  VMID: 106

misp/Deployment/mariadb-v2
  persistence: UNKNOWN
  pvc: UNKNOWN
  storage node: UNKNOWN
  VMID: UNKNOWN

moodle/StatefulSet/moodle-mariadb
  persistence: OBSERVED
  pvc: data-moodle-mariadb-0
  storage node: k3s-worker-02
  VMID: 108
```

Accepted VM source verification:

```text
/tmp/vm-backup-assurance.json: hash_match=true
/tmp/proxmox-ve-backup-task-results.json: hash_match=true
```

## Accepted derived context

```text
schema: PASS
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
accepted_vm_timestamps_match: true
acceptance_counters_match: true
gate_rc: 0
```

Instance-level accepted timestamps:

```text
bookstack/Deployment/mariadb -> VMID 108 -> 2026-04-15T12:36:38Z
misp/Deployment/mariadb -> VMID 106 -> 2026-08-14T16:39:53Z
misp/Deployment/mariadb-v2 -> UNKNOWN
moodle/StatefulSet/moodle-mariadb -> VMID 108 -> 2026-04-15T12:36:38Z
```

## Trust boundary

`OBSERVED` infrastructure recovery means a persistent MariaDB-compatible workload was related to a PVE VM with accepted strict VM last-successful-backup evidence.

It does not establish MariaDB-consistent backup, database backup execution/result, restore verification, integrity, retention, RPO, or RTO assurance.

The persistence-unknown `misp/mariadb-v2` candidate is not classified `UNPROTECTED`.

Timestamp age alone does not produce `BACKUP_STALE` or `RPO_VIOLATION` without an accepted MariaDB-specific target.

## Safety

No Kubernetes Secret values, environment values, container commands/args, PV backing paths, CSI handles, database rows, dumps, raw PVE VM config, disks, networks, or credentials were projected.

No infrastructure mutation was performed.
