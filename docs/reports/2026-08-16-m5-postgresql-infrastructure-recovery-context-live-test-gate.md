# Milestone 5 PostgreSQL Infrastructure Recovery Context Live Test Gate — 2026-08-16

## Status

Accepted.

The bounded PostgreSQL infrastructure-recovery context v0.1 passed the full repository gate and the live read-only acceptance gate on `mgmt-automation`.

## Accepted implementation

```text
branch: feature/m5-postgresql-infrastructure-recovery-context
package: 0.25.0
postgresql_infrastructure_recovery_context_version: 0.1
mutation_allowed: false
```

The implementation is pure derivation and is not runtime/systemd-wired.

Reusable live gate:

```text
scripts/live_gates/m5_postgresql_infrastructure_recovery_context.py
```

## Repository gate

```text
292 passed in 1.23s
repository gate: PASS
```

## Live relationship gate

Observed persistent PostgreSQL workload relationships:

```text
8
```

Bounded PVE node-to-VM mappings:

```text
k3s-master-01 -> VMID 106
k3s-worker-01 -> VMID 107
k3s-worker-02 -> VMID 108
```

All eight workload/PVC/node/VM relationships matched the accepted discovery:

```text
discovery_mapping_match: true
```

Accepted instance mapping:

```text
drfarah-staging       -> k3s-worker-02 -> VMID 108
fastapi-platform      -> k3s-worker-01 -> VMID 107
fastapi-platform-dev  -> k3s-worker-01 -> VMID 107
keycloak              -> k3s-master-01 -> VMID 106
openproject           -> k3s-worker-01 -> VMID 107
soria-academie        -> k3s-worker-02 -> VMID 108
soria-prospecting     -> k3s-worker-01 -> VMID 107
toilettage            -> k3s-worker-01 -> VMID 107
```

The PVE credential remained discovery-only:

```text
runtime_credential_approved: false
```

## Accepted VM source verification

Both previously accepted input artifacts matched their recorded SHA256 values:

```text
/tmp/vm-backup-assurance.json
sha256: 14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a
hash_match: true

/tmp/proxmox-ve-backup-task-results.json
sha256: 18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
hash_match: true
```

VM Backup Assurance v0.2 derivation:

```text
schema: PASS
VM assets: 12
LAST_SUCCESSFUL_BACKUP observed: 6
```

Relevant accepted VM timestamps:

```text
106 -> 2026-08-14T16:39:53Z
107 -> 2026-08-14T17:39:32Z
108 -> 2026-04-15T12:36:38Z
accepted_vm_timestamps_match: true
```

## PostgreSQL context gate

```text
PostgreSQL context schema: PASS
version: 0.1
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
acceptance_counters_match: true
gate_rc: 0
```

## Trust interpretation

`infrastructure_recovery=OBSERVED` means the bounded chain was observed and joined successfully:

```text
PostgreSQL workload
-> persistent PVC
-> explicit PV storage node
-> K3s node
-> PVE VMID
-> accepted strict VM LAST_SUCCESSFUL_BACKUP evidence
```

It does not establish PostgreSQL-consistent backup, PostgreSQL backup execution/result, artifact location, retention effectiveness, restore verification, integrity verification, RPO satisfaction, or RTO satisfaction.

The VMID 108 timestamp is retained as observed evidence only. No `BACKUP_STALE` or `RPO_VIOLATION` classification is accepted because no RPO/freshness target exists.

## First live attempt

The first live attempt passed 290 repository tests but rejected at the PV hostname-affinity projection because the nested kubectl JSONPath returned zero hostname values. That rejection was a gate-projection failure, not evidence that node affinity disappeared.

The retry replaced that projection with a bounded Go-template and added safety tests for the versioned live-gate script. The accepted retry then passed 292 repository tests and reproduced all eight previously observed relationships.

## Safety boundary

The accepted gate did not read or project Kubernetes Secret values, Pod environment values, PV backing paths, CSI volume handles, VM configuration, database rows, dump contents, or credential values.

No backup, restore, WAL, retention, PostgreSQL configuration, service, Kubernetes, PVE, or credential mutation occurred.
