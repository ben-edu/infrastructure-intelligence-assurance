# Milestone 5 — VM Last Successful Backup Integration

## Goal

Use accepted local task-result evidence to strengthen only the `LAST_SUCCESSFUL_BACKUP` assurance dimension for virtual machines with strict authoritative task support.

## Inputs

```text
vm_backup_assurance_version: 0.1
pve_backup_task_results_version: 0.1
```

Both inputs must have `mutation_allowed=false`.

## Output

```text
vm_backup_assurance_version: 0.2
mutation_allowed: false
last_successful_backup_integration.version: 0.1
last_successful_backup_integration.mode: STRICT_CORRELATION_ONLY
```

The output remains a `VIRTUAL_MACHINE` source-neutral Backup Assurance view. Kubernetes PVC assurance remains separate and unchanged.

## Derived-only boundary

The integration contains no network/API client, Proxmox credential access, subprocess/control CLI, RBAC change, systemd wiring, or infrastructure mutation.

It consumes only accepted local JSON artifacts.

## Strict evidence consumption

The integration trusts no new time heuristic. It consumes accepted strict correlation records and validates source/asset/task identities.

Positive support requires:

```text
correlation.status = STRICT_SUCCESS_TASK_MATCH
recovery-point identity belongs to the target VM
task-result identity exists
task type = VZDUMP
task result = SUCCESS
task VMID = target VMID
```

## Strengthened dimension

For a VM with strict support:

```text
last_successful_backup_status: OBSERVED
last_successful_backup_at: <latest matched task completion time>
LAST_SUCCESSFUL_BACKUP dimension: OBSERVED
```

Bounded evidence retains only source identity, recovery-point ID, task-result ID, and `STRICT_SUCCESS_TASK_MATCH` basis.

## Unchanged dimensions

For every VM this slice preserves:

```text
protection_status: UNKNOWN
integrity_verification_status: UNKNOWN
restore_verification_status: UNKNOWN
failure_domain_status: UNKNOWN
scheduled_protection_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

No universal `UNPROTECTED` classification is introduced.

## Historical incompleteness

Task-history completeness remains `NOT_ESTABLISHED`.

An unmatched old retained recovery point is not failed-backup evidence. A VM may still have an observed latest successful backup when a newer recovery point has strict successful-task support.

## Freshness

Task-result source v0.1 has no TTL/expiry contract. The integration records task-result source freshness as `UNKNOWN`.

## Future PBS compatibility

The common assurance dimension is source-neutral. A future PBS task/result adapter can satisfy the same `LAST_SUCCESSFUL_BACKUP` dimension using separate source provenance without redesigning VM assurance.

## Acceptance

Repository/manual-derived acceptance must prove:

- package `0.23.0`;
- full tests pass;
- both source artifacts remain unchanged during derivation;
- no RBAC/systemd/network/credential/control markers are introduced;
- output validates against `vm-last-successful-backup-integration.schema.json`;
- current VM set is unchanged;
- only VMs with valid strict successful-task support become `last_successful_backup_status=OBSERVED`;
- latest success time comes from matched task completion time;
- `LAST_SUCCESSFUL_BACKUP` dimension becomes `OBSERVED` only for supported VMs;
- unmatched historical evidence is not promoted to failure;
- protection/restore/integrity/failure-domain/scheduled-protection/RPO/RTO remain unchanged;
- PVC assurance remains untouched;
- no unsafe source/task/credential fields enter the output.
