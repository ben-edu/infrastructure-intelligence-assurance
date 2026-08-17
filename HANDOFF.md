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

## Open Milestone 5 roadmap gaps

```text
PBS / external backup targets beyond current observed PVE local storage scope
failure-domain assurance beyond same-PVE-storage relationship
retention effectiveness
accepted RPO/RTO targets and evaluation
restore tests / verified recovery exercises
```

Restore tests and recovery exercises remain intentionally deferred while infrastructure interaction is read-only.

## Active slice — recovery-objective declaration discovery

Goal: find safe declared-state evidence for explicit RPO/RTO targets before evaluating any backup age or recovery result.

Implementation on the active branch:

```text
scripts/discovery/m5_recovery_objective_declaration_discovery.py
tests/test_recovery_objective_declaration_discovery.py
```

Bounded source:

```text
/home/ben/projects/afpa-infra-rebuild
Git-tracked safe text files only
```

Excluded from scanning/output:

```text
.env
Secret/credential/password/private-key paths
cert/key material
Terraform state
real .tfvars
raw matching lines
```

An `EXPLICIT_TARGET_CANDIDATE` is only a file-level declaration signal. It is not accepted as an authoritative asset/service RPO/RTO until source authority and scope are validated.

## Exact next step

On `mgmt-automation`:

1. run the focused safety/unit tests;
2. run the bounded recovery-objective declaration discovery;
3. inspect only the safe projected findings;
4. if no candidate exists, preserve RPO/RTO targets and results as `UNKNOWN` and move to external-backup-target discovery.

Do not evaluate existing backup timestamps against an assumed target.

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
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, dump data, or WAL contents enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
