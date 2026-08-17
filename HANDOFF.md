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
accepted main after PR #53: 7456e20116ec47d501112a1d643109683fd6cefe
active branch: agent/m5-pve-storage-retention-discovery
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

VM Backup Assurance last-success integration remains `STRICT_CORRELATION_ONLY` and accepts only `STRICT_SUCCESS_TASK_MATCH` evidence.

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

PR #53 merged at:

```text
7456e20116ec47d501112a1d643109683fd6cefe
```

Accepted result:

```text
strict_success_tasks_total: 9
task_list_matches: 9
task_detail_complete: 9
scheduled_provenance_observed: 0
manual_provenance_observed: 0
external_orchestration_provenance_observed: 0
provenance_not_explicitly_returned: 9
failed_to_observe: 0
discovery_rc: 0
```

Accepted distinction:

```text
historical successful VZDUMP execution: OBSERVED
current declared backup jobs: NONE_OBSERVED
historical execution provenance: PROVENANCE_NOT_EXPLICITLY_RETURNED
```

## Accepted PVE storage-level retention declaration discovery

Report:

```text
docs/reports/2026-08-17-m5-pve-storage-retention-declaration-discovery.md
```

The accepted VM assurance artifact shape probe established:

```text
vm_backup_assurance_version: 0.1
assets_total: 12
assets_with_source_recovery_point_ids: 6
source_recovery_point_id_count: 12
assets_with_backup_mechanisms: 6
backup_mechanism_storage_id_present: 6
backup_mechanism_types: PROXMOX_VE_STORAGE_ARCHIVE=6
backup_mechanism_basis_shapes: RECOVERY_POINT_OBSERVED_IN_SOURCE_SCOPE=6
```

Accepted live retry result:

```text
regression tests: 2 passed in 0.03s
accepted source hash_match: true
accepted_recovery_point_storage_ids: 1
accepted_recovery_point_storage_id_list: local
storage_config_source_status: COMPLETE
storage=local type=dir backup_content=True disabled=False accepted_recovery_point_target=True
retention_declaration=PRUNE_BACKUPS_DECLARED
retention_value=keep-all=1
accepted_targets_with_prune_backups_declared: 1
retention_effectiveness_claims: 0
unprotected_claims: 0
rpo_violation_claims: 0
discovery_rc: 0
```

Accepted semantics:

```text
storage-level retention declaration: OBSERVED
retention policy: prune-backups=keep-all=1
retention effectiveness: UNKNOWN
restore verification: UNKNOWN
RPO/RTO: UNKNOWN
```

The discovery correction history is part of the report: two earlier attempts failed closed because they used the wrong derived-artifact shape/version assumptions. No infrastructure state was changed.

## Exact next step — PostgreSQL database-aware backup source discovery

The PVE retention-declaration lane is now sufficiently characterized for the current read-only phase. The next smallest useful Milestone 5 slice is bounded PostgreSQL database-aware backup source discovery.

Do not create backups, run dumps, connect to databases, read database rows, expose Kubernetes Secret values, or change workload configuration.

Bounded questions:

```text
For each of the 8 accepted Kubernetes PostgreSQL workload subjects, do current workload specs expose an explicit backup sidecar/init container or backup-oriented mounted ConfigMap/PVC by safe metadata only?
Do current Kubernetes CronJobs/Jobs expose PostgreSQL-aware backup tooling or naming signals beyond the previously observed zero bounded matches?
For management-host PostgreSQL, is there a configured pgBackRest/Barman/WAL-G/pg_basebackup systemd unit/timer/cron/script reference in bounded local metadata?
Can any discovered mechanism be classified as DECLARED/OBSERVED without connecting to PostgreSQL or reading secrets?
Which subjects remain DATABASE_BACKUP_MECHANISM_UNKNOWN?
```

Safe projections may include namespace, workload kind/name, container name/image, non-secret volume type/name, ConfigMap name, PVC name, systemd unit/timer names, executable/tool names, and bounded schedule metadata.

Do not print env values, Secret names when their presence would disclose sensitive purpose unnecessarily, Secret keys/values, commands/args containing connection material, full connection strings, database names/users/passwords, raw ConfigMap contents, DB rows, dumps, WAL contents, or filesystem backup contents.

A backup-capable binary or backup-looking name is not successful backup evidence. A declared mechanism does not establish execution result, artifact validity, retention effectiveness, restore verification, RPO, RTO, or protection.

## Milestone 5 gaps still open

```text
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
- storage retention declaration is not retention effectiveness;
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
