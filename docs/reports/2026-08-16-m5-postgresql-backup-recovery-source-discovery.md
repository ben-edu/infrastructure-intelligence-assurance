# Milestone 5 PostgreSQL Backup and Recovery Source Discovery — 2026-08-16

## Status

Accepted discovery checkpoint. No PostgreSQL backup collector or assurance promotion is accepted by this report.

## Scope

Read-only discovery on `mgmt-automation`, Kubernetes context `default` for cluster `k3s-main`, and bounded Proxmox VE guest lookup for the three K3s nodes.

The purpose was to identify current PostgreSQL instances in accepted infrastructure scope and determine what backup/recovery evidence sources are actually observable without reading secrets, database data, raw sensitive configuration, or performing mutations.

## Kubernetes PostgreSQL instances

Eight persistent PostgreSQL database workload candidates were observed:

```text
drfarah-staging      StatefulSet/drfarah-staging-postgres  postgres:16-alpine
fastapi-platform      Deployment/postgres                  postgres:18
fastapi-platform-dev  Deployment/postgres                  postgres:18
keycloak              StatefulSet/keycloak-postgresql      bitnamilegacy/postgresql:17.4.0
openproject           StatefulSet/openproject-postgresql   bitnamilegacy/postgresql:15.4.0
soria-academie        StatefulSet/academie-postgres        postgres:16-alpine
soria-prospecting     Deployment/soria-postgres            postgres:16-alpine
toilettage            StatefulSet/toilettage-postgres      postgres:16-alpine
```

The earlier `soria-academie/academie-api-migrate` PostgreSQL-image match was classified as a job/helper candidate and excluded from the database-instance count.

All eight database candidates had a Bound PVC using the `local-path` StorageClass:

```text
drfarah-staging      5Gi   k3s-worker-02
fastapi-platform      10Gi  k3s-worker-01
fastapi-platform-dev  10Gi  k3s-worker-01
keycloak              8Gi   k3s-master-01
openproject           8Gi   k3s-worker-01
soria-academie        5Gi   k3s-worker-02
soria-prospecting     5Gi   k3s-worker-01
toilettage            5Gi   k3s-worker-01
```

The PV node affinity explicitly established the listed Kubernetes storage nodes. PVC presence and node affinity are persistence evidence only; they are not backup-protection evidence.

## Kubernetes backup-mechanism discovery

Within the bounded Kubernetes CronJob/Job discovery scope:

```text
matching PostgreSQL/backup CronJobs: 0
matching PostgreSQL/backup Jobs: 0
```

This is source-scoped negative evidence only. It does not establish universal absence of PostgreSQL backup orchestration because external schedulers, host-level tooling, sidecars, operators, or other mechanisms may exist outside the inspected object-name/image scope.

## Kubernetes node to PVE VM mapping

A bounded read-only Proxmox VE lookup established:

```text
k3s-master-01 -> VMID 106 -> running QEMU guest on delfan
k3s-worker-01 -> VMID 107 -> running QEMU guest on delfan
k3s-worker-02 -> VMID 108 -> running QEMU guest on delfan
```

The existing PVE discovery credential boundary remains unchanged:

```text
runtime_credential_approved: false
```

No VM config, disks, network values, credentials, or raw API payloads were persisted.

## Accepted VM recovery evidence join

The accepted local source artifacts were byte-verified before derivation:

```text
/tmp/vm-backup-assurance.json
sha256: 14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a

/tmp/proxmox-ve-backup-task-results.json
sha256: 18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
```

Both hashes matched the previously accepted Milestone 5 live-test gate inputs.

Derived VM Backup Assurance for the three K3s VMs remained within the accepted `STRICT_CORRELATION_ONLY` contract:

```text
VMID 106 LAST_SUCCESSFUL_BACKUP=OBSERVED 2026-08-14T16:39:53Z
VMID 107 LAST_SUCCESSFUL_BACKUP=OBSERVED 2026-08-14T17:39:32Z
VMID 108 LAST_SUCCESSFUL_BACKUP=OBSERVED 2026-04-15T12:36:38Z
```

For all three VMs:

```text
protection_status: UNKNOWN
restore_verification_status: UNKNOWN
integrity_verification_status: UNKNOWN
failure_domain_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

The derived output was computed in memory only. No infrastructure query or mutation was required for the derivation.

## PostgreSQL to infrastructure recovery relationship

The currently established relationship is:

```text
PostgreSQL workload
-> Bound local-path PVC
-> explicit Kubernetes PV storage node
-> K3s VM
-> PVE VMID
-> authoritative successful VZDUMP task evidence
```

Current grouping:

```text
keycloak
  -> k3s-master-01 -> VMID 106 -> last successful VM backup 2026-08-14T16:39:53Z

