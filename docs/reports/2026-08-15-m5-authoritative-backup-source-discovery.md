# Milestone 5 Authoritative Backup-Source Discovery — 2026-08-15

## Status

Discovery in progress. Two bounded management-host preflights completed successfully without triggering backup or restore operations.

## Purpose

Identify which backup/recovery source is actually present and can be observed safely before implementing an authoritative Milestone 5 collector.

This discovery does not classify any asset as protected or unprotected and does not modify backup schedules, infrastructure, credentials, or data.

## Stable foundation

PR #30 established the derived-only Kubernetes PVC assurance foundation:

```text
backup_assurance_version: 0.1
PVC assets: 37
protection UNKNOWN: 37
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
```

## First management-host source-discovery preflight

Observed CLI availability:

```text
proxmox-backup-client: absent
pvesh: absent
pvesm: absent
vzdump: absent
pgbackrest: absent
wal-g: absent
pg_dump: present
pg_restore: present
psql: present
mariadb-backup: absent
mariabackup: absent
mysqldump: absent
mariadb: absent
restic: absent
borg: absent
kopia: absent
rclone: absent
velero: absent
```

Relevant systemd unit names included `pg_basebackup@.service/.timer`, but only `dpkg-db-backup.timer` appeared active/scheduled in the generic timer listing.

No accepted PBS/Proxmox/database-native backup configuration was found in the platform repository. No matching SSH host aliases were available on `mgmt-automation`.

The first config-variable-name subsection had an `awk` syntax error. This affected that subsection only and printed no secret value.

## Second PostgreSQL metadata-only preflight

Observed PostgreSQL runtime metadata:

```text
cluster: 15/main
port: 5432
status: online
owner: postgres
systemd: postgresql@15-main.service active/running
```

Observed `pg_basebackup` package capability:

```text
pg_basebackup@.service
  Description=Basebackup of PostgreSQL Cluster %i
  User=postgres
  Exec program=pg_backupcluster
  Environment variable name=KEEP

pg_basebackup@.timer
  Description=Weekly Basebackup of PostgreSQL Cluster %i
  OnCalendar=weekly
  RandomizedDelaySec=1h
```

However, no instantiated `pg_basebackup@<instance>.service` or `.timer`, no enabled instance symlink, and no scheduled `pg_basebackup` timer were observed.

No active backup/replication-related PostgreSQL configuration keys were observed in the bounded configuration scan. No relevant backup/PBS/Proxmox/database variable names were found in `/etc/infra-assurance/collector.env` or `/etc/environment`.

No `pg_basebackup`-specific configuration file was found. `/var/backups` exists, but directory existence alone is not backup evidence and its contents were not read.

## PostgreSQL conclusion

PostgreSQL on `mgmt-automation` is a real running database capability, but the current discovery does not establish an active database-native backup mechanism.

The `pg_basebackup@` units are package/template capability only. They are not evidence of an instantiated schedule, completed backup, retention, integrity verification, restore test, RPO result, or RTO result.

Therefore PostgreSQL is **not selected as the next authoritative backup source** from this host.

Do not implement a PostgreSQL backup collector from these observations alone.

## Historical Proxmox/PBS signal requiring live verification

Historical infrastructure/project material records two Proxmox VE bare-metal environments and documents Proxmox Backup Server as the selected infrastructure-backup approach. This is useful discovery context but is not current live evidence and must not be treated as proof that PBS is presently configured or healthy.

The next discovery should verify the current Proxmox/PBS path read-only before any collector is designed.

## Exact next discovery step

Perform a bounded Proxmox/PBS preflight using current infrastructure endpoints/access paths only for verification. The preflight should:

1. verify current Proxmox VE endpoint reachability and TLS/API identity without credentials where possible;
2. inspect local project/config metadata for existing Proxmox observer/API credential *names or file paths only*, never values;
3. determine whether an existing read-only Proxmox API identity/access path already exists;
4. if a safe authenticated observation path exists, determine whether PBS-backed storage/backup jobs are configured without printing tokens, secrets, full connection strings, or sensitive configuration;
5. distinguish Proxmox VE reachability from PBS presence;
6. distinguish configured backup storage/job from successful backup evidence;
7. do not run backup, restore, prune, verify, garbage-collection, snapshot, or schedule-changing operations.

If no least-privilege read-only path exists, stop at `UNKNOWN` and design that observation identity separately rather than reusing an administrative credential.

## Trust boundary

- package/tool presence is capability evidence, not backup evidence;
- a systemd template is declared capability, not an instantiated backup job;
- an enabled timer would be schedule evidence, not successful backup evidence;
- backup files/directories existing on disk are not sufficient to claim successful or restorable protection;
- historical design documentation is not current live evidence;
- authoritative protection classification remains UNKNOWN until accepted source evidence exists;
- no secrets, tokens, passwords, private keys, raw database credentials, or complete sensitive connection strings may enter discovery output.
