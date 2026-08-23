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
accepted main after PR #60: 50d30d7d59f88bc5909092d410eb4b446b8b4e72
active branch: docs/m5-read-only-discovery-closure
package on accepted main: 0.27.0
Milestone 5 overall: ACTIVE — NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
mutation_allowed: false
management host: mgmt-automation
Kubernetes cluster: k3s-main
PVE source: pve-bm2 / delfan
```

PVE collection remains manual-only. Existing PVE credentials remain discovery-only and `runtime_credential_approved=false`.

## Milestone 5 read-only closure checkpoint

Report:

```text
docs/reports/2026-08-23-m5-read-only-discovery-closure.md
```

Decision:

```text
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
remaining unknowns: EXPLICITLY PRESERVED
mutation-required work: DEFERRED
```

Do not create additional probes merely to force unsupported unknowns into stronger states.

## Stable Milestone 5 evidence

### VM / PVE

```text
VM assets: 12
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
strict successful VZDUMP correlations: 9
current declared PVE backup jobs: 0
historical execution provenance: PROVENANCE_NOT_EXPLICITLY_RETURNED 9/9
accepted recovery-point storage: local
storage retention declaration: prune-backups=keep-all=1
external backup target: NONE_OBSERVED_IN_BOUNDED_PVE_STORAGE_SCOPE
```

For VMIDs `100,101,106,107,108,109`:

```text
same PVE node: OBSERVED
VM storage ID: local
accepted backup storage ID: local
storage-ID overlap: OBSERVED
logical access-path separation: NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID
physical failure-domain independence: UNKNOWN
```

### PVC

```text
PVC assets: 37
infrastructure_recovery_observed: 37
protection_unknown: 37
retention_effectiveness_unknown: 37
restore_verification_unknown: 37
rpo_unknown: 37
rto_unknown: 37
```

### PostgreSQL

```text
Kubernetes instances: 8
infrastructure_recovery_observed: 8
database-aware backup mechanism: UNKNOWN 8/8
management-host infrastructure recovery: OBSERVED
management-host backup-capable tooling: OBSERVED
management-host configured backup mechanism: UNKNOWN
```

### MariaDB

```text
accepted candidates: 4
infrastructure_recovery_observed: 3
infrastructure_recovery_unknown: 1
database-aware backup mechanism: UNKNOWN 4/4
```

### Recovery objectives

```text
safe Git-tracked declared-state files scanned: 175
explicit RPO target candidates: 0
explicit RTO target candidates: 0
RPO target/result: UNKNOWN
RTO target/result: UNKNOWN
```

No accepted `UNPROTECTED`, backup-stale, or RPO-violation claim has been promoted from bounded signal absence.

## Milestone 5 deferred gaps

```text
physical failure-domain independence beyond logical PVE coupling
retention effectiveness
accepted RPO/RTO targets and evaluation
restore verification
integrity verification
application/database-consistent backup evidence where no authoritative mechanism was found
```

These gaps require new authoritative policy/topology/history evidence or controlled mutation. Restore and integrity exercises require explicit authorization and a separately reviewed mutation plan.

## Transition to Milestone 6

The Project Source roadmap defines Milestone 6 as IaC Governance:

```text
Terraform:
- stacks/workspaces
- managed-resource coverage
- plan/apply metadata
- drift
- destructive-change detection

Ansible:
- inventories
- roles/playbooks
- managed-host coverage
- execution outcomes
- configuration drift where measurable
```

## Exact next step

Start the smallest read-only Milestone 6 slice: **Terraform declared-state inventory** for the known infrastructure repository.

Bounded source:

```text
/home/ben/projects/afpa-infra-rebuild
Git-tracked safe Terraform source only
```

First questions:

```text
Which Terraform roots/stacks are declared?
Which backend/workspace declarations are observable without state access?
Which provider/resource types are declared?
What managed-resource coverage can be stated from configuration only?
Which coverage questions require Terraform state or live provider verification?
```

Exclude:

```text
terraform.tfstate / state backups
real tfvars
.env
secrets/credentials/private keys
provider tokens/passwords
raw sensitive connection strings
terraform apply/destroy/import/state mutation
```

Do not call configuration-declared resources `OBSERVED` infrastructure. Keep declared state separate from live/provider/state evidence.

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance remain separate;
- declared state is not observed state;
- unknowns are not forced closed without authoritative evidence;
- no Terraform state or real tfvars enter evidence/AI context;
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, dump data, WAL contents, backup contents, or complete sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
