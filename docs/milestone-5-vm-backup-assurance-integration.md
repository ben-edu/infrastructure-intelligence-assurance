# Milestone 5 — VM Backup Assurance Integration

## Goal

Consume accepted Proxmox VE recovery-point source evidence and derive a source-neutral VM Backup and Recovery Assurance view without performing another infrastructure query.

## Input

Accepted source artifact:

```text
proxmox_ve_backup_evidence_version: 0.1
```

The integration assumes the source artifact itself has already passed its own trust/schema/live gate.

## Output

```text
vm_backup_assurance_version: 0.1
mutation_allowed: false
scope.asset_type: VIRTUAL_MACHINE
scope.derived_only: true
scope.source_neutral_assurance: true
scope.kubernetes_pvc_assurance_modified: false
```

The artifact is deliberately separate from the Kubernetes PVC Backup Assurance artifact.

## VM identity

A VM asset is identified by bounded source identity:

```text
system: proxmox_ve
source_id
kind: VirtualMachine
node
vmid
guest_type
guest_status
```

No guest name is required and no VMID-to-Kubernetes-PVC relation is inferred.

## Recovery-point semantics

For an observed recovery point:

```text
recovery_point_status: OBSERVED
backup_mechanism_status: OBSERVED
backup_mechanism.type: PROXMOX_VE_STORAGE_ARCHIVE
latest_recovery_point_at: observed timestamp
protection_status: UNKNOWN
```

For a complete selected scope with no observed point:

```text
recovery_point_status: NOT_OBSERVED_IN_COMPLETE_SELECTED_SCOPE
backup_mechanism_status: UNKNOWN
protection_status: UNKNOWN
```

For incomplete/failed selected-source evidence:

```text
recovery_point_status: UNKNOWN
protection_status: UNKNOWN
```

## Common assurance dimensions

Every VM retains:

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

Dimension status is one of:

```text
OBSERVED
PARTIAL
REQUIRED
```

Current PVE recovery-point evidence may satisfy `BACKUP_MECHANISM`. Retention configuration may make `BACKUP_RETENTION` partial. Archive presence is not promoted to `LAST_SUCCESSFUL_BACKUP` because task-result semantics are not observed in this source artifact.

## Unknowns retained

The integration explicitly retains:

- source artifact freshness unknown because v0.1 has no TTL contract;
- other backup sources not evaluated;
- restore/integrity/RPO/RTO unknown.

## Trust boundaries

- no network/API client in the integration;
- no subprocess/control CLI;
- no credential access;
- no systemd wiring;
- no RBAC change;
- no infrastructure mutation;
- no PVC artifact mutation;
- source-scoped negative evidence is not universal absence;
- source-native archive `protected` is not consumed as platform protection status.

## Future PBS compatibility

PBS remains a separate source adapter with explicit source-specific provenance. It can populate the same common assurance dimensions without changing VM asset identity or the assurance contract.

## Acceptance

Repository acceptance must prove:

- package `0.21.0`;
- full tests pass;
- schema validation passes;
- integration is derived-only and contains no query-capable client/control markers;
- systemd and Kubernetes RBAC are unchanged;
- previous PVE source adapter and PVC foundation contracts remain intact;
- observed recovery points strengthen mechanism/recovery-point evidence only;
- complete selected-scope negatives do not become `UNPROTECTED`;
- failed source evidence remains unknown;
- no unsafe source fields are projected.

Manual derived live acceptance must consume the already-generated `/tmp/proxmox-ve-backup-evidence.json` from the accepted PR #33 live gate and validate the current VM assurance projection without making another Proxmox request.
