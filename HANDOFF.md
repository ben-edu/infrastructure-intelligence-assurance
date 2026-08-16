# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live/discovery report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #52: cb70c2a13e81dd4d4fcd360317709a98334d62de
active branch: agent/m5-pve-vzdump-provenance-discovery
package on accepted main: 0.27.0
Milestone 5: active
mutation_allowed: false
management host: mgmt-automation
Kubernetes cluster: k3s-main
PVE source: pve-bm2 / delfan
```

PVE collection remains manual-only. Existing PVE credentials remain discovery-only and `runtime_credential_approved=false`.

## Stable Milestone 5 evidence

### VM recovery evidence

VM Backup Assurance v0.2 remains `STRICT_CORRELATION_ONLY` and accepts only `STRICT_SUCCESS_TASK_MATCH` evidence.

```text
assets: 12
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
protection UNKNOWN: 12
restore/integrity/failure-domain/RPO/RTO: UNKNOWN
unprotected_claims: 0
```

Accepted last-success timestamps:

```text
100 -> 2026-05-08T06:15:18Z
101 -> 2026-05-08T10:38:50Z
106 -> 2026-08-14T16:39:53Z
107 -> 2026-08-14T17:39:32Z
108 -> 2026-04-15T12:36:38Z
109 -> 2026-04-13T10:36:41Z
```

Accepted source inputs:

```text
/tmp/vm-backup-assurance.json
sha256: 14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a

/tmp/proxmox-ve-backup-task-results.json
sha256: 18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
```

### PVC Infrastructure Recovery Context v0.1

PR #51 merged at:

```text
e41d3efaabdeaec1dd5861e786b1f3946d426e00
```

Accepted live gate:

```text
package: 0.27.0
repository tests: 328 passed
assets_total: 37
infrastructure_recovery_observed: 37
underlying_vm_last_successful_backup_observed: 37
protection_unknown: 37
retention_effectiveness_unknown: 37
failure_domain_unknown: 37
restore_verification_unknown: 37
rpo_unknown: 37
rto_unknown: 37
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
gate_rc: 0
```

This remains infrastructure recovery context only, not application/database-consistent protection.

### Database infrastructure recovery contexts

```text
PostgreSQL Kubernetes instances_total: 8
PostgreSQL infrastructure_recovery_observed: 8
PostgreSQL protection_unknown: 8

Management-host PostgreSQL: mgmt-automation -> PVE VMID 109
local PostgreSQL infrastructure recovery: OBSERVED

MariaDB instances_total: 4
MariaDB persistence_observed: 3
MariaDB persistence_unknown: 1
MariaDB infrastructure_recovery_observed: 3
MariaDB infrastructure_recovery_unknown: 1
MariaDB protection_unknown: 4
```

PostgreSQL and MariaDB database-aware backup mechanism, execution/result, artifact location, retention, restore, integrity, RPO, and RTO remain unknown.

## Accepted PVE current backup-policy discovery

PR #52 merged at:

```text
cb70c2a13e81dd4d4fcd360317709a98334d62de
```

Accepted result:

```text
selected_vmids_observed: 12/12
backup_job_source_status: COMPLETE
declared_jobs: 0
selected_vmids_with_declared_job_scope: 0
selected_vmids_without_declared_job_scope_observed: 12
job-level retention/prune declarations observed: 0
discovery_rc: 0
```

Current `/cluster/backup` state returned no backup jobs. This does not invalidate historical successful VZDUMP evidence and does not establish `UNPROTECTED`, retention ineffectiveness, or RPO violation.

## Accepted PVE historical VZDUMP provenance discovery

Report:

```text
docs/reports/2026-08-16-m5-pve-vzdump-execution-provenance-discovery.md
```

Accepted result:

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

All nine accepted strict successful VZDUMP tasks were present in returned task history and had successful task-status/detail observations, but no explicit scheduler/job/manual/external provenance field was returned.

Accepted distinction:

```text
historical successful VZDUMP execution: OBSERVED
current declared backup jobs: NONE_OBSERVED
historical execution provenance: PROVENANCE_NOT_EXPLICITLY_RETURNED
```

Do not infer provenance from timestamps, current job absence, user identity, or task success.

## Exact next step — PVE storage-level retention declaration discovery

Inspect authoritative PVE storage configuration for the storage target(s) that contain accepted VM recovery points.

Discovery only. Do not modify storage or retention configuration.

Questions:

```text
Which PVE storage IDs currently support backup content?
Which storage target contains the accepted recovery points?
Does that storage configuration explicitly return prune-backups?
Does it explicitly return legacy maxfiles?
What is the safe declared retention value, if any?
Is the retention field absent from the current authoritative storage config?
```

Keep semantics strict:

```text
storage retention declaration != retention effectiveness
storage retention declaration != successful prune execution
storage retention declaration != restore verification
field absence != global absence outside inspected source
```

Safe output may include storage ID/type, whether backup content is supported, and sanitized retention declaration fields. Do not print paths, endpoints, credentials, secrets, complete connection strings, raw storage objects, or backup contents.

## Milestone 5 gaps still open

```text
PVE storage-level retention declaration
PostgreSQL database-aware backup evidence
MariaDB database-aware backup evidence
PBS (future)
external backup targets
failure-domain assurance beyond storage-ID relationship
retention effectiveness
RPO/RTO
restore tests
```

## Later roadmap

```text
Milestone 6: IaC Governance
Milestone 7: Operational Intelligence Layer
Milestone 8: Reliability and Hardening
```

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance remain separate;
- declared backup policy is not observed backup success;
- current job absence does not determine historical execution provenance;
- task success does not establish provenance when provenance fields are absent;
- infrastructure recovery evidence is not application/database-consistent backup evidence;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- observation credentials remain separate from control credentials;
- stale/current/unknown semantics remain explicit;
- no RPO violation is inferred without an accepted target;
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, or raw dump contents enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
