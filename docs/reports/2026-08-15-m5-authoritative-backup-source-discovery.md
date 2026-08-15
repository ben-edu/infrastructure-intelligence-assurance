# Milestone 5 Authoritative Backup-Source Discovery — 2026-08-15

## Status

Discovery in progress. Three bounded management-host preflights completed without triggering backup or restore operations.

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

## Third Proxmox/PBS endpoint preflight

Current live reachability from `mgmt-automation`:

```text
BM1 PVE API candidate TCP/8006: REACHABLE
BM2 PVE API candidate TCP/8006: REACHABLE
BM1 same-address TCP/8007: TIMEOUT
BM2 same-address TCP/8007: TIMEOUT
BM1 unauthenticated PVE API /version: HTTP 401
BM2 unauthenticated PVE API /version: HTTP 401
```

The two `401` responses prove that current Proxmox VE API endpoints are reachable and require authentication. They do not prove any backup configuration.

The two TCP/8007 timeouts do **not** prove that PBS is absent. Operator-provided current context states that BM1 uses UFW source-IP restrictions, and similar network restrictions may exist for VMs or other services. Therefore negative reachability is classified as `FAILED_TO_REACH / UNKNOWN`, not `ABSENT`. PBS may also live on another host or VM.

Observed TLS metadata:

```text
BM1 certificate CN: proxbenovh.cloud
BM1 certificate expiry: 2025-08-04 (expired relative to 2026-08-15)
BM2 certificate CN: delfan.local
BM2 certificate expiry: 2027-10-13
```

Reachability used an insecure TLS probe, so BM1 endpoint reachability is established but certificate trust is not. Do not silently normalize the expired BM1 certificate into a healthy TLS state.

Safe local metadata discovered existing Proxmox integration material:

```text
api-cluster-infra Terraform provider config for bm1/bm2
Proxmox API token variable names for bm1/bm2
historical/current local MCP Proxmox env file path under afpa-infra-rebuild
Proxmox env example defining BASE_URL, TOKEN_ID, TOKEN_SECRET and TLS options
```

The `api-cluster-infra` provider config consumes only an API URL, token ID, token secret, and TLS verification setting. The token secret is declared sensitive. Existing Terraform defaults allow insecure TLS until certificate trust is established. These are configuration capabilities, not accepted observer credentials.

Potentially sensitive Terraform state/tfvars files were identified by filename only and were not read.

The Proxmox environment-variable subsection hit a permission error when a non-root process attempted to stat `/etc/infra-assurance/collector.env`. This is a preflight helper limitation only. No secret value was printed.

## Current Proxmox interpretation

Proxmox VE is now a **live source candidate** because both API endpoints are reachable and the local project history contains an API-token access pattern.

PBS itself is still `UNKNOWN`. Direct TCP/8007 timeout is insufficient evidence of absence because of firewall/source restrictions and because PBS may be configured behind PVE storage metadata or on another endpoint.

Official Proxmox VE storage semantics represent Proxmox Backup Server as storage type `pbs` inside PVE. Therefore PVE's own bounded storage configuration is the preferred next discovery surface. Do not read `/etc/pve/priv` or any storage-password/encryption-key files.

The next discovery should use only an already-existing Proxmox credential path, first to determine whether that credential is usable for read-only observation. It must never print the token ID/secret and must not be accepted as the platform observer identity merely because it works.

If authenticated read-only access succeeds, inspect bounded safe projections from PVE only:

1. PVE version / node identity;
2. configured storage IDs/types/content/disabled state, especially whether any storage has type `pbs`;
3. configured cluster backup job IDs, schedule, enabled state, mode, target storage, and bounded VM-selection metadata;
4. no raw storage configuration fields that can contain usernames, secrets, fingerprints, encryption-key paths, or full endpoint strings.

A configured `pbs` storage proves PVE-to-PBS configuration, not backup success. A configured backup job proves declared schedule, not successful execution. Successful/retained/restorable protection still requires stronger authoritative evidence.

## Exact next discovery step

Perform a credential-metadata and bounded authenticated PVE preflight using the existing local Proxmox env file only if it contains the expected non-empty variables.

The preflight must:

- print only file metadata and variable names/presence states, never values;
- map the configured base URL internally to BM1/BM2/OTHER without printing the raw URL;
- use the token only for GET requests;
- first query a harmless identity/version endpoint;
- if authentication works, query only safe projections of PVE storage configuration and cluster backup jobs;
- stop on authorization failure rather than escalating privileges;
- never read Terraform state/tfvars;
- never run backup, restore, snapshot, prune, verify, garbage collection, or schedule mutation.

This existing token is **discovery-only** unless a later accepted check proves it is an appropriate least-privilege observer identity. Successful authentication alone is not evidence that the credential should be reused by the platform.

## Trust boundary

- package/tool presence is capability evidence, not backup evidence;
- a systemd template is declared capability, not an instantiated backup job;
- an enabled timer would be schedule evidence, not successful backup evidence;
- backup files/directories existing on disk are not sufficient to claim successful or restorable protection;
- PVE endpoint reachability is not PBS presence;
- TCP timeout is not absence when firewall/source restrictions may apply;
- PVE `pbs` storage configuration would prove configured integration, not successful backups;
- backup-job configuration would prove declared schedule, not successful execution;
- historical design documentation is not current live evidence;
- authoritative protection classification remains UNKNOWN until accepted source evidence exists;
- no secrets, tokens, passwords, private keys, raw database credentials, Terraform state values, or complete sensitive connection strings may enter discovery output.
