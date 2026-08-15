# Milestone 5 Kubernetes Backup Assurance Foundation Live Test Gate — 2026-08-15

## Status

Pending repository and management-host live acceptance.

## Purpose

Validate the first read-only Backup and Recovery Assurance vertical slice: derive current Kubernetes PVC stateful assets from accepted local evidence while refusing to infer backup protection without an authoritative backup source.

## Repository gate

1. `deploy/kubernetes/observer-rbac.yaml` has no diff from `main`.
2. `backup_assurance_foundation.py` contains no subprocess, kubectl, network client, backup-engine client, database client, or live query boundary.
3. Package version is `0.19.0`.
4. Full pytest passes.
5. Schema fixes `backup_assurance_version=0.1`, `mutation_allowed=false`, `derived_only=true`, and `authoritative_backup_source_integrated=false`.
6. Schema permits only `UNKNOWN` foundation protection/restore/RPO states and fixes `unprotected_claims=0`.

## Runtime order

The final systemd post-steps must end with:

```text
prometheus_rule_context
prometheus_rule_context_integration
backup_assurance_foundation
```

All stages must exit `0/SUCCESS` for live acceptance.

## Asset source checks

Compare `backup-assurance.json` directly to the same-cycle `kubernetes.json` and `topology.json`.

If the PVC collection is `COMPLETE`:

- every complete PRESENT PVC envelope must appear exactly once as an asset;
- no other asset may appear;
- PVC asset count must equal the complete observed PVC count;
- source overall is `COMPLETE` when workload/PVC relation collection scope is also complete, otherwise `PARTIAL`;
- a complete zero-PVC collection is a valid zero-asset result.

If PVC collection fails:

- source overall is `FAILED_TO_OBSERVE`;
- asset list must not be interpreted as a complete zero-PVC result;
- an explicit PVC collection unknown must exist.

## Freshness

Every emitted asset freshness must be derived from its exact PVC evidence expiry:

```text
CURRENT
STALE
UNKNOWN
```

Do not convert stale evidence into current state.

## Workload context

Only accepted topology relations with:

```text
type: WORKLOAD_REFERENCES_PVC
basis: OBSERVED_REFERENCE
```

may enter `related_workloads`.

No direct relation must not produce an orphan claim.

Incomplete Deployment/StatefulSet/DaemonSet/PVC collection scope must produce `RELATION_SCOPE_INCOMPLETE`.

## Protection semantics

For every emitted asset:

```text
protection_status: UNKNOWN
backup_freshness_status: UNKNOWN
integrity_verification_status: UNKNOWN
restore_verification_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

And globally:

```text
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
```

`UNKNOWN` must remain explicitly distinct from `UNPROTECTED`.

## Required evidence targets

Each asset must retain exactly these authoritative evidence targets:

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

## Sensitive / false-evidence guard

The foundation artifact must not contain raw Kubernetes labels or annotations, Secret material, tokens, passwords, authorization fields, private keys, complete connection strings, or raw URL markers.

PVC `storage_class`, `phase`, capacity, volume name, workload context, or naming conventions must never alter protection status in this slice.

## Interpretation

Acceptance proves that the platform can identify a bounded class of stateful assets requiring backup assurance and represent missing backup evidence honestly. It does not prove that any asset is protected or unprotected.
