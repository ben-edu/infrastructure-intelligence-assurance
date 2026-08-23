# Milestone 5 — External Backup Target Discovery

Date: 2026-08-23
Status: ACCEPTED
Mode: read-only

## Scope

This discovery inspected the authoritative PVE storage configuration using `GET /storage` and projected only safe backup-target metadata.

## Accepted live evidence

Focused safety tests:

```text
2 passed in 0.13s
```

Live discovery:

```text
operation: GET /storage
http_status: 200
runtime_credential_approved: False
storage_config_source_status: COMPLETE

storage=local type=dir backup_content=True disabled=False target_classification=PATH_BASED_LOCATION_UNKNOWN

storage_config_rows_projected: 1
backup_capable_targets_total: 1
enabled_backup_capable_targets: 1
pbs_like_enabled_targets: 0
network_storage_like_enabled_targets: 0
path_based_location_unknown_enabled_targets: 1
other_storage_type_unknown_enabled_targets: 0
external_target_presence_claims: 0
failure_domain_independence_claims: 0
restore_verification_claims: 0
unprotected_claims: 0
external_backup_target_status: NONE_OBSERVED_IN_BOUNDED_PVE_STORAGE_SCOPE
discovery_rc: 0
```

## Accepted interpretation

```text
current backup-capable PVE targets: 1
PBS-like enabled targets: NONE_OBSERVED
network-storage-like enabled targets: NONE_OBSERVED
path-based target: local / dir
external backup target: NONE_OBSERVED_IN_BOUNDED_PVE_STORAGE_SCOPE
physical failure-domain independence: UNKNOWN
```

A `dir` storage type cannot establish whether the backing location is physically local, a separately mounted device, or another externally backed path. Therefore the target is not promoted to either `LOCAL_PHYSICAL_STORAGE` or `EXTERNAL_STORAGE`.

`NONE_OBSERVED_IN_BOUNDED_PVE_STORAGE_SCOPE` is bounded negative evidence only. It is not proof that no external backup system exists elsewhere in the infrastructure.

## Trust boundary

Only GET/read-only PVE API calls were used. Output was restricted to storage ID, storage type, backup-content capability, disabled state, and derived type classification.

No server, endpoint, path, mountpoint, portal, datastore connection details, usernames, passwords, tokens, fingerprints, credentials, raw storage objects, or backup contents were printed or persisted.

No storage, backup, retention, or infrastructure state was changed.

## Next bounded step

Derive a failure-domain access-path relationship from accepted evidence without claiming physical media independence. Determine whether protected VM location, accepted recovery-point storage, PVE node, and storage ID are logically coupled. Preserve physical failure-domain independence as `UNKNOWN` unless stronger authoritative evidence is obtained.