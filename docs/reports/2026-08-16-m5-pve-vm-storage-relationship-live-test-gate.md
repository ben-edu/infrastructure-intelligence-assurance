# Milestone 5 PVE VM Storage Relationship Live Test Gate — 2026-08-16

## Status

Accepted.

The bounded manual preflight and the versioned live source-artifact collector have both passed against BM2.

## Rejected first repository-gate attempt

The first full repository gate on `mgmt-automation` was rejected before any live collector execution:

```text
272 passed
1 failed
```

The only failure was a stale regression assertion in `tests/test_vm_last_successful_backup_integration_wiring.py` that hard-coded package version `0.23.0` even though this slice intentionally advances the package to `0.24.0`.

The correct invariant is package-version synchronization plus preservation of the previous integration CLI, not freezing the package version. The test was corrected accordingly.

Because the interactive shell had `set -euo pipefail`, that pytest failure terminated the SSH shell before live collection. No new PVE observation was made in that rejected attempt.

## Accepted repository gate

The corrected branch was pulled on `mgmt-automation` at:

```text
43e8604 Refresh PR43 handoff after rejected repository gate
```

Full repository result:

```text
273 passed in 1.23s
```

Package version:

```text
0.24.0
```

## Accepted live collector

The manual source-tree collector was run against:

```text
source_id: pve-bm2
node: delfan
backup storage ID: local
VMIDs: 100,101,102,103,104,105,106,107,108,109,110,9000
```

The existing discovery-only credential boundary was preserved.

Accepted source metadata:

```text
pve_vm_storage_relationship_version: 0.1
source status: COMPLETE
mutation_allowed: false
runtime credential approved: false
```

Accepted summary:

```text
target_vms: 12
config_complete: 12
same_pve_storage_id_as_backup: 12
different_pve_storage_id_from_backup: 0
unknown: 0
failed_to_observe: 0
direct_or_unresolved_disks: 0
referenced_storage_ids: 1
```

Every selected VM produced:

```text
relationship_status: SAME_PVE_STORAGE_ID_AS_BACKUP
primary_storage_ids: [local]
backup_storage_id: local
unresolved_disks: 0
```

Accepted storage metadata projection:

```text
storage_id: local
metadata_status: OBSERVED
storage_type: dir
shared_status: NOT_EXPLICITLY_RETURNED
node_restrictions: none returned
```

## Schema gate

The generated live artifact validated against:

```text
schemas/proxmox-ve-vm-storage-relationship.schema.json
```

Result:

```text
schema: PASS
version: 0.1
mutation_allowed: false
source status: COMPLETE
target_vms: 12
same: 12
different: 0
unknown: 0
failed_to_observe: 0
direct_or_unresolved_disks: 0
```

## Safety acceptance

The collector remained HTTP GET only and manual-only.

No VM, storage, backup, snapshot, schedule, ACL, token, Kubernetes, systemd, RBAC, or other infrastructure mutation occurred.

The persisted artifact contains no raw VM config, raw disk strings, volume IDs, paths, serials, cloud-init values, network configuration, MAC/IP values, snippets, URLs, credentials, token material, or raw API payloads.

## Trust interpretation

This gate accepts one bounded statement:

```text
For the accepted live snapshot, all 12 selected VMs reference the same PVE storage ID (`local`) for their safely resolved primary disks as the selected backup storage ID.
```

It does not prove that primary disks and backup archives occupy the same physical disk, controller, host-local hardware, power domain, or other physical failure domain.

It does not prove failure-domain separation.

The source did not explicitly return shared status for `local`, and the platform must not infer node-locality from `storage_id=local` or `storage_type=dir`.

Therefore:

```text
BACKUP_FAILURE_DOMAIN remains UNKNOWN
```

A future promotion requires a separate accepted evidence contract with stronger authoritative failure-domain evidence.
