# ADR 0025 — Observe Bounded PVE VM Storage Relationships

## Status

Accepted.

Accepted by the full repository gate and live BM2 source-artifact gate on 2026-08-16.

## Context

Accepted VM Backup Assurance v0.2 keeps `BACKUP_FAILURE_DOMAIN` unknown.

The accepted recovery-point source shows current PVE backups in:

```text
source_id: pve-bm2
node: delfan
backup storage ID: local
```

A bounded manual preflight inspected only safe primary-storage identity for the 12 accepted VMIDs. It found that every VM's resolved primary disk storage ID was also `local`, with no direct/unresolved disk devices.

The versioned source collector implemented by this ADR was then validated live against BM2 and reproduced the same bounded result.

PVE storage configuration did not explicitly return shared status for `local`.

Therefore the evidence supports a statement about PVE storage identifiers, but not a statement about physical disks, controllers, host-locality, power domains, or independent recovery failure domains.

## Decision

Add a separate manual-only Proxmox VE source artifact:

```text
pve_vm_storage_relationship_version: 0.1
mutation_allowed: false
```

The collector is given an explicit source ID, PVE node, backup storage ID, and bounded VMID list.

It performs read-only HTTP GET observations for:

```text
/api2/json/version
/api2/json/cluster/resources?type=vm
/api2/json/storage
/api2/json/nodes/<node>/qemu/<vmid>/config
/api2/json/nodes/<node>/lxc/<vmid>/config
```

Only the required guest configuration endpoint is queried for each selected VM.

## Accepted live result

The accepted live gate produced:

```text
package: 0.24.0
repository tests: 273 passed
source status: COMPLETE
schema validation: PASS
target_vms: 12
config_complete: 12
same_pve_storage_id_as_backup: 12
different_pve_storage_id_from_backup: 0
unknown: 0
failed_to_observe: 0
direct_or_unresolved_disks: 0
referenced_storage_ids: 1
backup storage ID: local
primary storage ID for all selected VMs: local
local storage type: dir
local shared status: NOT_EXPLICITLY_RETURNED
mutation_allowed: false
credential_runtime_approved: false
```

The accepted VMIDs are:

```text
100,101,102,103,104,105,106,107,108,109,110,9000
```

## Safe projection

Raw guest configuration is processed only in memory.

Persisted VM fields are limited to:

```text
vmid
node
guest_type
config_observation_status
primary_disk_devices_observed
managed_primary_disk_count
direct_or_unresolved_disk_count
primary_storage_ids
backup_storage_id
relationship_status
reason
basis
```

Persisted storage metadata is limited to:

```text
storage_id
metadata_status
storage_type
shared_status
node_restrictions_status
node_restrictions
images_content_enabled
backup_content_enabled
disabled
```

The collector must never persist raw VM config, raw disk strings, volume IDs, paths, serials, cloud-init values, networks, MAC/IP values, snippets, URLs, token material, or credentials.

## Disk-device boundary

For this slice, the safe primary-storage projection considers:

```text
QEMU: ide*, sata*, scsi*, virtio* guest data disk devices
LXC: rootfs and mp* storage devices
```

QEMU CD-ROM and cloud-init devices are excluded from the primary data-disk scope.

A direct device or a value that cannot be safely mapped to a PVE storage identifier increments `direct_or_unresolved_disk_count`; its raw value is discarded.

## Relationship semantics

The source-level relationship is one of:

```text
SAME_PVE_STORAGE_ID_AS_BACKUP
DIFFERENT_PVE_STORAGE_ID_FROM_BACKUP
UNKNOWN
FAILED_TO_OBSERVE
```

`SAME_PVE_STORAGE_ID_AS_BACKUP` means only that every safely resolved primary storage ID equals the selected backup storage ID.

`DIFFERENT_PVE_STORAGE_ID_FROM_BACKUP` means every safely resolved primary storage ID differs from the selected backup storage ID.

Mixed IDs, unresolved/direct disks, missing current targets, or unsupported/insufficient evidence remain `UNKNOWN`.

A failed guest-config GET is `FAILED_TO_OBSERVE`.

## Failure-domain boundary

This source artifact does not promote VM Backup Assurance.

In particular:

```text
BACKUP_FAILURE_DOMAIN remains UNKNOWN
```

Same PVE storage ID is not proof of the same physical disk or hardware failure domain.

Different PVE storage IDs are not proof of independent failure domains.

Storage name or type is not interpreted as node-local/shared when authoritative metadata does not explicitly establish that property.

## Credential and runtime boundary

The collector reuses the existing PVE discovery credential gate.

The current BM2 credential is not runtime-approved. Its env file and TLS posture still require explicit discovery overrides.

The collector remains manual-only and is not added to systemd.

## Rejected alternatives

### Infer `local` + `dir` as node-local failure domain

Rejected because storage naming/type does not prove physical or shared scope.

### Persist raw VM configuration for later analysis

Rejected because it creates unnecessary sensitive-data exposure and is not required for the bounded join.

### Promote `BACKUP_FAILURE_DOMAIN` in the same slice

Rejected because identifier equality is weaker than failure-domain evidence.

## Consequences

The platform now has an accepted, versioned, testable source artifact for the observed PVE storage-ID relationship without overstating recovery assurance.

The current PVE failure-domain question remains partially evidenced but not resolved. A future assurance promotion requires a separate evidence contract with stronger authoritative locality/failure-domain evidence.
