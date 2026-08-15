# Milestone 5 Authoritative Backup-Source Discovery — 2026-08-15

## Status

Discovery in progress. Four bounded management-host preflights completed without triggering backup or restore operations.

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

## PostgreSQL discovery conclusion

A local PostgreSQL `15/main` cluster is online and PostgreSQL client/package backup capability exists, but no instantiated `pg_basebackup` schedule, enabled timer instance, or bounded active archive/backup configuration was observed.

PostgreSQL on `mgmt-automation` is therefore not selected as the next authoritative backup source. Package/tool/template presence is capability evidence only.

## Proxmox endpoint discovery

Live reachability from `mgmt-automation`:

```text
BM1 PVE API TCP/8006: REACHABLE
BM2 PVE API TCP/8006: REACHABLE
BM1 unauthenticated PVE /version: HTTP 401
BM2 unauthenticated PVE /version: HTTP 401
BM1 same-address TCP/8007: TIMEOUT
BM2 same-address TCP/8007: TIMEOUT
```

The 8006 observations prove both current PVE endpoints are reachable and authentication-required.

The 8007 timeouts do not prove PBS absence. Operator-provided current context states that BM1 uses UFW source-IP restrictions and similar restrictions may exist for VMs/services. Negative reachability is therefore `FAILED_TO_REACH / UNKNOWN` when the network observation path is not known complete.

Observed TLS metadata:

```text
BM1 CN=proxbenovh.cloud; certificate expired 2025-08-04
BM2 CN=delfan.local; certificate valid through 2027-10-13
```

BM1 endpoint reachability was observed with insecure TLS verification. Reachability is current evidence; healthy TLS trust is not.

## Authenticated BM2 PVE discovery

An existing local Proxmox env file was inspected with values never printed:

```text
path: /home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env
owner/group: ben/ben
mode: 0644
tracked by Git: no
ignored by Git: yes
configured endpoint: BM2
TLS verification configured: false
custom CA configured: false
```

The existing token was used for bounded HTTP GET discovery only. It is discovery-only and has not been accepted as the platform observer identity.

Authenticated observations:

```text
PVE version: 9.1.9
release: 9.1
node: delfan
node status: online
storage: local
storage type: dir
content capability: iso,snippets,backup,vztmpl,images,rootdir
storage disabled: false
retention projection: keep-all=1
configured PBS storage IDs: none observed
cluster backup jobs: 0
```

These facts mean:

- BM2 PVE is a current live authoritative source candidate for VM/storage/backup configuration;
- local storage is configured to allow `backup` content;
- retention configuration `keep-all=1` is storage configuration, not proof that any backup artifact exists;
- no cluster backup job is currently declared in the returned scope;
- no PBS storage is currently configured in BM2 PVE.

The operator explicitly confirms that PBS does not exist today. Therefore PBS current state is treated as `NOT_CONFIGURED_BY_OPERATOR` for current architecture planning, while previous network timeouts remain non-authoritative evidence by themselves.

## PBS future-compatibility requirement

The platform must remain ready for a future Proxmox Backup Server without redesigning the core Backup and Recovery Assurance contract.

Future PBS support must be added as another authoritative source adapter rather than changing the meaning of existing asset/assurance fields.

The source-neutral contract must continue to model evidence such as:

```text
BACKUP_MECHANISM
LAST_SUCCESSFUL_BACKUP
BACKUP_RETENTION
BACKUP_FAILURE_DOMAIN
BACKUP_INTEGRITY_VERIFICATION
RESTORE_TEST
RPO_TARGET_AND_RESULT
RTO_TARGET_AND_RESULT
```

A future PBS adapter may satisfy some of these fields from PBS-native evidence, while current PVE/local-backup evidence may satisfy them from PVE-native evidence. Source identity/provenance must remain explicit so evidence from PVE local storage and PBS is never conflated.

No current field should require a PBS-specific identifier in order to represent protection. PBS datastore/namespace/snapshot identity, if later required, should live inside source-specific evidence/provenance context behind the common assurance model.

## Current security observations

The discovered existing Proxmox env file is mode `0644`. It contains token material and therefore is not acceptable as the final platform observation credential location without a separate hardening decision.

The current token successfully reads version, nodes, storage configuration, and cluster backup-job configuration. Successful GET access does not prove least privilege. Its effective permission scope still needs bounded verification before runtime reuse.

Terraform provider files confirm an API-token access pattern and declare the token secret sensitive. Sensitive Terraform state/tfvars were identified by filename only and were not read.

## Exact next discovery step

Before implementing a PVE backup collector:

1. inspect the existing token's effective read privilege scope using bounded safe API metadata if available;
2. do not print token ID, secret, ACL raw records containing unrelated identities, or sensitive configuration;
3. query BM2 local storage backup content metadata read-only to determine whether any current backup artifacts actually exist;
4. if backup artifacts exist, project only safe identity/time/size/type metadata sufficient to assess last observed recovery point;
5. keep backup success, integrity, restore verification, RPO and RTO separate;
6. do not infer scheduled protection because cluster backup jobs are currently zero;
7. decide whether a new dedicated least-privilege Proxmox observer token is required before runtime integration;
8. BM1 remains a separate observation target; do not reuse BM2 facts for BM1 and do not classify firewall-restricted failures as absence.

No backup, restore, snapshot, prune, verify, garbage collection, schedule mutation, credential creation, or Terraform state read is allowed during discovery.

## Trust boundary

- package/tool presence is capability evidence, not backup evidence;
- storage `content=backup` is configured capability, not a recovery point;
- `keep-all=1` is retention configuration, not proof of retained backups;
- zero configured backup jobs means no cluster backup job was observed in the returned complete scope, not that no manual backup artifact can exist;
- PVE endpoint reachability is not PBS presence;
- network timeout is not absence when firewall/source restrictions may apply;
- operator-confirmed current PBS nonexistence may guide current design, but future PBS compatibility remains required;
- a configured future `pbs` storage will prove PVE-to-PBS configuration, not successful backups;
- backup-job configuration proves declared schedule, not successful execution;
- successful backup evidence is not restore verification;
- no secrets, tokens, passwords, private keys, raw database credentials, Terraform state values, or complete sensitive connection strings may enter discovery output.
