# ADR 0024 — Integrate Strict Backup Task Success into VM Assurance

## Status

Proposed. Repository and manual derived acceptance are required before merge.

## Context

Accepted VM Backup Assurance v0.1 distinguishes observed recovery points from protection quality and keeps `LAST_SUCCESSFUL_BACKUP` unknown.

Accepted PVE Backup Task Results v0.1 provides authoritative returned `vzdump` task-result records and strict recovery-point correlations. The accepted BM2 live gate currently contains 22 successful task results, nine `STRICT_SUCCESS_TASK_MATCH` correlations, and three older retained recovery points with no strict match in returned history.

Task-history completeness remains `NOT_ESTABLISHED`.

## Decision

Add a derived-only VM Backup Assurance integration that consumes:

```text
vm_backup_assurance_version: 0.1
pve_backup_task_results_version: 0.1
```

and emits:

```text
vm_backup_assurance_version: 0.2
last_successful_backup_integration.version: 0.1
last_successful_backup_integration.mode: STRICT_CORRELATION_ONLY
mutation_allowed: false
```

The integration performs no infrastructure, Proxmox, Kubernetes, database, or network query and reads no credential.

## Join boundary

The derived layer does not recalculate correlation by time.

It consumes only accepted `STRICT_SUCCESS_TASK_MATCH` records and validates:

```text
same accepted source identity
recovery-point identity belongs to the VM asset
task-result identity exists
task type is VZDUMP
task result is SUCCESS
task VMID matches correlation VMID
```

A contract mismatch fails the integration rather than creating inferred evidence.

## LAST_SUCCESSFUL_BACKUP semantics

For a VM with one or more valid strict matches:

```text
last_successful_backup_status: OBSERVED
last_successful_backup_at: <latest matched successful task end_time>
```

The bounded evidence projection contains only:

```text
source_type: PROXMOX_VE_VZDUMP_TASK_RESULT
source_id
recovery_point_id
task_result_id
basis: [STRICT_SUCCESS_TASK_MATCH]
```

The common `LAST_SUCCESSFUL_BACKUP` required-evidence dimension becomes `OBSERVED` for that VM.

Task completion time is used because this field represents an authoritative completed successful backup operation, while `latest_recovery_point_at` remains separate recovery-point evidence.

## Unknown semantics

A VM without strict task-result support remains:

```text
last_successful_backup_status: UNKNOWN
last_successful_backup_at: null
```

`NO_STRICT_MATCH_IN_RETURNED_HISTORY` is not failed-backup evidence because historical task retention completeness is not established.

A VM may still have `last_successful_backup_status=OBSERVED` when an older retained recovery point is unmatched, provided a newer retained recovery point has authoritative strict successful-task support.

## Unchanged assurance dimensions

This integration must not alter:

```text
protection_status
integrity_verification_status
restore_verification_status
failure_domain_status
scheduled_protection_status
rpo_status
rto_status
```

Current values therefore remain UNKNOWN/RTO_UNKNOWN.

Recovery-point status, backup-mechanism evidence, and retention context remain as previously derived.

## Freshness and history

PVE task-result source v0.1 has no TTL/expiry contract. Task-result source freshness remains `UNKNOWN`.

`historical_completeness=NOT_ESTABLISHED` is retained explicitly.

## Domain separation and PBS

Kubernetes PVC assurance is not modified.

Future PBS-native task/result evidence may satisfy the same source-neutral `LAST_SUCCESSFUL_BACKUP` dimension through a separate adapter and explicit provenance. The common VM assurance contract must not depend on PVE-specific identifiers beyond source evidence references.

## Consequences

The platform can now distinguish:

- recovery point exists;
- authoritative backup task completed successfully;
- protection quality remains unknown;
- restore/integrity/RPO/RTO remain unknown.

This reduces a real assurance unknown without overstating recoverability.
