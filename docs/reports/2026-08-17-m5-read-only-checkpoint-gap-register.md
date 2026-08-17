# Milestone 5 — Read-Only Checkpoint and Gap Register

Date: 2026-08-17
Status: CHECKPOINT — MILESTONE NOT COMPLETE
Infrastructure mutation allowed: false

## Purpose

Consolidate accepted Milestone 5 evidence after the bounded VM, PVC, PostgreSQL, MariaDB, PVE policy/provenance, and PVE retention discovery slices.

This checkpoint does not promote unknown assurance dimensions and does not declare Milestone 5 complete. The Project Source roadmap still requires broader backup/recovery assurance, including PBS/external targets, retention effectiveness, RPO/RTO, and restore tests.

## OBSERVED

### VM recovery evidence

- 12 VM assets are in accepted scope.
- 6/12 VMs have an accepted `LAST_SUCCESSFUL_BACKUP=OBSERVED` derived only from `STRICT_SUCCESS_TASK_MATCH` evidence.
- 9 accepted strict successful VZDUMP task correlations were independently re-observed in PVE task metadata.
- Historical task execution provenance was not explicitly returned for any of the nine tasks.

### PVC infrastructure recovery

- 37/37 accepted Kubernetes PVC assets have `infrastructure_recovery=OBSERVED` through the bounded chain:
  `PVC -> explicit storage node -> PVE VMID -> accepted strict VM last-successful-backup evidence`.
- 22/37 PVCs had a directly observed workload-controller reference.
- 15/37 had `NONE_OBSERVED` for the bounded direct-controller reference. This is context only and is not an orphan/protection classification.

### Database infrastructure recovery

- PostgreSQL Kubernetes instances: 8/8 infrastructure recovery observed.
- Management-host PostgreSQL maps to PVE VMID 109 and has infrastructure recovery observed.
- MariaDB candidates: 3/4 infrastructure recovery observed; 1/4 remains unknown because persistence was not established in the accepted source scope.

### PVE storage configuration

- Accepted recovery-point storage target: `local`.
- Storage type: `dir`.
- Backup content capability: enabled.
- Storage disabled state: false.

## DECLARED

### Current PVE backup jobs

The complete current `/cluster/backup` source returned:

```text
declared_jobs: 0
selected_vmids_with_declared_job_scope: 0/12
```

This is current declared policy state only. It does not invalidate historical VZDUMP execution.

### PVE storage retention

The accepted recovery-point storage target currently declares:

```text
prune-backups=keep-all=1
```

This is a retention declaration only. It is not retention-effectiveness evidence.

## NOT_OBSERVED_IN_BOUNDED_SCOPE

The following are bounded negative observations, not universal absence claims:

- no current declared PVE backup job in the complete inspected `/cluster/backup` source;
- no explicit scheduled/manual/external provenance field for the nine accepted strict successful VZDUMP tasks;
- no PostgreSQL-aware backup sidecar/init/ConfigMap signal across the 8 accepted Kubernetes PostgreSQL workloads;
- no matching PostgreSQL backup CronJob/Job in the complete bounded Kubernetes source;
- no instantiated or active management-host PostgreSQL backup unit/timer/cron filename in the inspected scope;
- no MariaDB/MySQL-compatible backup sidecar/init/ConfigMap signal across the 4 accepted MariaDB candidates;
- no matching MariaDB/MySQL backup CronJob/Job in the complete bounded Kubernetes source;
- no MariaDB/MySQL-compatible management-host backup tool/unit/timer/cron filename in the inspected scope;
- no additional accepted backup-capable PVE storage target was observed beyond `local` in the accepted storage discovery.

These observations do not establish `UNPROTECTED`.

## UNKNOWN

### VM / PVC assurance

- protection status;
- backup freshness as a policy result;
- physical failure-domain independence;
- retention effectiveness;
- integrity verification;
- restore verification;
- RPO target/result;
- RTO target/result.

### PostgreSQL

For all 8 accepted Kubernetes PostgreSQL workloads and the management-host PostgreSQL scope:

- configured database-aware backup mechanism: UNKNOWN;
- successful database-aware backup execution: UNKNOWN;
- database-consistent artifact validity: UNKNOWN;
- retention effectiveness: UNKNOWN;
- restore verification: UNKNOWN;
- RPO/RTO: UNKNOWN.

Tool presence on the management host (`pg_basebackup`, `pg_dump`, `pg_dumpall`) is capability evidence only.

### MariaDB

For all 4 accepted MariaDB candidates:

- database-aware backup mechanism: UNKNOWN;
- successful database-aware backup execution: UNKNOWN;
- database-consistent artifact validity: UNKNOWN;
- retention effectiveness: UNKNOWN;
- restore verification: UNKNOWN;
- RPO/RTO: UNKNOWN.

## OBSERVED RISKS / ASSURANCE GAPS

These are evidence gaps or risk indicators, not failure classifications:

1. Six of twelve VM assets have no accepted strict last-successful-backup result.
2. The current PVE configuration exposes zero declared backup jobs for the selected VM scope.
3. The accepted recovery-point target is the PVE `local` storage ID; physical failure-domain independence is not established.
4. PostgreSQL database-aware backup mechanisms remain unknown across all accepted scopes.
5. MariaDB database-aware backup mechanisms remain unknown across all accepted candidates.
6. Retention effectiveness is not verified even though a storage retention declaration exists.
7. No accepted RPO/RTO targets are available for compliance evaluation.
8. No restore verification evidence is accepted.

Old backup timestamps are evidence only. No stale-backup or RPO-violation result is allowed without an accepted target/policy.

## REQUIRED LIVE VERIFICATION / NEW AUTHORITATIVE EVIDENCE

Read-only progress remains possible if an authoritative source can safely provide:

- explicit RPO targets;
- explicit RTO targets;
- external backup target declarations outside the currently observed PVE `local` storage scope;
- PBS registration/coverage evidence if PBS exists outside the current accepted source;
- authoritative database-backup mechanism declarations;
- retained-history evidence sufficient to evaluate retention effectiveness without inspecting backup contents;
- stronger failure-domain metadata that does not expose sensitive paths or state.

## REQUIRES FUTURE CONTROLLED MUTATION

The following cannot be honestly established from current read-only evidence alone:

- real restore tests;
- isolated database restore validation;
- VM/PVC recovery exercises;
- measured RTO from a recovery exercise;
- destructive/failure simulation.

Any future controlled mutation requires an explicitly reviewed control-plane design, fresh live verification, and approval. Observation credentials must not be reused silently as control credentials.

## Current Milestone Decision

Milestone 5 remains ACTIVE.

The bounded PostgreSQL and MariaDB source-discovery lanes are closed for the current read-only phase at `DATABASE_BACKUP_MECHANISM_UNKNOWN` unless new authoritative evidence appears.

The next smallest useful read-only slice should first attempt **recovery-objective declaration discovery** for explicit RPO/RTO targets. This is higher value than classifying backup age without a target because accepted RPO/RTO declarations would unlock policy-aware evaluation of existing timestamp evidence.

If no authoritative RPO/RTO declaration source is found, preserve `UNKNOWN` and move to bounded external-backup-target discovery.

## Trust boundary

- no infrastructure mutation;
- no database connection or data access;
- no backup-content inspection;
- no Secret/env values;
- no raw task logs or raw VM configuration;
- no sensitive Terraform state or connection strings;
- bounded negative evidence is not generalized beyond its source scope;
- declared state, observed state, unknown state, and required live verification remain distinct.
