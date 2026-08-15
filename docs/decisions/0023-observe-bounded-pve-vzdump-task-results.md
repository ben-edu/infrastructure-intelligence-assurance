# ADR 0023 — Observe Bounded Proxmox VE vzdump Task Results

## Status

Accepted on 2026-08-15 after repository and manual live acceptance.

## Context

PR #33 established authoritative PVE recovery-point source evidence. PR #35 derived VM Backup Assurance but intentionally kept `LAST_SUCCESSFUL_BACKUP` unknown because archive presence is not authoritative task-result success.

A bounded BM2 preflight on 2026-08-15 observed 22 returned `vzdump` task records, all normalized `SUCCESS`, over the returned range 2026-02-24 through 2026-08-14. Nine of the twelve retained recovery points aligned to same-VMID successful task start times within 0–1 seconds. Three older retained recovery points predated the returned task-history range and therefore had no trustworthy historical task match.

Task-history retention completeness is not established.

## Decision

Add a separate source-evidence adapter for bounded PVE `vzdump` task results.

The adapter:

- performs HTTP GET only;
- remains manual-only and is not systemd-wired;
- reuses the existing discovery credential only under explicit manual override;
- rejects automatic runtime credential approval;
- reads the accepted PVE recovery-point artifact to bound VM identity and correlate retained recovery points;
- never queries raw task logs;
- never persists complete UPIDs, user/token identity, raw status/error text, command lines, URLs, or raw API payloads.

## Task result semantics

Returned task rows are normalized to:

```text
SUCCESS
FAILURE
RUNNING_OR_INCOMPLETE
UNKNOWN
```

`SUCCESS` means the returned `vzdump` task record has a completion timestamp and source status `OK`.

This is authoritative task-result evidence for the returned record. It is not restore verification, integrity verification, RPO compliance, or RTO compliance.

## Strict recovery-point correlation

A retained recovery point may correlate to a successful task only when all of the following hold:

```text
same VMID
successful VZDUMP task
absolute(recovery_point.created_at - task.start_time) <= 2 seconds
```

The correlation basis is:

```text
VMID
RECOVERY_POINT_CREATED_AT
VZDUMP_START_TIME
```

No nearest-task heuristic outside the two-second window is allowed.

A strict match is `STRICT_SUCCESS_TASK_MATCH`.

If no strict match exists in the returned task history, the state is:

```text
NO_STRICT_MATCH_IN_RETURNED_HISTORY
```

This is not a failed-backup classification because historical task retention completeness is unknown.

## Bounded history semantics

The task query is bounded by `task_limit` and prefers server-side `typefilter=vzdump`.

If the API rejects that filter with HTTP 400, one bounded task-list GET may be made and filtered locally.

If the returned row count reaches the configured limit, `TASK_RESULT_LIMIT_SATURATED` is explicit.

Regardless of limit saturation, `historical_completeness=NOT_ESTABLISHED` remains true because PVE task-history retention is not established by this slice.

## Credential boundary

The existing BM2 token remains discovery-only. It is broad/admin-like, stored in a mode-0644 env file, and used with TLS verification disabled.

The adapter must not be wired into runtime until a separate least-privilege observer identity and trusted TLS path are accepted.

## Accepted evidence

Repository/manual live gate:

```text
249 passed in 1.61s
source artifact unchanged: true
source status: COMPLETE
HTTP status: 200
rows returned: 22
successful task results: 22
strict recovery-point/task matches: 9
recovery points without strict match in returned history: 3
limit saturated: false
historical completeness: NOT_ESTABLISHED
forbidden projected keys: none
raw URL markers: false
credential material projection: none
restore/integrity/RPO/RTO promotion: none
```

The three older retained recovery points for VMIDs 106, 107, and 108 remained unmatched and were not attached to distant nearest tasks.

## Consequences

A later derived integration may use `STRICT_SUCCESS_TASK_MATCH` evidence to strengthen the `LAST_SUCCESSFUL_BACKUP` assurance dimension while preserving explicit task-history and freshness limitations.

No restore, integrity, RPO, RTO, or universal protection claim is created by this source artifact.
