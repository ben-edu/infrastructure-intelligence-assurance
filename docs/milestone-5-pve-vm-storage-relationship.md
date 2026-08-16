# Milestone 5 — PVE VM Storage Relationship Evidence

## Goal

Formalize the successful BM2 primary-storage preflight as a bounded, versioned source artifact without promoting physical failure-domain assurance.

## Why this slice exists

VM Backup Assurance v0.2 currently knows that six VMs have strictly supported successful PVE backup tasks, but `BACKUP_FAILURE_DOMAIN` remains unknown for every VM.

Current recovery points are stored in PVE storage ID `local`.

The 2026-08-16 manual preflight safely established that the selected primary VM disk devices also reference PVE storage ID `local` for all 12 accepted VMIDs.

That relationship is useful evidence, but it is weaker than proof that VM disks and backup archives share one physical failure domain.

## Artifact

```text
pve_vm_storage_relationship_version: 0.1
mutation_allowed: false
collector: infra_assurance.proxmox_ve_vm_storage_relationship
```

The artifact contains:

- bounded source identity and observation status;
- explicit target VMIDs and selected backup storage ID;
- safe storage metadata projection;
- per-VM safe primary-storage IDs;
- direct/unresolved disk counts;
- bounded storage-ID relationship status;
- explicit unknowns and caveats.

## Current bounded target

```text
source_id: pve-bm2
node: delfan
backup storage ID: local
VMIDs: 100,101,102,103,104,105,106,107,108,109,110,9000
```

## Safe query boundary

HTTP GET only:

```text
GET /api2/json/version
GET /api2/json/cluster/resources?type=vm
GET /api2/json/storage
GET /api2/json/nodes/delfan/qemu/<vmid>/config
GET /api2/json/nodes/delfan/lxc/<vmid>/config
```

No mutation endpoints are used.

## Safe projection boundary

Allowed persisted VM configuration facts:

```text
vmid
node
guest_type
primary disk device counts
resolved PVE storage IDs
direct/unresolved disk count
storage-ID relationship to the selected backup storage
```

Allowed storage configuration facts:

```text
storage ID
storage type
explicit shared status when returned
explicit node restrictions when returned
images/backup content capability
disabled flag
```

Not persisted:

```text
raw VM config
raw disk strings
volume IDs
paths
serials
cloud-init values
network config
MAC/IP values
snippets
URLs
credentials
raw API payloads
```

## Relationship meanings

### SAME_PVE_STORAGE_ID_AS_BACKUP

All safely resolved primary storage IDs equal the selected backup storage ID.

This is not a physical failure-domain classification.

### DIFFERENT_PVE_STORAGE_ID_FROM_BACKUP

All safely resolved primary storage IDs differ from the selected backup storage ID.

This is not proof of independent failure domains.

### UNKNOWN

Used for mixed primary storage IDs, direct/unresolved disk devices, missing current targets, unsupported target scope, or other insufficient evidence.

### FAILED_TO_OBSERVE

Used when the required VM config observation fails.

## Storage locality semantics

`shared_status` is source-native and explicit:

```text
SHARED
NOT_SHARED
NOT_EXPLICITLY_RETURNED
UNKNOWN
```

The collector does not infer node-locality from `storage_id=local`, `type=dir`, or lack of a returned `shared` field.

## Assurance boundary

This slice produces source evidence only.

It does not modify VM Backup Assurance v0.2 and does not change:

```text
protection_status
integrity_verification_status
restore_verification_status
failure_domain_status
scheduled_protection_status
rpo_status
rto_status
```

In particular, `failure_domain_status` remains `UNKNOWN`.

## Runtime boundary

The current PVE token remains discovery-only and is not runtime-approved.

This collector is manual-only. No systemd wiring is added.

## Acceptance gate

The slice is accepted only after:

1. the full repository test suite passes;
2. schema validation passes;
3. the live manual collector run against BM2 is `COMPLETE`;
4. all 12 current selected VMIDs are represented without raw/sensitive projection;
5. observed storage-ID relationships match the live source evidence;
6. no infrastructure mutation occurs;
7. `BACKUP_FAILURE_DOMAIN` is not promoted.
