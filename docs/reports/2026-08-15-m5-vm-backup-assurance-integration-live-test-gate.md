# Milestone 5 VM Backup Assurance Integration Live Test Gate — 2026-08-15

## Status

Pending repository and manual derived live acceptance.

## Scope

Validate package `0.21.0` and `vm_backup_assurance_version=0.1` using the already accepted PR #33 Proxmox VE source artifact.

This gate must not make any new Proxmox request and must not use/read any Proxmox credential.

## Repository gate

Required:

- full pytest suite passes;
- schema validation passes;
- integration contains no network/query/control client markers;
- no RBAC change;
- no systemd change;
- prior Proxmox source adapter CLI remains available;
- prior Kubernetes PVC foundation contract remains `KUBERNETES_PVC` and unchanged by this slice;
- package version is `0.21.0` only in current-slice version tests.

## Manual derived live gate

Input:

```text
/tmp/proxmox-ve-backup-evidence.json
```

The input should be the accepted source artifact generated during PR #33 live validation. If it is missing, do not silently rerun the PVE source collector as part of this derived-only gate.

Expected current-source baseline from PR #33:

```text
source: pve-bm2
source status: COMPLETE
current guests: 12
recovery points: 12
VMs with recovery points: 6
VMs with no recovery point in complete selected local scope: 6
```

Counts may change only if a different accepted source artifact is intentionally supplied. The gate should derive values from the supplied artifact rather than hard-code all counts.

## Trust acceptance

Validate:

```text
vm_backup_assurance_version: 0.1
mutation_allowed: false
scope.asset_type: VIRTUAL_MACHINE
scope.derived_only: true
scope.source_neutral_assurance: true
scope.kubernetes_pvc_assurance_modified: false
source_status.source_type: PROXMOX_VE
source_status.source_freshness: UNKNOWN
summary.unprotected_claims: 0
summary.kubernetes_pvc_assets_modified: 0
```

For source records with `RECOVERY_POINT_OBSERVED`:

- VM assurance `recovery_point_status=OBSERVED`;
- `backup_mechanism_status=OBSERVED`;
- mechanism type `PROXMOX_VE_STORAGE_ARCHIVE`;
- latest recovery point and source recovery-point IDs are projected;
- `protection_status=UNKNOWN`;
- `LAST_SUCCESSFUL_BACKUP` remains `REQUIRED`;
- restore/integrity/RPO/RTO remain unknown/required.

For complete selected-source negative records:

- `recovery_point_status=NOT_OBSERVED_IN_COMPLETE_SELECTED_SCOPE`;
- `protection_status=UNKNOWN`;
- no universal `UNPROTECTED` classification.

For unknown/failed source records:

- `recovery_point_status=UNKNOWN`;
- no absence claim.

## Safety gate

The output must not contain source credentials, URLs, raw `volid`, guest names, source raw payloads, storage server/path/username, fingerprints, encryption-key references, Terraform state, or connection strings.

No Proxmox request, backup, restore, snapshot, prune, verify, GC, ACL, credential, RBAC, systemd, Kubernetes PVC, or infrastructure mutation is allowed.

## Acceptance result

Pending.
