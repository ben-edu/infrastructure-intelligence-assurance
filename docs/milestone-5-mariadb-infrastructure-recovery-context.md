# Milestone 5 — MariaDB Infrastructure Recovery Context v0.1

## Purpose

Derive a bounded recovery context for the four observed Kubernetes MariaDB/MySQL-compatible workload candidates by joining safe workload/persistence relationships with accepted VM last-successful-backup evidence.

This slice is infrastructure context only. It does not establish MariaDB-consistent backup protection.

## Inputs

```text
mariadb_infrastructure_relationship_evidence_version: 0.1
vm_backup_assurance_version: 0.2
```

Accepted VM evidence must use:

```text
mode: STRICT_CORRELATION_ONLY
basis: STRICT_SUCCESS_TASK_MATCH
```

## Scope

Observed discovery scope:

```text
bookstack/Deployment/mariadb
misp/Deployment/mariadb
misp/Deployment/mariadb-v2
moodle/StatefulSet/moodle-mariadb
```

Expected persistence state from the accepted 2026-08-16 discovery:

```text
OBSERVED: 3
UNKNOWN: 1
```

`misp/Deployment/mariadb-v2` remains `UNKNOWN` because no persistent PVC relationship was observed in the bounded safe scope. This is not an `UNPROTECTED` claim.

## Promotion rule

Infrastructure recovery becomes `OBSERVED` only when all required edges are observed:

```text
MariaDB-compatible workload
-> persistent PVC
-> explicit PV storage node
-> Kubernetes node to PVE VMID mapping
-> accepted VM LAST_SUCCESSFUL_BACKUP=OBSERVED
-> STRICT_SUCCESS_TASK_MATCH evidence
```

Any missing persistence or mapping edge remains `UNKNOWN`. Failed observation remains explicit `FAILED_TO_OBSERVE`.

## Database assurance boundary

The schema structurally fixes these MariaDB-specific dimensions to unknown:

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

And fixes:

```text
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

The VMID 108 timestamp must not be classified stale or as an RPO violation without an accepted MariaDB-specific target.

## Runtime boundary

The derivation module is pure and has no live infrastructure access.

The reusable live gate is manual-only and reuses the accepted bounded MariaDB discovery projections. It is not systemd-wired.

No database connection, backup execution, restore execution, Secret/env projection, or infrastructure mutation is introduced.
