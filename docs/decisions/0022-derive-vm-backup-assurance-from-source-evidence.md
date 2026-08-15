# ADR 0022 — Derive VM Backup Assurance from Accepted Source Evidence

## Status

Accepted.

Repository and manual derived live acceptance passed on 2026-08-15.

## Context

ADR 0021 accepted a bounded Proxmox VE recovery-point source artifact without runtime credential wiring. The accepted BM2 source evidence contains current VM inventory, selected-storage scope status, storage retention configuration, and recovery-point metadata.

The Kubernetes PVC Backup Assurance foundation is a separate asset domain and has no accepted VMID-to-PVC identity relation.

The operator also requires future PBS support without redesigning the common assurance model.

## Decision

Add a derived-only `VIRTUAL_MACHINE` Backup Assurance artifact that consumes the accepted Proxmox VE source artifact locally.

Do not modify the Kubernetes PVC assurance artifact or infer a VM-to-PVC relation.

### Derived-only boundary

The integration performs no Proxmox, Kubernetes, database, network, or external-system query.

It reads one accepted local source artifact and emits:

```text
vm_backup_assurance_version: 0.1
asset_type: VIRTUAL_MACHINE
mutation_allowed: false
source_neutral_assurance: true
kubernetes_pvc_assurance_modified: false
```

No systemd/runtime wiring is added because the PVE source collector itself is not runtime-wired.

### Assurance semantics

For a VM with `RECOVERY_POINT_OBSERVED` in the accepted PVE source artifact:

- `backup_mechanism_status=OBSERVED`;
- a source-neutral mechanism record identifies `PROXMOX_VE_STORAGE_ARCHIVE` plus source/node/storage provenance;
- `recovery_point_status=OBSERVED`;
- count and latest observed recovery-point timestamp are projected;
- retention configuration may be `OBSERVED`, while retention effectiveness remains `UNKNOWN`.

Even with an observed recovery point:

```text
protection_status: UNKNOWN
last_successful_backup_status: UNKNOWN
integrity_verification_status: UNKNOWN
restore_verification_status: UNKNOWN
failure_domain_status: UNKNOWN
scheduled_protection_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

Recovery-point presence is not promoted to task-result success, restore verification, integrity verification, RPO compliance, or RTO compliance.

### Scoped negative semantics

For `NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE`:

```text
recovery_point_status: NOT_OBSERVED_IN_COMPLETE_SELECTED_SCOPE
protection_status: UNKNOWN
```

This is authoritative negative evidence only for the exact selected source/node/storage scope. It is not universal backup absence and must not become platform `UNPROTECTED`.

For incomplete/failed source scope:

```text
recovery_point_status: UNKNOWN
protection_status: UNKNOWN
```

### Required-evidence dimensions

Every VM retains the common eight evidence dimensions:

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

Each dimension is classified as `OBSERVED`, `PARTIAL`, or `REQUIRED`.

An observed PVE recovery point may satisfy `BACKUP_MECHANISM`. Observed retention configuration may make `BACKUP_RETENTION` partial. `LAST_SUCCESSFUL_BACKUP` remains required because archive presence is not equivalent to authoritative task-result success.

### Freshness

PVE source artifact v0.1 has no TTL/expiry contract. Derived VM source freshness therefore remains `UNKNOWN` even when the source artifact status is `COMPLETE`.

### Future PBS compatibility

The common VM assurance fields are source-neutral.

Future PBS-native evidence must enter through a separate source adapter and may satisfy the same assurance dimensions. PBS datastore/namespace/snapshot identifiers remain source-specific provenance rather than common VM asset identity.

A VM may eventually have evidence from multiple adapters. Source-scoped negative evidence from PVE local storage must not override stronger positive PBS evidence.

## Accepted evidence

Repository/live gate:

```text
240 passed in 1.25s
source artifact unchanged during derivation: true
source status: COMPLETE
source freshness: UNKNOWN
VM assets: 12
recovery-point observed: 6
complete selected-scope negative: 6
recovery-point unknown: 0
backup mechanism observed: 6
retention configuration observed: 12
protection unknown: 12
restore verification unknown: 12
integrity verification unknown: 12
RPO unknown: 12
RTO unknown: 12
unprotected claims: 0
Kubernetes PVC assets modified: 0
```

The accepted VM asset set exactly matches the 12 source VMIDs. No sensitive/raw source fields were projected and no URL markers were present.

## Consequences

The platform now has a useful VM-level assurance view without broadening infrastructure access or conflating recovery-point existence with verified recoverability.

The accepted Kubernetes PVC assurance artifact remains unchanged.

The next useful VM evidence should strengthen a currently unresolved assurance dimension, preferably authoritative backup task-result evidence for `LAST_SUCCESSFUL_BACKUP`, before adding broader source coverage. Runtime credential wiring remains out of scope until its separate trust prerequisites are met.
