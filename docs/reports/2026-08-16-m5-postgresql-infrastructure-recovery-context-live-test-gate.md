# Milestone 5 PostgreSQL Infrastructure Recovery Context Live Test Gate — 2026-08-16

## Status

Pending live acceptance on `mgmt-automation`.

Do not treat this slice as accepted until the repository, bounded live relationship, accepted-source hash, derivation, and schema gates all pass.

## Implementation under test

```text
branch: feature/m5-postgresql-infrastructure-recovery-context
package: 0.25.0
postgresql_infrastructure_recovery_context_version: 0.1
mutation_allowed: false
```

The implementation is pure derivation and is not runtime-wired.

## Gate plan

### 1. Repository gate

Run the complete repository test suite on the management host.

Acceptance requires zero failures.

### 2. Bounded PostgreSQL relationship observation

Observe only the eight accepted Kubernetes PostgreSQL workload subjects and their required persistence chain:

```text
workload -> mounted PVC -> bound PV -> explicit hostname node affinity
```

Then perform the existing bounded read-only PVE guest lookup for only:

```text
k3s-master-01
k3s-worker-01
k3s-worker-02
```

Safe output is limited to workload/PVC/PV identifiers, storage node, PostgreSQL image identity, PVE VMID, PVE node, guest type/status, source status, and bounded provenance.

No Secret values, environment values, PV backing paths, CSI handles, VM config, network values, credentials, or raw API payloads may be persisted.

### 3. Accepted VM source verification

Before deriving VM Backup Assurance v0.2, byte-verify the two accepted input artifacts:

```text
/tmp/vm-backup-assurance.json
expected sha256: 14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a

/tmp/proxmox-ve-backup-task-results.json
expected sha256: 18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
```

A hash mismatch rejects the gate. Do not substitute current live PVE collection in that case without a separate source-acceptance decision.

### 4. Pure derivation

Derive VM Backup Assurance v0.2 from the byte-verified accepted inputs, then derive PostgreSQL infrastructure recovery context v0.1 from:

```text
bounded relationship evidence v0.1
accepted VM Backup Assurance v0.2
```

### 5. Schema gate

Validate the output against:

```text
schemas/postgresql-infrastructure-recovery-context.schema.json
```

## Expected bounded result

If the discovery state remains unchanged, expected instance relationships are:

```text
keycloak              -> k3s-master-01 -> VMID 106
fastapi-platform      -> k3s-worker-01 -> VMID 107
fastapi-platform-dev  -> k3s-worker-01 -> VMID 107
openproject           -> k3s-worker-01 -> VMID 107
soria-prospecting     -> k3s-worker-01 -> VMID 107
toilettage            -> k3s-worker-01 -> VMID 107
drfarah-staging       -> k3s-worker-02 -> VMID 108
soria-academie        -> k3s-worker-02 -> VMID 108
```

Expected accepted VM latest-success timestamps:

```text
106 -> 2026-08-14T16:39:53Z
107 -> 2026-08-14T17:39:32Z
108 -> 2026-04-15T12:36:38Z
```

These are comparison expectations only; the gate must derive them from accepted evidence.

## Acceptance counters

The gate is expected to produce:

```text
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

Any change in live relationship state must be reported as observed rather than forced to these expected counters.

## Trust boundary

Even if all eight infrastructure recovery relationships are `OBSERVED`, the gate does not establish:

```text
PostgreSQL-consistent backup
PostgreSQL backup execution/result
PostgreSQL backup artifact location
PostgreSQL retention effectiveness
PostgreSQL restore verification
PostgreSQL integrity verification
PostgreSQL RPO satisfaction
PostgreSQL RTO satisfaction
```

The old VMID 108 timestamp must not be classified as `BACKUP_STALE` or `RPO_VIOLATION` because no accepted target exists.

## Safety boundary

The gate must remain read-only.

Prohibited:

```text
backup execution
restore execution
WAL changes
retention changes
PostgreSQL configuration changes
service restarts
Kubernetes mutations
PVE mutations
credential changes
secret projection
raw database or dump content
```

## Acceptance evidence

Pending live run.
