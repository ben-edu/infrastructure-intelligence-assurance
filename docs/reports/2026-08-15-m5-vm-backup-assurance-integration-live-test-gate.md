# Milestone 5 VM Backup Assurance Integration Live Test Gate — 2026-08-15

## Status

Accepted.

## Scope

Validated package `0.21.0` and `vm_backup_assurance_version=0.1` using the already accepted PR #33 Proxmox VE source artifact.

No new Proxmox request was made and no Proxmox credential was read by the integration.

## Repository gate

Accepted on `mgmt-automation`:

```text
RBAC changes: none
systemd changes: none
query/control/credential markers: none
missing assurance markers: none
240 passed in 1.25s
```

The accepted source artifact validated before derivation:

```text
source version: 0.1
source status: COMPLETE
source mutation_allowed: false
source guests: 12
source recovery points: 12
```

The SHA-256 of `/tmp/proxmox-ve-backup-evidence.json` was identical before and after derivation:

```text
7cd293e49ff09bb7bfb89493b288aae198930dff7f5c1c3c6a73e0fa6732e826
```

This proves the derived slice did not modify its source artifact.

## Accepted derived artifact

```text
vm_backup_assurance_version: 0.1
mutation_allowed: false
scope.asset_type: VIRTUAL_MACHINE
scope.derived_only: true
scope.source_neutral_assurance: true
scope.kubernetes_pvc_assurance_modified: false
source_type: PROXMOX_VE
source_id: pve-bm2
source status: COMPLETE
source freshness: UNKNOWN
```

The VM asset set exactly matched the 12 current VMIDs in the accepted PVE source artifact:

```text
100,101,102,103,104,105,106,107,108,109,110,9000
```

## Recovery-point assurance

Observed recovery points:

```text
VMID 100 -> 2 points, latest 2026-05-08T06:13:59Z
VMID 101 -> 1 point,  latest 2026-05-08T10:36:12Z
VMID 106 -> 3 points, latest 2026-08-14T16:13:14Z
VMID 107 -> 3 points, latest 2026-08-14T16:40:35Z
VMID 108 -> 2 points, latest 2026-04-15T12:30:02Z
VMID 109 -> 1 point,  latest 2026-04-13T10:34:52Z
```

For these six VM assets:

```text
recovery_point_status: OBSERVED
backup_mechanism_status: OBSERVED
mechanism type: PROXMOX_VE_STORAGE_ARCHIVE
protection_status: UNKNOWN
```

Complete selected-scope negative observations:

```text
VMID 102
VMID 103
VMID 104
VMID 105
VMID 110
VMID 9000
```

For these six assets:

```text
recovery_point_status: NOT_OBSERVED_IN_COMPLETE_SELECTED_SCOPE
backup_mechanism_status: UNKNOWN
protection_status: UNKNOWN
```

This remains a negative fact only for the accepted `pve-bm2/delfan/local` selected scope. It is not universal backup absence.

## Accepted summary

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

Required unresolved evidence remains:

```text
LAST_SUCCESSFUL_BACKUP
BACKUP_INTEGRITY_VERIFICATION
RESTORE_TEST
RPO_TARGET_AND_RESULT
RTO_TARGET_AND_RESULT
```

Retention configuration is partial evidence only; effectiveness remains unknown.

## Trust acceptance

Accepted:

- source artifact unchanged during derivation;
- VM/PVC asset-domain separation preserved;
- no VMID-to-Kubernetes-PVC relation inferred;
- `protection_status=UNKNOWN` for all 12 VM assets;
- no universal `UNPROTECTED` classification;
- `unprotected_claims=0`;
- `kubernetes_pvc_assets_modified=0`;
- source freshness remains `UNKNOWN` because PVE source artifact v0.1 has no TTL contract;
- `LAST_SUCCESSFUL_BACKUP` remains required because archive presence is not task-result success;
- restore/integrity/RPO/RTO remain unknown;
- no source-native archive protection flag is promoted into common assurance output;
- forbidden projected keys: none;
- raw URL markers: false.

No Proxmox request, backup, restore, snapshot, prune, verify, garbage collection, ACL, credential, RBAC, systemd, Kubernetes PVC, or infrastructure mutation occurred.

## Acceptance result

```text
PR #35 LIVE ACCEPTANCE: PASS
```
