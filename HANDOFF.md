# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #57: 2c46603b822d40dca22094eb64862268fa65a262
active branch: agent/m5-recovery-objective-declaration-discovery
package on accepted main: 0.27.0
Milestone 5: ACTIVE — NOT COMPLETE
mutation_allowed: false
management host: mgmt-automation
Kubernetes cluster: k3s-main
PVE source: pve-bm2 / delfan
```

PVE collection remains manual-only. Existing PVE credentials remain discovery-only and `runtime_credential_approved=false`.

## Stable Milestone 5 checkpoint

Read-only checkpoint report:

```text
docs/reports/2026-08-17-m5-read-only-checkpoint-gap-register.md
```

Current accepted evidence includes:

```text
VM assets: 12
VM last_successful_backup OBSERVED: 6
VM last_successful_backup UNKNOWN: 6
strict successful VZDUMP correlations: 9
current declared PVE backup jobs: 0
accepted PVE recovery-point storage: local
storage retention declaration: prune-backups=keep-all=1
retention effectiveness: UNKNOWN

PVC assets: 37
PVC infrastructure_recovery_observed: 37
PVC protection_unknown: 37
PVC restore/RPO/RTO: UNKNOWN

PostgreSQL Kubernetes instances: 8
PostgreSQL infrastructure_recovery_observed: 8
PostgreSQL database-aware backup mechanism: UNKNOWN 8/8
management-host PostgreSQL configured backup mechanism: UNKNOWN

MariaDB candidates: 4
MariaDB infrastructure_recovery_observed: 3
MariaDB infrastructure_recovery_unknown: 1
MariaDB database-aware backup mechanism: UNKNOWN 4/4
```

No accepted `UNPROTECTED`, stale-backup, or RPO-violation claims have been promoted from bounded signal absence.

## Accepted recovery-objective declaration discovery

Report:

```text
docs/reports/2026-08-23-m5-recovery-objective-declaration-discovery.md
```

Focused tests:

```text
3 passed in 0.06s
```

Accepted bounded live result:

```text
source_mode: GIT_TRACKED_TEXT_ONLY
source_status: COMPLETE
tracked_safe_text_files_scanned: 175
read_or_decode_skips: 0
objective_signals: NONE_OBSERVED
rpo_declaration_signals: 0
rpo_explicit_target_candidates: 0
rto_declaration_signals: 0
rto_explicit_target_candidates: 0
rpo_compliance_claims: 0
rto_compliance_claims: 0
rpo_violation_claims: 0
discovery_rc: 0
```

Accepted state:

```text
RPO target: UNKNOWN
RTO target: UNKNOWN
RPO result: UNKNOWN
RTO result: UNKNOWN
```

This is bounded negative evidence only. It does not prove that no RPO/RTO objective exists elsewhere. No backup age, recovery-point age, task result, or restore duration may be evaluated against an assumed target.

## Open Milestone 5 roadmap gaps

```text
PBS / external backup targets beyond current observed PVE local storage scope
failure-domain assurance beyond same-PVE-storage relationship
retention effectiveness
accepted RPO/RTO targets and evaluation
restore tests / verified recovery exercises
```

Restore tests and recovery exercises remain intentionally deferred while infrastructure interaction is read-only.

## Exact next step

Start bounded **external-backup-target discovery**.

Goal: determine whether authoritative safe metadata exposes any backup target beyond the currently accepted PVE `local` storage scope, including PBS or other external target types.

Do not print or persist endpoint addresses, server names when unnecessarily sensitive, paths, datastore connection details, credentials, tokens, fingerprints, usernames, passwords, connection strings, raw storage objects, or backup contents.

Safe projected fields may include only:

```text
source status
storage/target identifier when non-sensitive and already part of accepted operational inventory
storage/target type
disabled/enabled state
backup-content capability
external-vs-local classification
PBS-like target presence count
```

Absence in a bounded source is `NONE_OBSERVED_IN_BOUNDED_SCOPE`, not universal absence.

If no external target is observed, preserve:

```text
external backup target: UNKNOWN / NONE_OBSERVED_IN_BOUNDED_SCOPE
failure-domain independence: UNKNOWN
```

Do not infer physical failure-domain independence from a storage type or target name alone.

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance remain separate;
- declared backup policy is not observed backup success;
- storage retention declaration is not retention effectiveness;
- infrastructure recovery evidence is not application/database-consistent backup evidence;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- stale/current/unknown semantics remain explicit;
- no RPO violation is inferred without an accepted target;
- external target type/name does not establish physical failure-domain independence;
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, dump data, WAL contents, backup contents, or complete connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
