# Milestone 5 PVE Backup Policy / Retention Source Discovery — 2026-08-16

## Status

Accepted bounded read-only discovery on `mgmt-automation`.

## Scope

Observe current declared Proxmox VE backup-job policy for the accepted 12-VM scope without changing backup jobs, schedules, storage, retention, credentials, or infrastructure state.

## Authoritative source

The bounded observation used:

```text
GET /cluster/resources?type=vm
GET /cluster/backup
```

PVE source:

```text
source_id: pve-bm2
node: delfan
runtime_credential_approved: false
```

## Accepted evidence

The selected VM identity scope remained complete:

```text
selected_vmids_expected: 12
selected_vmids_observed: 12
```

The current declared backup-job source was observed successfully:

```text
backup_job_source_status: COMPLETE
declared_jobs: 0
```

No current PVE backup job was returned by the authoritative cluster backup-job endpoint.

For each accepted VMID:

```text
100,101,102,103,104,105,106,107,108,109,110,9000
```

the bounded current policy result was:

```text
declared_enabled_or_unspecified_job_scope: NONE_OBSERVED
```

Summary:

```text
declared_jobs_total: 0
enabled_true: 0
enabled_false: 0
enabled_not_explicitly_returned: 0
scope_all_guests: 0
scope_explicit_vmids: 0
scope_pool: 0
scope_unknown: 0
retention_prune_backups: 0
retention_legacy_maxfiles: 0
retention_not_explicitly_returned: 0
selected_vmids_total: 12
selected_vmids_with_declared_job_scope: 0
selected_vmids_without_declared_job_scope_observed: 12
```

Discovery return code:

```text
discovery_rc: 0
```

## Interpretation

This is current **declared state** only.

The authoritative current PVE backup-job source returned no jobs. This does not invalidate previously accepted historical backup execution evidence. Accepted strict successful VZDUMP task evidence remains observed for VMIDs 100, 101, 106, 107, 108, and 109.

Therefore the current evidence contains a real distinction:

```text
current declared PVE backup jobs: NONE_OBSERVED
historical successful VZDUMP execution evidence: OBSERVED for 6/12 VMs
execution provenance relative to a scheduler/policy: UNKNOWN
```

No inference is allowed that the historical tasks were manual, scheduled by a deleted job, scheduled externally, or produced by another orchestration mechanism without explicit evidence.

## Retention boundary

Because no current backup job was returned, no current job-level retention/prune declaration was observed from `/cluster/backup`.

This does not prove:

```text
no retention mechanism exists anywhere
retention is ineffective
recovery points are unprotected
historical backup tasks were unscheduled
RPO is violated
```

Retention effectiveness requires both an accepted retention target/policy and observed retained recovery-point evidence. Neither may be inferred from job absence alone.

## Safety

Only GET/read-only PVE API calls were used.

The discovery did not persist or print raw backup-job objects, free-form notes, hook scripts, mail/notification targets, credentials, connection strings, raw task logs, raw UPIDs, raw VM configuration, disk/network values, or backup contents.

No infrastructure mutation occurred.

## Next bounded slice

Perform a read-only provenance discovery for the already accepted successful VZDUMP task records.

The goal is not to infer scheduling from timestamps. Safely inspect only authoritative task metadata that can distinguish an explicit provenance signal, if PVE exposes one.

Allowed outcomes:

```text
SCHEDULED_PROVENANCE_OBSERVED
MANUAL_PROVENANCE_OBSERVED
EXTERNAL_ORCHESTRATION_PROVENANCE_OBSERVED
PROVENANCE_NOT_EXPLICITLY_RETURNED
FAILED_TO_OBSERVE
```

If the PVE task metadata does not explicitly expose scheduling provenance, close the slice as `PROVENANCE_NOT_EXPLICITLY_RETURNED` rather than guessing from user identity, timestamp patterns, or current job absence.
