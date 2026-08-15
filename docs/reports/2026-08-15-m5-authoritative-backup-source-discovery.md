# Milestone 5 Authoritative Backup-Source Discovery — 2026-08-15

## Status

Discovery in progress. First management-host preflight completed successfully without triggering backup or restore operations.

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

## First source-discovery preflight

Management host: `mgmt-automation`.

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

Observed systemd unit names relevant to backup/recovery:

```text
dpkg-db-backup.service
dpkg-db-backup.timer
pg_basebackup@.service
pg_basebackup@.timer
postgresql.service
postgresql@.service
```

Only `dpkg-db-backup.timer` was observed as an active/scheduled relevant timer in the generic timer listing. The presence of `pg_basebackup@.service/.timer` templates does not prove that an instantiated PostgreSQL backup job exists or runs.

No cron or local systemd files containing the searched backup-tool references were found under the bounded paths checked.

No matching SSH host alias was available in `~/.ssh/config` because that file was not present.

Repository search found only the newly accepted backup-assurance foundation files; no accepted PBS/Proxmox/database-native backup configuration was found.

The configuration-variable-name subsection of the first preflight had an `awk` syntax error. This is a preflight-script defect only. It does not invalidate the other discovery results and no secret value was printed by that subsection.

## Current interpretation

The current evidence does not justify implementing a PBS/Proxmox collector: no corresponding management-host CLI or accepted repository configuration was observed.

The presence of `pg_dump`, `pg_restore`, `psql`, and `pg_basebackup@` templates makes PostgreSQL the only source with a concrete local signal worth investigating next. However, CLI/template presence alone is not evidence of an active backup mechanism, backup success, retention, restore verification, or database coverage.

Do not classify PostgreSQL as the selected authoritative source yet.

## Exact next discovery step

Run a second bounded PostgreSQL backup preflight that performs no database connection and no backup operation. Determine only:

1. whether any `pg_basebackup@` service/timer instances are enabled, active, or scheduled;
2. where the template unit files reside;
3. whether template execution depends on environment/config files, while printing only filenames/directive names and never values;
4. which local PostgreSQL clusters are registered/running, using cluster metadata only;
5. whether any local backup directories or known package-managed backup paths exist, without reading backup contents;
6. whether `collector.env` or `/etc/environment` contain relevant variable names, with values redacted;
7. whether the observed PostgreSQL backup path can prove last success, retention, integrity, restore test, RPO, or RTO without broad credentials or mutation.

No database connection, `pg_basebackup`, `pg_dump`, restore, schedule change, credential creation, or backup execution is allowed during this discovery step.

## Trust boundary

- package/tool presence is capability evidence, not backup evidence;
- a systemd template is declared capability, not an instantiated backup job;
- an enabled timer is schedule evidence, not successful backup evidence;
- backup files/directories existing on disk are not sufficient to claim successful or restorable protection;
- authoritative protection classification remains UNKNOWN until accepted source evidence exists;
- no secrets, tokens, passwords, private keys, raw database credentials, or complete sensitive connection strings may enter discovery output.
