# ADR 0026 — Distinguish PostgreSQL Infrastructure Recovery from Database Backup

## Status

Accepted.

Accepted from bounded read-only discovery evidence on 2026-08-16. This ADR defines the trust boundary for the next Milestone 5 slice; it does not accept a PostgreSQL backup collector or promote PostgreSQL backup protection.

## Context

Milestone 5 requires recovery assurance without replacing specialized backup tooling and without overstating incomplete evidence.

Read-only discovery identified eight persistent PostgreSQL workloads in Kubernetes. Each workload uses a Bound `local-path` PVC whose PV node affinity identifies one of three K3s nodes.

A bounded PVE lookup established the K3s node-to-VM relationship:

```text
k3s-master-01 -> VMID 106
k3s-worker-01 -> VMID 107
k3s-worker-02 -> VMID 108
```

Accepted VM Backup Assurance source artifacts establish `LAST_SUCCESSFUL_BACKUP=OBSERVED` for all three VMIDs:

```text
106 -> 2026-08-14T16:39:53Z
107 -> 2026-08-14T17:39:32Z
108 -> 2026-04-15T12:36:38Z
```

However, the accepted VM assurance deliberately keeps protection, restore verification, integrity verification, failure domain, RPO, and RTO unknown.

Kubernetes discovery found no matching PostgreSQL/backup CronJobs or Jobs in the inspected scope. Management-host discovery found PostgreSQL backup-capable client tooling and an uninstantiated packaged `pg_basebackup@` systemd template, but no configured template instance, PostgreSQL-specific cron file-name signal, local backup-script file-name signal, pgBackRest, Barman, or WAL-G.

No authoritative database-aware backup execution/result source has therefore been established.

## Decision

Treat the Kubernetes-to-PVE relationship as **infrastructure recovery context**, not PostgreSQL backup assurance.

The next implementation may derive a bounded relationship of the form:

```text
PostgreSQL workload
-> persistent PVC
-> explicit Kubernetes storage node
-> K3s VM
-> PVE VMID
-> accepted VM last-successful-backup evidence
```

That relationship may state that infrastructure-level recovery evidence is observed when every required source edge is observed and the joined VM has accepted `LAST_SUCCESSFUL_BACKUP=OBSERVED` evidence.

It must not state or imply any of the following without separate authoritative PostgreSQL-aware evidence:

```text
PostgreSQL backup protection is verified
PostgreSQL-consistent backup exists
PostgreSQL backup execution succeeded
PostgreSQL backup artifact is restorable
PostgreSQL integrity is verified
PostgreSQL restore is verified
PostgreSQL RPO is satisfied
PostgreSQL RTO is satisfied
```

For PostgreSQL-specific dimensions, absence of an accepted database-aware source remains `UNKNOWN` rather than `UNPROTECTED`.

The management-host PostgreSQL instance remains a separate discovery subject until a safe authoritative backup source or infrastructure-recovery relationship is established for it.

## Evidence semantics

The next bounded context must preserve source and derived-state separation.

Recommended semantic fields are conceptually equivalent to:

```text
instance_observation_status: OBSERVED | UNKNOWN | FAILED_TO_OBSERVE
persistence_status: OBSERVED | UNKNOWN | FAILED_TO_OBSERVE
infrastructure_recovery_relationship_status: OBSERVED | UNKNOWN | FAILED_TO_OBSERVE
underlying_vm_last_successful_backup_status: OBSERVED | UNKNOWN
underlying_vm_last_successful_backup_at: timestamp | null
postgresql_backup_mechanism_status: UNKNOWN
postgresql_backup_execution_status: UNKNOWN
postgresql_restore_verification_status: UNKNOWN
postgresql_integrity_verification_status: UNKNOWN
postgresql_rpo_status: UNKNOWN
postgresql_rto_status: RTO_UNKNOWN
```

Exact schema naming remains an implementation detail and may be revised during the next small vertical slice.

## Freshness and RPO

The VMID 108 successful backup timestamp is materially older than VMIDs 106 and 107, but no accepted PostgreSQL or infrastructure RPO target/freshness contract currently exists.

Therefore the next slice must not infer:

```text
STALE
BACKUP_STALE
RPO_VIOLATION
```

from timestamp age alone.

The timestamp is observed evidence. Its policy interpretation remains unknown until an accepted target exists.

## Source-scoped negative evidence

The following observations are bounded negatives only:

```text
matching Kubernetes backup/PostgreSQL CronJobs: 0
matching Kubernetes backup/PostgreSQL Jobs: 0
configured local pg_basebackup systemd instances: 0
PostgreSQL-specific local cron file-name signals: 0
local backup-script file-name signals: 0
```

They do not establish universal backup absence. External orchestration, different mechanisms, or uninspected scopes may exist.

## Safety boundary

The accepted discovery and next derived slice remain read-only.

Do not read or project:

```text
Kubernetes Secret values
PostgreSQL passwords
.pgpass content
secret environment values
complete sensitive connection strings
raw database contents
raw dump contents
raw PostgreSQL configuration
raw cron commands when credentials may be embedded
raw systemd arguments when credentials may be embedded
```

Do not execute backups, restores, WAL changes, retention changes, service restarts, or infrastructure mutations.

## Consequences

Positive:

- existing authoritative VM recovery evidence becomes useful to PostgreSQL operators without being mislabeled as database backup assurance;
- the platform can expose a complete infrastructure dependency chain for the eight Kubernetes PostgreSQL instances;
- database-aware unknowns remain explicit;
- future pgBackRest, Barman, WAL-G, PostgreSQL-native, operator-native, or external backup sources can be integrated separately without redesigning the infrastructure relationship.

Trade-off:

- PostgreSQL backup protection remains unknown even when the underlying VM has a successful VZDUMP recovery point;
- the platform intentionally withholds stronger claims until database-aware evidence exists.

## Follow-up

Implement one small read-only derived PostgreSQL infrastructure-recovery context for the eight Kubernetes PostgreSQL instances only.

Do not include the local `mgmt-automation` PostgreSQL instance in that first implementation unless an authoritative infrastructure relationship is established for it.
