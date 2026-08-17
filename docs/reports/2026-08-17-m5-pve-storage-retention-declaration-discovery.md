# Milestone 5 — PVE Storage-Level Retention Declaration Discovery

Date: 2026-08-17

Status: ACCEPTED

## Scope

Bounded read-only discovery of current PVE storage-level retention declaration for storage target(s) containing accepted VM recovery-point evidence.

This slice does not evaluate retention effectiveness, pruning execution, restore viability, integrity, RPO, RTO, or protection state.

## Accepted source boundary

Accepted VM backup assurance source:

```text
/tmp/vm-backup-assurance.json
sha256: 14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a
```

Authoritative live PVE source:

```text
GET /api2/json/storage
```

Existing PVE credentials remained discovery-only:

```text
runtime_credential_approved: false
```

## Discovery correction history

The first implementation incorrectly attempted to read top-level recovery-point storage IDs from the accepted VM assurance artifact. That artifact is derived assurance and does not expose top-level `recovery_points`.

The first retry then correctly targeted preserved `assurance.backup_mechanisms[*].storage_id`, but incorrectly required `vm_backup_assurance_version=0.2`.

A bounded shape probe over the accepted artifact established the actual safe structure:

```text
vm_backup_assurance_version: 0.1
assets_total: 12
assets_with_source_recovery_point_ids: 6
source_recovery_point_id_count: 12
assets_with_backup_mechanisms: 6
backup_mechanism_rows: 6
backup_mechanism_storage_id_present: 6
backup_mechanism_types: PROXMOX_VE_STORAGE_ARCHIVE=6
backup_mechanism_basis_shapes: RECOVERY_POINT_OBSERVED_IN_SOURCE_SCOPE=6
```

No recovery-point IDs, storage IDs, task IDs, timestamps, paths, endpoints, credentials, or backup contents were printed by the shape probe.

The retry extractor was then corrected to consume the accepted VM Backup Assurance v0.1 structure.

## Regression test

```text
2 passed in 0.03s
```

## Accepted live result

```text
retry_basis: VM_BACKUP_ASSURANCE_V0.1_PRESERVED_RECOVERY_POINT_STORAGE_MECHANISM
/tmp/vm-backup-assurance.json: hash_match=True
accepted_recovery_point_storage_ids: 1
accepted_recovery_point_storage_id_list: local

operation: GET /storage
http_status: 200
runtime_credential_approved: False
storage_config_source_status: COMPLETE

storage=local type=dir backup_content=True disabled=False accepted_recovery_point_target=True retention=prune-backups=keep-all=1

storage=local config_status=OBSERVED backup_content=True disabled=False retention_declaration=PRUNE_BACKUPS_DECLARED retention_value=keep-all=1

storage_config_rows_projected: 1
backup_capable_storages: 1
accepted_recovery_point_storage_ids: 1
accepted_target_configs_observed: 1
accepted_targets_with_prune_backups_declared: 1
accepted_targets_with_legacy_maxfiles_declared: 0
accepted_targets_without_explicit_retention_field: 0
retention_effectiveness_claims: 0
unprotected_claims: 0
rpo_violation_claims: 0
discovery_rc: 0
```

## Interpretation

Accepted current declared state:

```text
accepted recovery-point storage target: local
storage type: dir
backup content enabled: true
storage disabled: false
storage-level retention declaration: OBSERVED
retention declaration: prune-backups=keep-all=1
```

The declaration is not retention-effectiveness evidence. It does not establish that pruning has executed as intended, that expected recovery points remain available, that backup history is complete, or that restore is viable.

No `UNPROTECTED`, retention-effectiveness, RPO-violation, restore, or RTO claim is promoted by this slice.

## Trust boundary

Only GET/read-only PVE API calls were used.

No storage paths, mountpoints, endpoints, server addresses, credentials, raw storage objects, backup contents, VM configuration, or connection strings were printed.

No storage, retention, backup, schedule, or infrastructure state was changed.

`mutation_allowed=false` remains the project operating boundary.
