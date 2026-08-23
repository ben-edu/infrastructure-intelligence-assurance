# Milestone 5 — Read-Only Discovery Closure Checkpoint

Date: 2026-08-23
Status: ACCEPTED CHECKPOINT
Milestone status: ACTIVE — NOT COMPLETE
Infrastructure mutation: not allowed

## Decision

Milestone 5 is not complete against the Project Source roadmap. However, the current read-only source-discovery phase is complete for the authoritative sources currently available and safely inspectable.

```text
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
remaining unknowns: EXPLICITLY PRESERVED
mutation-required work: DEFERRED
```

No additional probe should be created merely to convert an unsupported `UNKNOWN` into a stronger-looking status.

## Evidence reached in the read-only phase

### VM / PVE

```text
VM assets: 12
last successful backup OBSERVED: 6
last successful backup UNKNOWN: 6
strict successful VZDUMP task correlations: 9
current declared PVE backup jobs: 0
historical task provenance explicit: 0/9
historical task provenance: PROVENANCE_NOT_EXPLICITLY_RETURNED 9/9
accepted recovery-point storage: local
storage retention declaration: prune-backups=keep-all=1
external/PBS/network-like backup target: NONE_OBSERVED_IN_BOUNDED_PVE_STORAGE_SCOPE
```

For the six VMs with accepted recovery-point mechanisms:

```text
same PVE node: OBSERVED 6/6
same storage ID: OBSERVED 6/6
logical access-path separation: NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID 6/6
physical failure-domain independence: UNKNOWN
```

### PVC

```text
PVC assets: 37
infrastructure recovery OBSERVED: 37
protection: UNKNOWN 37
retention effectiveness: UNKNOWN 37
restore verification: UNKNOWN 37
RPO: UNKNOWN 37
RTO: UNKNOWN 37
```

### PostgreSQL

```text
Kubernetes PostgreSQL instances: 8
infrastructure recovery OBSERVED: 8
Kubernetes database-aware backup mechanism: UNKNOWN 8/8
management-host PostgreSQL infrastructure recovery: OBSERVED
management-host backup-capable tooling: OBSERVED
management-host configured database backup mechanism: UNKNOWN
```

### MariaDB

```text
accepted candidates: 4
infrastructure recovery OBSERVED: 3
infrastructure recovery UNKNOWN: 1
database-aware backup mechanism: UNKNOWN 4/4
```

### Recovery objectives

```text
bounded safe declared-state files scanned: 175
explicit RPO target candidates: 0
explicit RTO target candidates: 0
RPO target: UNKNOWN
RTO target: UNKNOWN
RPO result: UNKNOWN
RTO result: UNKNOWN
```

## Preserved gaps

The remaining Milestone 5 gaps are not implementation failures; they are unresolved assurance questions that require stronger evidence or a different authorization boundary.

```text
physical failure-domain independence
retention effectiveness
accepted RPO/RTO targets and evaluation
restore verification
integrity verification
application/database-consistent backup evidence where no authoritative mechanism was found
```

### Why retention effectiveness stays UNKNOWN

A current declaration such as `prune-backups=keep-all=1` does not prove that retention behaved as intended over time. The accepted task/recovery-point history does not establish a complete policy-effective history sufficient to prove retention effectiveness.

### Why RPO/RTO stay UNKNOWN

No authoritative RPO/RTO target was observed in the bounded declared-state source. Backup age must not be evaluated against an invented target.

### Why restore/integrity stay UNKNOWN

A real restore or integrity exercise changes or creates operational state. The current project boundary is read-only. These checks therefore require future controlled mutation and explicit authorization.

## Deferred controlled-recovery work

Future work may include isolated restoration exercises and integrity verification, as allowed by the Project Source roadmap. Such work must use a separately reviewed mutation plan, scoped test targets, rollback/cleanup rules, evidence capture, and explicit authorization.

Until then:

```text
restore verification: UNKNOWN
integrity verification: UNKNOWN
RTO result: UNKNOWN
```

## Transition decision

The project may proceed to Milestone 6 — IaC Governance without pretending Milestone 5 is fully complete. Milestone 5 controlled-recovery gaps remain registered and must be revisited when policy targets, stronger topology evidence, or a controlled mutation window become available.

The smallest next useful slice is a read-only Terraform declared-state inventory for the known infrastructure repository, focused first on stacks/workspaces and managed-resource coverage. It must exclude Terraform state, real tfvars, secrets, credentials, and apply operations.

## Trust boundary

This checkpoint synthesizes already accepted evidence only. It performs no live read and no infrastructure/database/storage mutation.

No secrets, raw sensitive configuration, Terraform state, backup contents, database data, private keys, credentials, or complete connection strings are introduced into the checkpoint.
