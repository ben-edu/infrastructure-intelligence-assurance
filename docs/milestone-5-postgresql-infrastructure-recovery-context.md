# Milestone 5 — PostgreSQL Infrastructure Recovery Context

## Status

Implementation ready for repository and live acceptance gates.

This slice is not accepted until the management-host gate passes and the live bounded relationship input reproduces the expected eight-instance scope.

## Purpose

Provide a small derived context that makes existing infrastructure recovery evidence useful for the eight observed Kubernetes PostgreSQL instances without misrepresenting VM-level recovery evidence as PostgreSQL-consistent backup assurance.

The accepted trust decision is ADR 0026:

```text
docs/decisions/0026-distinguish-postgresql-infrastructure-recovery-from-database-backup.md
```

## Package

```text
package: 0.25.0
context artifact version: 0.1
relationship evidence input version: 0.1
required VM Backup Assurance version: 0.2
mutation_allowed: false
```

CLI:

```text
iia-postgresql-infrastructure-recovery-context
```

## Inputs

The derivation consumes two bounded inputs.

### PostgreSQL infrastructure relationship evidence v0.1

This input carries only the already-established safe relationship fields required for the join:

```text
PostgreSQL Kubernetes workload identity
persistent PVC identity
PV identity and explicit Kubernetes storage node
Kubernetes node -> PVE VMID mapping
PVE source identity and node
```

The relationship source type is:

```text
BOUNDED_KUBERNETES_PVE_RELATIONSHIP_OBSERVATION
```

The first live gate will construct this bounded input from read-only Kubernetes observation plus the already-approved discovery-only PVE lookup. It must not persist raw Pod specs, Secret values, PV backing paths, CSI handles, VM config, network values, credentials, or raw API payloads.

### VM Backup Assurance v0.2

The derivation requires the accepted `STRICT_CORRELATION_ONLY` VM last-successful-backup contract.

An `OBSERVED` underlying VM last-successful-backup claim is accepted only when all of the following are present and consistent:

```text
last_successful_backup_status = OBSERVED
last_successful_backup_at is present
source_type = PROXMOX_VE_VZDUMP_TASK_RESULT
source_id matches the VM assurance source
recovery_point_id matches the accepted ID contract
task_result_id matches the accepted ID contract
basis = [STRICT_SUCCESS_TASK_MATCH]
```

Malformed observed claims fail closed.

## Derived relationship

When every required source edge is observed, both source scopes are complete, the PVE source identities match, and the joined VM has accepted strict last-successful-backup evidence, the context may state:

```text
infrastructure_recovery.relationship_status = OBSERVED
```

The evidence chain is:

```text
PostgreSQL workload
-> persistent PVC
-> explicit PV storage node
-> K3s node
-> PVE VMID
-> accepted VM LAST_SUCCESSFUL_BACKUP evidence
```

Missing or incomplete evidence produces `UNKNOWN` or `FAILED_TO_OBSERVE`; it is never converted to an absence claim.

## PostgreSQL-specific assurance boundary

For every PostgreSQL instance in this slice, these fields are structurally fixed to unknown until a separate authoritative database-aware source is integrated:

```text
protection_status: UNKNOWN
backup_mechanism_status: UNKNOWN
backup_execution_status: UNKNOWN
backup_artifact_location_status: UNKNOWN
retention_effectiveness_status: UNKNOWN
restore_verification_status: UNKNOWN
integrity_verification_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

The artifact also fixes:

```text
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

An old VM backup timestamp is evidence only. It must not become `BACKUP_STALE` or `RPO_VIOLATION` without an accepted target/freshness contract.

## Scope exclusion

The local PostgreSQL instance on `mgmt-automation` is explicitly excluded from this first implementation:

```text
management_host_postgresql_included: false
```

Only Kubernetes PostgreSQL subjects are accepted by the relationship input validator.

## Runtime boundary

The implementation is pure derivation.

It does not contain or invoke:

```text
kubectl
PVE API clients
psql
pg_dump
pg_basebackup
network clients
subprocess execution
credentials
systemd wiring
```

It is not added to the existing runtime service. Live source acquisition remains a separate manual gate operation.

## Expected live scope

If the infrastructure observed during discovery remains unchanged, the gate should derive eight instances:

```text
drfarah-staging       -> k3s-worker-02 -> VMID 108
fastapi-platform      -> k3s-worker-01 -> VMID 107
fastapi-platform-dev  -> k3s-worker-01 -> VMID 107
keycloak              -> k3s-master-01 -> VMID 106
openproject           -> k3s-worker-01 -> VMID 107
soria-academie        -> k3s-worker-02 -> VMID 108
soria-prospecting     -> k3s-worker-01 -> VMID 107
toilettage             -> k3s-worker-01 -> VMID 107
```

Accepted VM timestamps expected from the byte-verified source artifacts are:

```text
106 -> 2026-08-14T16:39:53Z
107 -> 2026-08-14T17:39:32Z
108 -> 2026-04-15T12:36:38Z
```

The live gate must treat these as expectations to verify, not values to fabricate.

## Acceptance criteria

The slice is accepted only if all of the following pass:

```text
full repository tests: PASS
output JSON schema: PASS
context version: 0.1
mutation_allowed: false
instances_total: 8
infrastructure_recovery_observed: 8
infrastructure_recovery_unknown: 0
infrastructure_recovery_failed_to_observe: 0
underlying_vm_last_successful_backup_observed: 8
postgresql_protection_unknown: 8
postgresql_backup_mechanism_unknown: 8
postgresql_backup_execution_unknown: 8
postgresql_restore_verification_unknown: 8
postgresql_integrity_verification_unknown: 8
postgresql_rpo_unknown: 8
postgresql_rto_unknown: 8
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

The two previously accepted source artifact SHA256 values must match before VM Backup Assurance v0.2 is re-derived in memory for the gate.

## Safety acceptance

The gate must remain read-only and must not expose or persist secrets, database data, raw Kubernetes Secret values, raw Pod environment values, raw VM config, sensitive connection strings, raw backup contents, or raw infrastructure credentials.
