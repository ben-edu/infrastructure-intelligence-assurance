# Milestone 5 — Proxmox VE Backup Task Result Evidence

## Goal

Observe bounded authoritative `vzdump` task-result metadata from BM2 PVE and preserve a strict, safe correlation to retained recovery-point evidence.

## Inputs

Accepted source artifact:

```text
proxmox_ve_backup_evidence_version: 0.1
```

Manual discovery credential:

```text
/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env
```

The credential remains discovery-only and is not approved for runtime.

## Output

```text
pve_backup_task_results_version: 0.1
mutation_allowed: false
source.type: proxmox_ve_api
source.operation: GET_BOUNDED_VZDUMP_TASK_RESULTS
source.historical_completeness: NOT_ESTABLISHED
source.runtime_credential_approved: false
```

## Query boundary

Preferred query:

```text
GET /api2/json/nodes/<node>/tasks?typefilter=vzdump&limit=<bounded>
```

If the server rejects `typefilter` with HTTP 400, one bounded task-list GET is allowed and filtering occurs locally.

No task log endpoint is queried.

## Safe task projection

Persist only:

```text
task_result_id
task_type=VZDUMP
node
vmid
start_time
end_time
result
```

Do not persist complete UPIDs, raw task logs, user/token identity, raw error/status text, command lines, URLs, or raw payloads.

## Strict archive/task correlation

A recovery point is correlated only when:

```text
same VMID
successful task
start-time delta <= 2 seconds
```

Anything outside that boundary remains `NO_STRICT_MATCH_IN_RETURNED_HISTORY`.

Do not use nearest-task correlation outside the threshold.

## Current discovery baseline

The accepted preflight observed:

```text
returned vzdump tasks: 22
normalized SUCCESS: 22
returned range: 2026-02-24T10:36:47Z .. 2026-08-14T17:39:32Z
retained recovery points evaluated: 12
strict 0-1 second task/archive candidates: 9
old retained points outside returned history: 3
```

The three older retained recovery points must remain unmatched by this source slice.

## Trust boundaries

- HTTP GET only;
- no backup/restore/snapshot/prune/verify/GC action;
- no schedule, ACL, credential, VM, or PVE configuration mutation;
- no systemd wiring;
- no Kubernetes RBAC change;
- no runtime credential approval;
- task history observation failure is UNKNOWN, not zero tasks;
- historical completeness is not established;
- task SUCCESS is not restore verification.

## Future integration

After this source artifact is separately accepted, a later derived-only VM assurance slice may strengthen `LAST_SUCCESSFUL_BACKUP` using successful task-result evidence.

The integration must preserve source-history limitations and must not strengthen restore, integrity, RPO, or RTO without separate evidence.
