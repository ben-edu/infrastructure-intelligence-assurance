# Milestone 5 MariaDB Backup/Recovery Source Discovery — 2026-08-16

## Status

Accepted bounded read-only discovery on `mgmt-automation`.

## Scope

Identify MariaDB/MySQL-compatible runtime candidates, persistence relationships, bounded backup signals, and existing infrastructure-level VM recovery evidence without claiming MariaDB-consistent backup protection.

## Kubernetes candidates

Four MariaDB-compatible containers were observed:

```text
bookstack/Deployment/mariadb
  image: mariadb:10.11
  pod node: k3s-worker-02
  PVC: mariadb-data
  PVC phase: Bound
  storageClass: local-path
  storage node: k3s-worker-02

misp/Deployment/mariadb
  image: mariadb:10.5
  pod node: k3s-master-01
  PVC: mariadb-pvc
  PVC phase: Bound
  storageClass: local-path
  storage node: k3s-master-01

misp/Deployment/mariadb-v2
  image: mariadb:10.5
  pod node: k3s-master-01
  PVC: NONE_OBSERVED

moodle/StatefulSet/moodle-mariadb
  image: docker.io/bitnamilegacy/mariadb:12.0.2-debian-12-r0
  pod node: k3s-worker-02
  PVC: data-moodle-mariadb-0
  PVC phase: Bound
  storageClass: local-path
  storage node: k3s-worker-02
```

Interpretation:

```text
candidate workloads: 4
persistent relationships observed: 3
persistent relationship not observed: 1
```

`NONE_OBSERVED` is not evidence that `misp/mariadb-v2` is intentionally ephemeral or unprotected. Its persistence state remains unknown in the inspected safe scope.

## Kubernetes backup signals

Bounded name/image discovery found:

```text
matching_cronjobs: 0
matching_jobs: 0
```

This is source-scoped negative evidence only. It does not establish universal absence of MariaDB backups.

## Bounded infrastructure recovery relationships

The persistence-bearing database candidates use two Kubernetes storage nodes:

```text
k3s-master-01
k3s-worker-02
```

Existing bounded PVE observation establishes:

```text
k3s-master-01 -> pve-bm2/delfan -> VMID 106
k3s-worker-02 -> pve-bm2/delfan -> VMID 108
```

Both accepted VM source artifacts were byte-verified before correlation:

```text
/tmp/vm-backup-assurance.json
sha256 match: true

/tmp/proxmox-ve-backup-task-results.json
sha256 match: true
```

Accepted VM Backup Assurance v0.2 provides:

```text
VMID 106
  LAST_SUCCESSFUL_BACKUP: OBSERVED
  latest: 2026-08-14T16:39:53Z

VMID 108
  LAST_SUCCESSFUL_BACKUP: OBSERVED
  latest: 2026-04-15T12:36:38Z
```

Therefore infrastructure-level recovery context can be safely joined for the three persistence-bearing MariaDB candidates:

```text
misp/Deployment/mariadb
  -> k3s-master-01
  -> VMID 106
  -> VM LAST_SUCCESSFUL_BACKUP=OBSERVED

bookstack/Deployment/mariadb
  -> k3s-worker-02
  -> VMID 108
  -> VM LAST_SUCCESSFUL_BACKUP=OBSERVED

moodle/StatefulSet/moodle-mariadb
  -> k3s-worker-02
  -> VMID 108
  -> VM LAST_SUCCESSFUL_BACKUP=OBSERVED
```

No equivalent persistence-backed infrastructure-recovery relationship is promoted for `misp/Deployment/mariadb-v2` because no mounted persistent PVC was observed in this bounded discovery.

## Management-host signals

No local MariaDB/MySQL server or backup tooling was observed on `mgmt-automation` in the inspected scope:

```text
mariadb.service: not-found/inactive
mysql.service: not-found/inactive
mariadb: NOT_PRESENT
mysql: NOT_PRESENT
mariadb-dump: NOT_PRESENT
mysqldump: NOT_PRESENT
mariadb-backup: NOT_PRESENT
xtrabackup: NOT_PRESENT
```

This does not establish that no remote or externally orchestrated MariaDB backup mechanism exists.

## Trust interpretation

Observed infrastructure recovery means only:

```text
MariaDB-compatible workload
-> observed persistent PVC relationship
-> explicit Kubernetes storage node
-> accepted PVE VM mapping
-> accepted strict VM last-successful-backup evidence
```

It does not establish:

```text
MariaDB-consistent backup
backup mechanism
backup execution/result
backup artifact location
retention effectiveness
restore verification
integrity verification
RPO satisfaction
RTO satisfaction
```

The older VMID 108 timestamp is retained as observed evidence and is not classified as stale or an RPO violation because no accepted MariaDB freshness/RPO target exists.

## Safety boundary

The discovery was read-only.

Not read or projected:

```text
Kubernetes Secret values
container environment values
container commands/args
PV backing paths
CSI handles
database rows
dump contents
connection strings
raw PVE VM config
disk/network details
credential values
```

No backup, restore, service, Kubernetes, PVE, database, or infrastructure mutation occurred.

## Next smallest useful slice

Implement a pure derived `MariaDB infrastructure recovery context v0.1` for the four observed Kubernetes candidates.

Expected conservative semantics:

```text
instances_total: 4
persistence_observed: 3
persistence_unknown: 1
infrastructure_recovery_observed: 3
infrastructure_recovery_unknown: 1
MariaDB-specific protection/mechanism/execution/restore/integrity/RPO/RTO: UNKNOWN
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

Do not implement a MariaDB database-aware backup claim until an authoritative MariaDB-specific execution/result source is identified.
