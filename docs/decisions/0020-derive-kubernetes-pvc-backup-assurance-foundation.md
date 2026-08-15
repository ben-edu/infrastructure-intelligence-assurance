# ADR 0020 — Derive Kubernetes PVC Backup-Assurance Foundation Before Backup-System Integration

Status: Proposed; pending repository and management-host live acceptance.

## Context

Milestone 5 requires backup and recovery assurance for stateful assets. The platform already has accepted read-only Kubernetes evidence for PersistentVolumeClaims and direct workload-to-PVC controller-spec references. It does not yet have an authoritative backup-system source for Kubernetes PVC data.

A PVC being `Bound`, having a StorageClass, belonging to a StatefulSet-like workload, or having a storage volume identifier is not evidence that the data is backed up, retained correctly, stored in another failure domain, integrity-checked, or restorable.

Starting Milestone 5 by integrating multiple backup engines would broaden credentials and implementation scope before the asset/protection semantics are proven.

## Decision

Add a derived-only Backup and Recovery Assurance foundation artifact for Kubernetes PVC assets.

Read only accepted local artifacts:

```text
kubernetes.json
topology.json
```

Do not issue any new Kubernetes, storage, backup, Proxmox/PBS, database, network, or shell query.

Each currently observed PVC from a complete PVC collection becomes a `KUBERNETES_PVC` stateful asset candidate.

Direct `WORKLOAD_REFERENCES_PVC` topology relations may be attached as workload context. Absence of such a relation is not an orphan classification because Pod-level mounts, generated StatefulSet claims, Jobs, and other consumers may be outside the current controller relationship model.

## Protection semantics

This foundation slice does not integrate an authoritative backup source.

Therefore every observed asset must remain:

```text
protection_status: UNKNOWN
backup_freshness_status: UNKNOWN
integrity_verification_status: UNKNOWN
restore_verification_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

The schema intentionally prevents `PROTECTED`, `PARTIALLY_PROTECTED`, `UNPROTECTED`, `BACKUP_STALE`, `RESTORE_UNVERIFIED`, or `RPO_VIOLATION` from being emitted by this first slice.

`UNKNOWN` means the required authoritative backup evidence has not been integrated. It does not mean no backup exists.

`UNPROTECTED` may only be introduced in a later accepted slice when complete authoritative backup evidence is sufficient to support that conclusion.

## Required future evidence

For each asset, keep explicit requirements for authoritative evidence covering:

- backup mechanism;
- latest successful backup;
- retention / retained recovery points;
- failure-domain separation;
- integrity verification;
- actual restore test;
- RPO target and observed result;
- RTO target and observed restore result.

A backup that has never been successfully restored is not fully verified protection.

## Source and failure semantics

PVC asset existence is trusted only from the PVC collection state:

- complete PVC collection: current PVC asset set may be derived;
- failed PVC collection: asset existence for the cycle is `FAILED_TO_OBSERVE`, not zero assets;
- stale successful PVC evidence remains stale observed evidence, not current evidence.

Workload-to-PVC relationship coverage is separate. It is complete only when the PVC plus Deployment, StatefulSet, and DaemonSet collection scopes are complete. Incomplete relationship scope must not suppress observed PVC assets or create orphan claims.

## Safe projection

Persist only the existing bounded PVC fields required for asset context:

```text
phase
storage_class
access_modes
requested_storage
capacity
volume_name
```

Do not use labels, annotations, naming conventions, snapshots, or storage metadata as backup-protection evidence.

## Consequences

The operator gains a clear inventory of stateful Kubernetes assets that need assurance and a precise list of missing backup evidence without premature credential expansion or false protection claims.

The slice is intentionally a semantic and asset-discovery foundation for later authoritative backup-source integrations such as PBS/Proxmox or database-native tooling where justified by live infrastructure evidence.
