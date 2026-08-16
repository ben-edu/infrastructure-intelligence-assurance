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
accepted main after PR #51: e41d3efaabdeaec1dd5861e786b1f3946d426e00
active branch: agent/m5-pve-backup-policy-retention-discovery
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
infrastructure_recovery_unknown: 0
underlying_vm_last_successful_backup_observed: 37
protection_unknown: 37
backup_freshness_unknown: 37
retention_effectiveness_unknown: 37
failure_domain_unknown: 37
integrity_verification_unknown: 37
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

PostgreSQL Kubernetes context:

```text
instances_total: 8
infrastructure_recovery_observed: 8
postgresql_protection_unknown: 8
```

Management-host PostgreSQL:

```text
mgmt-automation -> PVE VMID 109
VM LAST_SUCCESSFUL_BACKUP=OBSERVED
local PostgreSQL infrastructure recovery=OBSERVED
```

MariaDB context:

```text
instances_total: 4
persistence_observed: 3
persistence_unknown: 1
infrastructure_recovery_observed: 3
infrastructure_recovery_unknown: 1
mariadb_protection_unknown: 4
```

PostgreSQL and MariaDB database-aware backup mechanism, execution/result, artifact location, retention, restore, integrity, RPO, and RTO remain unknown.

## Accepted PVE current backup-policy discovery

Report:

```text
docs/reports/2026-08-16-m5-pve-backup-policy-retention-discovery.md
```

Accepted read-only live discovery:

```text
selected_vmids_expected: 12
selected_vmids_observed: 12
backup_job_source_status: COMPLETE
declared_jobs: 0
selected_vmids_with_declared_job_scope: 0
selected_vmids_without_declared_job_scope_observed: 12
retention_prune_backups: 0
retention_legacy_maxfiles: 0
discovery_rc: 0
```

Current authoritative PVE `/cluster/backup` state returned no backup jobs.

This is current declared state only. It does not invalidate historical successful VZDUMP evidence and does not prove that backups were manual, unscheduled, deleted-policy executions, or externally orchestrated.

The accepted distinction is:

```text
current declared PVE backup jobs: NONE_OBSERVED
historical successful VZDUMP execution evidence: OBSERVED for 6/12 VMs
execution provenance relative to scheduler/policy: UNKNOWN
```

No current job-level retention/prune declaration was observed. Retention effectiveness remains unknown.

## Exact next step — historical VZDUMP execution provenance discovery

Perform one bounded read-only discovery over the already accepted successful VZDUMP task records.

Goal: determine whether authoritative PVE task metadata explicitly exposes execution provenance. Do not infer provenance from timestamp patterns, current job absence, or user identity alone.

Allowed classifications:

```text
SCHEDULED_PROVENANCE_OBSERVED
MANUAL_PROVENANCE_OBSERVED
EXTERNAL_ORCHESTRATION_PROVENANCE_OBSERVED
PROVENANCE_NOT_EXPLICITLY_RETURNED
FAILED_TO_OBSERVE
```

If task status/detail metadata contains no explicit scheduler/job/provenance field, classify `PROVENANCE_NOT_EXPLICITLY_RETURNED` and close the path. Do not read or print raw task logs, raw UPIDs, commands, hook scripts, notification targets, credentials, or backup contents.

The accepted successful task records remain execution evidence regardless of whether provenance is knowable.

## Milestone 5 gaps still open

```text
historical VZDUMP execution provenance
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
- infrastructure recovery evidence is not application/database-consistent backup evidence;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- observation credentials remain separate from control credentials;
- stale/current/unknown semantics remain explicit;
- no RPO violation is inferred without an accepted target;
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, or raw dump contents enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
