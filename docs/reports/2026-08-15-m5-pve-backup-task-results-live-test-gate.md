# Milestone 5 PVE Backup Task Results Live Test Gate — 2026-08-15

## Status

Pending repository and manual live acceptance.

## Scope

Validate package `0.22.0` and `pve_backup_task_results_version=0.1` against BM2 PVE using the already accepted recovery-point source artifact.

The collector remains manual-only.

## Repository gate

Required:

- full pytest suite passes;
- schema validation passes;
- no Kubernetes RBAC change;
- no systemd wiring;
- no runtime Proxmox credential wiring;
- no control/mutation HTTP methods;
- no raw task-log endpoint;
- current package version is `0.22.0` only in the current-slice wiring test.

## Manual live gate

Inputs:

```text
/tmp/proxmox-ve-backup-evidence.json
/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env
```

Expected current source identity:

```text
source_id: pve-bm2
node: delfan
PVE recovery-point source status: COMPLETE
```

Manual execution must use explicit discovery overrides because the current credential is not runtime-approved.

## Trust acceptance

Validate:

```text
pve_backup_task_results_version: 0.1
mutation_allowed: false
source.status: COMPLETE
source.historical_completeness: NOT_ESTABLISHED
source.runtime_credential_approved: false
observation.status: COMPLETE
```

The source artifact must remain unchanged during task-result collection.

Persist only bounded safe task fields:

```text
task_result_id
task_type
node
vmid
start_time
end_time
result
```

No complete UPID, user/token identity, raw error/status text, task log, command line, URL, or credential material may enter output.

## Current expected correlation behavior

The discovery preflight observed 22 successful returned `vzdump` tasks.

For current retained recovery points, strict matches should occur only when same-VMID successful task start time is within two seconds of recovery-point creation.

Based on the accepted preflight:

```text
strict matches expected: 9
no strict match in returned history expected: 3
```

Do not hard-code timestamps into source semantics; the live gate should derive and print current values.

The three older recovery points outside the returned task-history range must not be attached to a distant nearest task.

## Safety gate

No backup, restore, snapshot, prune, verify, GC, schedule, ACL, credential, VM, Kubernetes, or PVE configuration mutation is allowed.

No task log endpoint is allowed.

No runtime wiring is allowed.

A missing historical task must remain an unknown/history-retention limitation, not a failed-backup conclusion.

## Acceptance result

Pending.
