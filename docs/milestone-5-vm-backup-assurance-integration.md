# Milestone 5 — VM Backup Assurance Integration

## Status

Accepted on 2026-08-15.

## Goal

Consume accepted Proxmox VE recovery-point source evidence and derive a source-neutral VM Backup and Recovery Assurance view without performing another infrastructure query.

## Input

Accepted source artifact:

```text
proxmox_ve_backup_evidence_version: 0.1
source: PROXMOX_VE/pve-bm2
source status: COMPLETE
```

The integration assumes the source artifact itself has already passed its trust/schema/live gate.

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

## Accepted live projection

The accepted source artifact contained 12 current VMs and 12 recovery-point records.

Observed recovery-point VMIDs:

```text
100,101,106,107,108,109
```

Complete selected-scope negative VMIDs:

```text
102,103,104,105,110,9000
```

Accepted summary:

```text
assets_total: 12
recovery_point_observed: 6
scoped_negative_recovery_point: 6
recovery_point_unknown: 0
backup_mechanism_observed: 6
retention_configuration_observed: 12
protection_unknown: 12
restore_verification_unknown: 12
integrity_verification_unknown: 12
rpo_unknown: 12
rto_unknown: 12
unprotected_claims: 0
authoritative_source_artifacts_consumed: 1
kubernetes_pvc_assets_modified: 0
```

The source artifact SHA-256 remained unchanged before and after derivation.

## Unknowns retained

The integration explicitly retains:

- source artifact freshness unknown because v0.1 has no TTL contract;
- other backup sources not evaluated;
- restore/integrity/RPO/RTO unknown;
- last successful backup task/result not observed;
- failure-domain evidence not observed;
- scheduled protection not established.

## Trust boundaries

- no network/API client in the integration;
- no subprocess/control CLI;
- no credential access;
- no systemd wiring;
- no RBAC change;
- no infrastructure mutation;
- no PVC artifact mutation;
- source-scoped negative evidence is not universal absence;
- source-native archive `protected` is not consumed as platform protection status;
- no sensitive/raw source fields are projected.

## Future PBS compatibility

PBS remains a separate source adapter with explicit source-specific provenance. It can populate the same common assurance dimensions without changing VM asset identity or the assurance contract.

## Acceptance

Accepted repository/live results:

```text
package: 0.21.0
240 passed in 1.25s
RBAC changes: none
systemd changes: none
query/control/credential markers: none
source artifact unchanged: true
VM asset set exact source match: true
unprotected claims: 0
Kubernetes PVC assets modified: 0
forbidden projected keys: none
raw URL markers: false
PR #35 LIVE ACCEPTANCE: PASS
```

## Next useful evidence

The smallest useful next VM-backup evidence should address a remaining assurance gap rather than repeat recovery-point inventory. Prefer bounded authoritative backup task-result evidence that can support or reject `LAST_SUCCESSFUL_BACKUP` semantics for observed PVE archives, while preserving read-only and source-scoped failure semantics.