fastapi-platform
fastapi-platform-dev
openproject
soria-prospecting
toilettage
  -> k3s-worker-01 -> VMID 107 -> last successful VM backup 2026-08-14T17:39:32Z

drfarah-staging
soria-academie
  -> k3s-worker-02 -> VMID 108 -> last successful VM backup 2026-04-15T12:36:38Z
```

This relationship is infrastructure-level recovery evidence only. It must not be represented as PostgreSQL-consistent backup evidence, PostgreSQL restore verification, or database integrity verification.

The older VMID 108 backup timestamp must not be promoted to `STALE` or `RPO_VIOLATION` until an accepted freshness/RPO contract exists.

## Management-host PostgreSQL discovery

A PostgreSQL 15 cluster was observed locally on `mgmt-automation`:

```text
postgresql@15-main.service: active/running
```

Backup-capable PostgreSQL client tooling was present:

```text
pg_dump: present, PostgreSQL 15.19
pg_dumpall: present, PostgreSQL 15.19
pg_basebackup: present, PostgreSQL 15.19
pg_receivewal: present, PostgreSQL 15.19
```

Specialized backup tooling was not present in the inspected command scope:

```text
pgBackRest: not present
Barman: not present
barman-cloud-backup: not present
WAL-G: not present
```

No PostgreSQL-specific cron file-name signal or local backup-script file-name signal was observed.

A packaged systemd template exists:

```text
pg_basebackup@.service
pg_basebackup@.timer
```

Safe template metadata established:

```text
Description=Basebackup of PostgreSQL Cluster %i
After=postgresql@%i.service
User=postgres

Description=Weekly Basebackup of PostgreSQL Cluster %i
OnCalendar=weekly
RandomizedDelaySec=1h
```

However:

```text
installed pg_basebackup instance symlinks: 0
loaded/known pg_basebackup service/timer instances: 0
pg_basebackup@.timer unit-file state: disabled
```

The raw `ExecStart` arguments were intentionally not projected and the mechanism behind the template command remains unestablished. Because no configured instance was observed, the template itself is capability/declaration evidence only and does not establish scheduled backup execution.

`dpkg-db-backup.timer` was observed but is not accepted as PostgreSQL application-data backup evidence.

## Current assurance interpretation

For the eight Kubernetes PostgreSQL instances:

```text
PostgreSQL instance: OBSERVED
persistent storage attachment: OBSERVED
infrastructure recovery relationship: OBSERVED
underlying VM last-successful-backup evidence: OBSERVED
PostgreSQL-consistent backup mechanism: UNKNOWN
PostgreSQL backup execution/result: UNKNOWN
PostgreSQL backup artifact location: UNKNOWN
PostgreSQL retention effectiveness: UNKNOWN
PostgreSQL integrity verification: UNKNOWN
PostgreSQL restore verification: UNKNOWN
PostgreSQL RPO/RTO: UNKNOWN
```

For the local `mgmt-automation` PostgreSQL instance:

```text
PostgreSQL instance: OBSERVED
backup-capable tooling: OBSERVED
configured PostgreSQL backup mechanism: UNKNOWN
scheduled PostgreSQL backup execution: NOT_OBSERVED_IN_INSPECTED_LOCAL_SCOPE
last successful PostgreSQL backup: UNKNOWN
restore verification: UNKNOWN
integrity verification: UNKNOWN
```

`NOT_OBSERVED_IN_INSPECTED_LOCAL_SCOPE` is not equivalent to `UNPROTECTED`.

## Safety boundary

The discovery did not:

```text
read Kubernetes Secret values
print PostgreSQL environment values
read .pgpass
open a PostgreSQL connection
read database rows or dump contents
read raw PostgreSQL configuration content
print raw cron commands
print raw systemd ExecStart arguments
execute a backup
execute a restore
modify WAL configuration
change retention
restart PostgreSQL
start or enable systemd units
modify Kubernetes or PVE resources
```

## Decision from discovery

No authoritative database-aware backup execution/result source has yet been established for the observed PostgreSQL instances.

Therefore the next implementation must not claim PostgreSQL backup protection. The next safe vertical slice should model a bounded PostgreSQL infrastructure-recovery context for the eight Kubernetes instances, preserving the distinction between:

```text
OBSERVED infrastructure recovery evidence
UNKNOWN PostgreSQL-consistent backup evidence
UNKNOWN restore/integrity/RPO/RTO assurance
```

The local management-host PostgreSQL instance should remain a separate discovery subject until an authoritative backup source or infrastructure-recovery relationship is established for it.
