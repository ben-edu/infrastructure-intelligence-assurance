# Milestone 5 VM Last Successful Backup Integration Live Test Gate — 2026-08-15

## Status

Retry required after a schema-contract defect was found in the first derived gate.

## Scope

Validate package `0.23.0` and `vm_backup_assurance_version=0.2` using already accepted local artifacts only.

Inputs:

```text
/tmp/vm-backup-assurance.json
/tmp/proxmox-ve-backup-task-results.json
```

The gate must not rerun any Proxmox collector.

## Repository gate

Required:

- full pytest suite passes;
- integration schema validates;
- no RBAC change;
- no systemd change;
- no network/API/query/control client markers in the integration;
- no Proxmox credential access;
- prior VM assurance and PVE task-result CLIs remain available;
- package version `0.23.0` is enforced only by the current-slice wiring test.

## Derived live gate

The gate must hash both input artifacts before and after integration and prove both are unchanged.

Current accepted source baseline:

```text
VM assets: 12
PVE task results: 22 successful
strict recovery-point/task matches: 9
unmatched retained recovery points in returned history: 3
```

Counts should be derived from the supplied artifacts rather than blindly hard-coded, except where the accepted baseline is used as a regression assertion for this current live artifact pair.

## Expected current derived behavior

Current strict matches belong to VMIDs:

```text
100
101
106
107
108
109
```

Expected VM-level result for the accepted artifact pair:

```text
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
strict success correlations consumed: 9
unmatched recovery points retained as historical unknown: 3
```

For a supported VM, `last_successful_backup_at` must equal the latest completion time of a task referenced by an accepted strict correlation for that VM.

The three old unmatched retained recovery points for VMIDs 106, 107 and 108 must not downgrade newer strictly supported latest-success evidence and must not become failure evidence.

## Trust acceptance

Validate:

```text
vm_backup_assurance_version: 0.2
mutation_allowed: false
last_successful_backup_integration.version: 0.1
last_successful_backup_integration.mode: STRICT_CORRELATION_ONLY
last_successful_backup_integration.source_status: COMPLETE
last_successful_backup_integration.source_freshness: UNKNOWN
last_successful_backup_integration.historical_completeness: NOT_ESTABLISHED
summary.unprotected_claims: 0
summary.kubernetes_pvc_assets_modified: 0
```

For every VM with strict support:

```text
last_successful_backup_status: OBSERVED
LAST_SUCCESSFUL_BACKUP dimension: OBSERVED
```

For every VM without strict support:

```text
last_successful_backup_status: UNKNOWN
LAST_SUCCESSFUL_BACKUP dimension: REQUIRED
```

## Unchanged dimensions

Every asset must retain:

```text
protection_status: UNKNOWN
integrity_verification_status: UNKNOWN
restore_verification_status: UNKNOWN
failure_domain_status: UNKNOWN
scheduled_protection_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

Recovery-point status/mechanism/retention context from VM assurance v0.1 must not be recomputed by this integration.

## Safety gate

Output must not contain credentials, URLs, raw UPIDs, raw task logs, user/token identity, raw errors, command lines, raw payloads, storage server/path/username, Terraform state, or connection strings.

No infrastructure, backup, restore, task, schedule, ACL, credential, RBAC, systemd, Kubernetes PVC, or Proxmox mutation is allowed.

## First derived gate result — 2026-08-16

Repository and semantic checks largely succeeded:

```text
261 passed in 1.21s
both input artifact hashes unchanged: true
VM assets: 12
strict correlations: 9
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
unmatched historical recovery points: 3
unprotected_claims: 0
forbidden projected keys: none
raw URL markers: false
```

However, output schema validation failed before final acceptance.

The accepted PR #38 source contract uses task result identifiers shaped as:

```text
pve-backup-task:<24 lowercase hex characters>
```

The new integration schema incorrectly expected:

```text
pve-task-<24 lowercase hex characters>
```

The generated integration output correctly preserved the accepted source `task_result_id`, so the defect was in the integration schema/test fixture, not in live source evidence or correlation logic.

The branch was corrected to reuse the authoritative PR #38 identifier contract:

```text
^pve-backup-task:[a-f0-9]{24}$
```

A dedicated regression test now asserts that the source and integration schemas use the same task-result ID pattern and that the stale fixture shape is rejected.

The first run is therefore not accepted despite the later semantic script printing `PR #41 LIVE ACCEPTANCE: PASS`; schema validation is mandatory and takes precedence.

## Acceptance result

Pending focused retry after the task-result ID schema correction.
