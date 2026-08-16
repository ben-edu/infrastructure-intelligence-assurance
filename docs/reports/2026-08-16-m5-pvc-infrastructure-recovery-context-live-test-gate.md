# Milestone 5 PVC Infrastructure Recovery Context Live Test Gate — 2026-08-16

## Status

Pending live acceptance on `mgmt-automation`.

## Implementation under test

```text
branch: feature/m5-pvc-infrastructure-recovery-context
package: 0.27.0
pvc_infrastructure_recovery_context_version: 0.1
mutation_allowed: false
```

Files:

```text
src/infra_assurance/pvc_infrastructure_recovery_context.py
schemas/pvc-infrastructure-recovery-context.schema.json
tests/test_pvc_infrastructure_recovery_context.py
tests/test_pvc_infrastructure_recovery_context_wiring.py
scripts/live_gates/m5_pvc_infrastructure_recovery_context.py
docs/milestone-5-pvc-infrastructure-recovery-context.md
```

## Accepted discovery baseline

```text
PVC foundation assets: 37
live PVC assets: 37
Bound PVCs: 37
direct workload reference observed: 22
direct workload reference none observed: 15
explicit storage node observed: 37
PVE VM mapping observed: 37
underlying VM last-successful-backup observed: 37
infrastructure recovery observed: 37
protection promotions: 0
```

## Acceptance criteria

The full repository suite must pass and the manual live gate must validate the strict schema.

Expected counters if live state is unchanged:

```text
assets_total: 37
direct_workload_reference_observed: 22
direct_workload_reference_none_observed: 15
infrastructure_recovery_observed: 37
infrastructure_recovery_unknown: 0
infrastructure_recovery_failed_to_observe: 0
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
```

A changed live state must fail closed for review rather than being forced to these counters.

## Trust boundary

Even when PVC infrastructure recovery is `OBSERVED`, this gate does not establish application-consistent or database-consistent backup, retention, integrity, restore verification, failure-domain independence, RPO, or RTO.

`NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED` is bounded relationship evidence only and must not be classified as orphaned or `UNPROTECTED`.

Timestamp age alone must not produce `BACKUP_STALE` or `RPO_VIOLATION` without an accepted target.

## Safety

The gate is manual and read-only.

It must not project Kubernetes Secret values, environment values, container commands/args, PV backing paths, CSI handles, application/database data, backup contents, raw PVE VM config, disk/network details, or credentials.

No infrastructure mutation is allowed.

## Acceptance evidence

Pending live execution.
