# Milestone 5 — Failure-Domain Access-Path Discovery

Date: 2026-08-23
Status: ACCEPTED
Mode: read-only

## Scope

This discovery correlates hash-verified accepted VM backup assurance with bounded live PVE VM configuration metadata to determine logical node/storage-ID coupling for VMs that already have an accepted recovery-point mechanism.

It does not inspect or classify physical disks, RAID groups, mounts, devices, racks, facilities, or backup media topology.

## Accepted live evidence

Focused tests:

```text
4 passed in 0.06s
```

Accepted source verification and live relationship:

```text
/tmp/vm-backup-assurance.json: hash_match=True
accepted_assets_with_recovery_point_mechanism: 6
runtime_credential_approved: False
live_vm_config_observed: 6
live_vm_config_failed_to_observe: 0
same_pve_node_observed: 6
storage_id_overlap_observed: 6
not_separated_at_pve_node_and_storage_id: 6
not_separated_at_pve_node_layer_only: 0
separated_at_observed_node_and_storage_id_layer: 0
logical_access_path_separation_unknown: 0
physical_failure_domain_independence_claims: 0
restore_verification_claims: 0
unprotected_claims: 0
rpo_violation_claims: 0
discovery_rc: 0
```

Per-VM accepted relationship:

```text
VMID 100: same PVE node=True, VM storage=local, backup storage=local, overlap=local, logical access-path separation=NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID
VMID 101: same PVE node=True, VM storage=local, backup storage=local, overlap=local, logical access-path separation=NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID
VMID 106: same PVE node=True, VM storage=local, backup storage=local, overlap=local, logical access-path separation=NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID
VMID 107: same PVE node=True, VM storage=local, backup storage=local, overlap=local, logical access-path separation=NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID
VMID 108: same PVE node=True, VM storage=local, backup storage=local, overlap=local, logical access-path separation=NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID
VMID 109: same PVE node=True, VM storage=local, backup storage=local, overlap=local, logical access-path separation=NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID
```

## Accepted interpretation

For all six VMs with accepted recovery-point mechanisms, the current VM storage relationship and accepted backup storage mechanism are logically coupled at both the PVE node layer and storage-ID layer.

```text
logical access-path separation: NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID for 6/6
physical failure-domain independence: UNKNOWN
```

This is stronger than the earlier same-storage-ID relationship because current live VM config was observed for all six accepted assets. It is still not evidence that VM data and backup data reside on the same physical disk or RAID group.

## Trust boundary

Only the hash-verified accepted VM assurance artifact and GET/read-only PVE VM config metadata were used.

Raw VM config values, disk volume names, paths, device identifiers, serials, mountpoints, endpoints, credentials, and backup contents were not printed or persisted. No VM, storage, backup, or infrastructure state was changed.

## Milestone effect

The logical failure-domain relationship is now characterized for the six accepted VM recovery mechanisms. Physical failure-domain independence remains `UNKNOWN` and requires stronger authoritative topology evidence if it is to be resolved.

The remaining Milestone 5 gaps are retention effectiveness, accepted RPO/RTO targets and evaluation, and restore/integrity verification. Under the current read-only boundary, restore exercises remain deferred and no RPO/RTO evaluation is possible without authoritative targets.
