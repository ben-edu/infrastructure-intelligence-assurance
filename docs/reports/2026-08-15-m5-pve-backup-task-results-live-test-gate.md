# Milestone 5 PVE Backup Task Results Live Test Gate — 2026-08-15

## Status

Accepted.

## Scope

Validated package `0.22.0` and `pve_backup_task_results_version=0.1` against BM2 PVE using the already accepted recovery-point source artifact.

The collector remains manual-only.

## Accepted repository gate

```text
RBAC changes: none
systemd changes: none
missing required markers: none
runtime wiring: none
control/mutation markers: none
249 passed in 1.61s
```

The accepted PVE recovery-point source artifact remained byte-identical during collection:

```text
SHA-256 before: 7cd293e49ff09bb7bfb89493b288aae198930dff7f5c1c3c6a73e0fa6732e826
SHA-256 after:  7cd293e49ff09bb7bfb89493b288aae198930dff7f5c1c3c6a73e0fa6732e826
```

## Accepted live source result

```text
source_id: pve-bm2
node: delfan
source status: COMPLETE
operation: GET_BOUNDED_VZDUMP_TASK_RESULTS
request mode: SERVER_FILTERED_VZDUMP
task limit: 500
limit saturated: false
historical completeness: NOT_ESTABLISHED
runtime credential approved: false
credential file mode secure: false
TLS verification: false
discovery override used: true
```

Observation:

```text
operation: GET_VZDUMP_TASK_RESULTS
status: COMPLETE
HTTP status: 200
rows returned: 22
```

All 22 projected returned `vzdump` task records normalized to `SUCCESS`.

Persisted task fields remained bounded to:

```text
task_result_id
task_type
node
vmid
start_time
end_time
result
```

## Accepted recovery-point correlation

Current retained recovery-point correlation:

```text
strict success matches: 9
no strict match in returned history: 3
```

Strict matches occurred only for same-VMID successful task start times within the accepted two-second threshold. Observed deltas were 0 or 1 second.

The three older retained points remained explicitly unmatched:

```text
VMID 106 2025-11-24T08:50:52Z -> NO_STRICT_MATCH_IN_RETURNED_HISTORY
VMID 107 2025-11-21T10:19:36Z -> NO_STRICT_MATCH_IN_RETURNED_HISTORY
VMID 108 2025-11-21T10:29:32Z -> NO_STRICT_MATCH_IN_RETURNED_HISTORY
```

No nearest-task heuristic was used for those older records.

## History semantics

`TASK_HISTORY_COMPLETENESS_NOT_ESTABLISHED` remains explicit.

The returned row count did not saturate the configured limit, so `TASK_RESULT_LIMIT_SATURATED` was not emitted. This does not establish complete historical retention.

A missing historical task remains an unknown/history-retention limitation, not failed-backup evidence.

## Safety acceptance

```text
forbidden projected keys: none
raw URL markers: false
credential material projection: none
restore/integrity/RPO/RTO promotion: none
```

No raw task log endpoint, complete UPID, user/token identity, raw error/status text, command line, URL, credential material, or raw API payload entered the artifact.

No backup, restore, snapshot, prune, verify, GC, schedule, ACL, credential, VM, Kubernetes, systemd, RBAC, or PVE configuration mutation occurred.

## Acceptance meaning

The source artifact is accepted as bounded authoritative PVE task-result evidence for returned `vzdump` records.

A later derived slice may strengthen `LAST_SUCCESSFUL_BACKUP` only for recovery points carrying `STRICT_SUCCESS_TASK_MATCH`. The three unmatched historical recovery points must remain unknown for task-result support. Restore verification, integrity verification, RPO, RTO, and universal protection remain outside this acceptance.
