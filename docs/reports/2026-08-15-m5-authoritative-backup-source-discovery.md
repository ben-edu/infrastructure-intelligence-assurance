# Milestone 5 Authoritative Backup-Source Discovery — 2026-08-15

## Status

Accepted. Five bounded read-only management-host preflights completed without triggering backup or restore operations.

## Purpose

Identify a real authoritative backup/recovery source and a safe observation contract before implementing a Milestone 5 collector.

## Stable foundation

PR #30 established the derived-only Kubernetes PVC assurance foundation:

```text
backup_assurance_version: 0.1
PVC assets: 37
protection UNKNOWN: 37
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
```

## PostgreSQL conclusion

A local PostgreSQL `15/main` cluster is online and PostgreSQL client/package backup capability exists, but no instantiated `pg_basebackup` schedule, enabled timer instance, or bounded active archive/backup configuration was observed. PostgreSQL is not selected as the next authoritative backup source.

## Network/firewall semantics

BM1 uses UFW source-IP restrictions, and similar restrictions may exist on VMs/services. A timeout or unreachable TCP path must therefore remain `FAILED_TO_REACH / UNKNOWN` unless the observation path is known complete. Network timeout is not absence.

## Proxmox endpoint observations

From `mgmt-automation`:

```text
BM1 PVE API TCP/8006: REACHABLE
BM2 PVE API TCP/8006: REACHABLE
BM1 unauthenticated /version: HTTP 401
BM2 unauthenticated /version: HTTP 401
BM1 same-address TCP/8007: TIMEOUT
BM2 same-address TCP/8007: TIMEOUT
```

Observed TLS metadata:

```text
BM1 CN=proxbenovh.cloud; certificate expired 2025-08-04
BM2 CN=delfan.local; certificate valid through 2027-10-13
```

BM1 reachability was tested with insecure TLS verification. Reachability is current evidence; healthy certificate trust is not.

## BM2 authenticated PVE discovery

An existing local API-token credential was used for bounded HTTP GET discovery only. Token ID/secret were never printed and Terraform state/tfvars were not read.

Safe endpoint observations:

```text
PVE version: 9.1.9
release: 9.1
node: delfan
node status: online
storage: local
storage type: dir
storage content capability: iso,snippets,backup,vztmpl,images,rootdir
storage disabled: false
retention projection: keep-all=1
configured PBS storage IDs: none
cluster backup jobs: 0
```

The operator explicitly confirms there is no PBS today.

## Existing BM2 token security conclusion

Effective permission metadata was observed successfully. The existing token is broad/admin-like and is rejected for platform runtime use.

Observed control-capable privileges include, among others:

```text
Datastore.Allocate
Datastore.AllocateSpace
Datastore.AllocateTemplate
Mapping.Modify
Permissions.Modify
Sys.Console
Sys.Modify
Sys.PowerMgmt
VM.Allocate
VM.Console
VM.PowerMgmt
VM.Snapshot
VM.Snapshot.Rollback
```

The existing credential remains `DISCOVERY_ONLY`. It must not be wired into the platform runtime. Its current file is Git-ignored but mode `0644`, and TLS verification is disabled. Neither property is acceptable for final observer credential handling.

## BM2 current guest inventory

Current PVE guest scope returned 12 QEMU guests:

```text
100 101 102 103 104 105 106 107 108 109 110 9000
```

## BM2 authoritative local backup artifacts

A complete authenticated GET of `local` storage backup content returned 12 backup artifacts in `vma.zst` format.

Recovery points by VMID:

```text
100: 2; latest 2026-05-08T06:13:59Z
101: 1; latest 2026-05-08T10:36:12Z
106: 3; latest 2026-08-14T16:13:14Z
107: 3; latest 2026-08-14T16:40:35Z
108: 2; latest 2026-04-15T12:30:02Z
109: 1; latest 2026-04-13T10:34:52Z
```

Current guest VMIDs with at least one observed local recovery point:

```text
100 101 106 107 108 109
```

Current guest VMIDs with no observed backup artifact in this complete `local` storage scope:

```text
102 103 104 105 110 9000
```

This is authoritative evidence only for BM2 PVE storage `local` in the returned scope. It must not be generalized to external backup systems, BM1, future PBS, or other storage backends.

Artifact presence proves a recovery-point artifact exists. It does not prove restore verification, application consistency, integrity verification, current scheduled protection, RPO compliance, or RTO compliance.

`protected=false` is a Proxmox retention/protection flag on the archive and must not be mapped to the platform's `UNPROTECTED` assurance state.

Cluster backup jobs returned zero. Therefore the current recovery points may be manual, historical, externally initiated, or created by a mechanism not represented by current cluster backup-job configuration. Do not infer scheduled protection.

## PBS future-compatibility requirement

The core Backup and Recovery Assurance model must remain source-neutral so a future Proxmox Backup Server can be added without redesigning asset/protection semantics.

PVE local backup and future PBS-native evidence are separate source adapters with explicit provenance. Both may satisfy common dimensions:

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

Do not make the core schema depend on PBS datastore/namespace/snapshot identifiers. Source-specific identities belong in source evidence/provenance.

## Selected next implementation source

BM2 Proxmox VE is selected as the first authoritative backup source adapter because:

1. the PVE API is live and queryable read-only;
2. current guest identity is observable;
3. storage backup content is authoritative and returns real recovery-point artifacts;
4. safe fields can be projected without secrets or raw storage configuration;
5. the adapter can remain source-neutral and future-PBS compatible.

## Implementation boundary

The first PVE adapter must:

- use HTTP GET only;
- model source observation independently from assurance interpretation;
- project bounded guest/storage/recovery-point metadata only;
- preserve BM2 source identity and storage ID provenance;
- distinguish complete empty scope from failed observation;
- never interpret archive `protected=false` as platform `UNPROTECTED`;
- never claim restore verification, integrity, RPO, RTO, or current scheduled protection from archive presence alone;
- keep future PBS as a separate adapter;
- not use the current broad discovery token for runtime wiring.

During the current read-only phase, repository implementation and a manual live validation may use the existing token only as a temporary discovery/test credential with GET-only code. Runtime credential provisioning and runtime wiring remain blocked until a dedicated least-privilege observer identity is separately approved/provisioned.

## Trust boundary

- tool/template presence is capability evidence, not backup evidence;
- `content=backup` is storage capability, not a recovery point;
- a returned backup artifact is observed recovery-point evidence, not restore verification;
- zero cluster backup jobs is current configuration evidence, not proof that historical/manual backups cannot exist;
- `protected=false` is not the platform assurance meaning `UNPROTECTED`;
- timeout is not absence when firewall/source restrictions may apply;
- operator-confirmed current PBS absence does not remove future PBS compatibility;
- no passwords, tokens, private keys, raw database credentials, Terraform state values, raw sensitive storage configuration, or complete sensitive connection strings may enter evidence output.
