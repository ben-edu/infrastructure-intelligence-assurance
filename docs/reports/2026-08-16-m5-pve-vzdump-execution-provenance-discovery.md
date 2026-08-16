# Milestone 5 PVE VZDUMP Execution Provenance Discovery — 2026-08-16

## Status

Accepted bounded read-only discovery on `mgmt-automation`.

## Scope

Determine whether authoritative PVE task metadata explicitly identifies execution provenance for the already accepted strict successful VZDUMP task records.

This discovery does not infer provenance from timestamps, current backup-job absence, user identity, successful task status, or naming patterns.

## Accepted source verification

```text
/tmp/proxmox-ve-backup-task-results.json
sha256: 18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
hash_match: true
```

Accepted strict task scope:

```text
source_id: pve-bm2
node: delfan
strict_success_task_ids: 9
```

## Live observation

```text
bounded PVE task list: HTTP 200
request_mode: SERVER_FILTERED_VZDUMP
runtime_credential_approved: false
task_metadata_source_status: COMPLETE
strict_tasks_matched_in_returned_history: 9
strict_tasks_not_matched_in_returned_history: 0
```

Task-status/detail lookup completed for all nine matched strict tasks.

## Provenance result

```text
strict_success_tasks_total: 9
task_list_matches: 9
task_detail_complete: 9
task_detail_failed_to_observe: 0
scheduled_provenance_observed: 0
manual_provenance_observed: 0
external_orchestration_provenance_observed: 0
provenance_not_explicitly_returned: 9
failed_to_observe: 0
discovery_rc: 0
```

For all nine accepted strict successful tasks, the inspected authoritative task-list and task-status metadata did not explicitly return a scheduler/job/manual/external provenance field or value.

Accepted classification:

```text
PROVENANCE_NOT_EXPLICITLY_RETURNED: 9/9
```

This is an unknown-origin classification, not evidence that the tasks were manual, scheduled, externally orchestrated, or orphaned from a policy.

## Relationship to current declared policy

The separately accepted current PVE backup-policy discovery returned:

```text
current declared /cluster/backup jobs: 0
```

That current declared state does not determine the origin of historical successful VZDUMP executions.

The accepted distinction remains:

```text
historical successful VZDUMP execution: OBSERVED
current declared backup jobs: NONE_OBSERVED
historical execution provenance: PROVENANCE_NOT_EXPLICITLY_RETURNED
```

## Trust boundary

Raw UPIDs were used only in memory for bounded task-status lookup and were not printed or persisted.

Raw task logs were not read. Raw user values, commands, hooks, notes, notification targets, credentials, VM configuration, backup contents, and connection strings were not printed or persisted.

Only GET/read-only PVE API calls were used. No backup job, task, storage, retention, schedule, or infrastructure state was changed.

## Next bounded slice

Inspect authoritative PVE storage configuration for retention declarations on storage targets that hold accepted VM recovery points.

This is distinct from job-level retention and must remain declared state only. Specifically inspect safe fields such as storage ID/type/content support and explicit `prune-backups` or legacy `maxfiles` if returned.

Do not infer retention effectiveness from a declaration, and do not infer absence globally if the bounded source does not expose a field.
