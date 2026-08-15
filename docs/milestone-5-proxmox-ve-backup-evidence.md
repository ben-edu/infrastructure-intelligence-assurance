# Milestone 5 — Proxmox VE Backup Evidence

## Status

Accepted and live validated on 2026-08-15.

## Goal

Add the first authoritative VM backup/recovery evidence source without turning source facts into premature platform protection claims and without wiring an administrative credential into runtime.

## Scope

This slice adds a bounded Proxmox VE source adapter and a standalone source artifact.

It does not:

- modify Proxmox;
- trigger backup, restore, snapshot, prune, verification, or garbage collection;
- change backup schedules;
- change guest state;
- change ACLs or credentials;
- read Terraform state/tfvars;
- wire Proxmox credentials into systemd;
- modify Kubernetes RBAC;
- rewrite the existing Kubernetes PVC Backup Assurance artifact.

## Source artifact

```text
proxmox_ve_backup_evidence_version: 0.1
mutation_allowed: false
```

The adapter performs bounded HTTP GET observations only:

```text
/api2/json/version
/api2/json/nodes
/api2/json/cluster/resources?type=vm
/api2/json/storage
/api2/json/cluster/backup
/api2/json/nodes/<node>/storage/<selected-storage>/content?content=backup
```

## Safe projection

The artifact may contain only bounded source evidence such as:

- PVE version/release identity;
- node name/status;
- current guest VMID/type/status/node;
- storage ID/type and bounded backup-capability/retention state;
- whether the storage backend type is `pbs`;
- bounded cluster backup-job metadata;
- selected node/storage content observation status;
- recovery-point VMID, node, storage, format, creation time and size;
- source-native archive protection flag;
- per-guest selected-storage recovery-point coverage.

It does not persist raw `volid`, raw API payload, raw URL, guest names, token material, storage server/path/username, fingerprints, encryption-key references, or arbitrary storage configuration.

## Failure semantics

Source status is:

```text
COMPLETE
PARTIAL
FAILED_TO_OBSERVE
```

Selected-storage guest coverage is:

```text
RECOVERY_POINT_OBSERVED
NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE
UNKNOWN
```

A complete empty storage-content scope is a valid scoped negative observation. A failed observation remains unknown and must not become an empty scope.

## Assurance boundary

A PVE backup artifact establishes an observed recovery point in the exact source/node/storage scope.

It does not establish:

- restore verification;
- integrity verification;
- application consistency;
- current scheduled protection;
- RPO compliance;
- RTO compliance.

The PVE archive `protected` flag is represented only as source-native `archive_protection_flag`. It must never map to platform `PROTECTED` or `UNPROTECTED`.

A VM with no recovery point in a complete selected storage scope is not automatically universally unprotected because other backup sources may exist now or later.

## Credential boundary

The currently available BM2 token is broad/admin-like, its env file is mode `0644`, and TLS verification is disabled.

Normal collector execution refuses insecure file mode and disabled TLS verification. Manual live validation may use explicit discovery overrides, but the artifact always keeps:

```text
credential_runtime_approved: false
```

This source slice does not auto-approve credentials. Runtime approval requires a separate least-privilege access-control decision.

## Future PBS compatibility

There is no PBS today. Future PBS support is mandatory without redesigning the common assurance model.

PVE-local evidence and future PBS-native evidence remain separate source adapters with explicit provenance. PBS-specific datastore/namespace/snapshot identity stays source-specific while common assurance dimensions remain source-neutral.

## Accepted repository gate

```text
package: 0.20.0
RBAC changes: none
systemd changes: none
control/mutation markers: none
runtime Proxmox wiring: none
228 passed in 1.34s
```

## Accepted BM2 live gate

```text
source status: COMPLETE
mutation_allowed: false
credential_runtime_approved: false
credential_file_mode_secure: false
TLS verification: false
discovery override used: true
PVE: 9.1.9 / release 9.1
node: delfan / ONLINE
storage: local / dir / backup-enabled
retention: keep-all=1
pbs backend: false
cluster backup jobs: 0
current guests: 12
recovery points: 12
VMs with recovery point in selected scope: 6
VMs without recovery point in complete selected scope: 6
selected-scope UNKNOWN: 0
forbidden projected keys: none
raw URL markers: false
credential material projection: none
```

Current selected-scope recovery-point VMIDs:

```text
100,101,106,107,108,109
```

Current selected-scope negative VMIDs:

```text
102,103,104,105,110,9000
```

Required unknowns remain explicit:

```text
RESTORE_VERIFICATION_NOT_OBSERVED
INTEGRITY_VERIFICATION_NOT_OBSERVED
RPO_RTO_NOT_OBSERVED
SCHEDULED_PROTECTION_NOT_INFERRED
```

## Next slice

Consume this accepted source artifact in a derived-only source-neutral Backup Assurance integration.

VM assets must remain a separate domain from Kubernetes PVC assets. Do not invent a VMID-to-PVC relation.

The integration may strengthen facts such as observed backup mechanism and last observed recovery point while preserving restore/integrity/RPO/RTO as unknown. Selected-scope absence remains scoped evidence rather than universal `UNPROTECTED`.

No new Proxmox query, credential, RBAC, systemd wiring, or infrastructure mutation belongs in that integration slice.
