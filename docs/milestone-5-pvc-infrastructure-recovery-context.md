# Milestone 5 — PVC Infrastructure Recovery Context v0.1

## Purpose

Relate the accepted Kubernetes PVC backup-assurance foundation to bounded infrastructure-level recovery evidence without promoting application- or database-consistent backup protection.

## Inputs

The derivation consumes three separate evidence families:

1. Kubernetes PVC Backup Assurance Foundation v0.1.
2. Bounded PVC infrastructure relationship evidence v0.1.
3. Accepted VM Backup Assurance v0.2.

The source artifacts remain separate from the derived context.

## Promotion rule

A PVC may receive `infrastructure_recovery=OBSERVED` only when all of the following are established:

```text
PVC foundation asset exists
+ live PVC is Bound
+ explicit PV storage node is OBSERVED
+ Kubernetes node -> PVE VMID is OBSERVED
+ VM Backup Assurance source is complete
+ VM LAST_SUCCESSFUL_BACKUP=OBSERVED
+ strict success-task evidence is present
= PVC infrastructure recovery OBSERVED
```

A current direct workload reference is context, not a recovery precondition. `NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED` does not mean orphaned and does not downgrade an otherwise complete storage-node/VM recovery chain.

## Fail-closed behavior

The derivation rejects or downgrades evidence when:

- foundation and relationship asset identity sets differ;
- relationship subjects differ from foundation subjects;
- PVE source identities differ;
- storage node and node-to-VM mapping disagree;
- VM Backup Assurance is incomplete;
- VM last-successful-backup is not strictly correlated to a successful task;
- required relationship observations are unknown or failed.

## Assurance boundary

The strict schema fixes the following fields to unknown:

```text
protection_status: UNKNOWN
backup_freshness_status: UNKNOWN
backup_mechanism_status: UNKNOWN
retention_effectiveness_status: UNKNOWN
failure_domain_status: UNKNOWN
integrity_verification_status: UNKNOWN
restore_verification_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

It also fixes:

```text
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

A VM-level successful backup is infrastructure recovery context only. It does not establish application-consistent backup, database-consistent backup, restore viability, data integrity, independent failure-domain protection, RPO, or RTO.

Timestamp age is not classified as stale or an RPO violation without an accepted target.

## Runtime boundary

This slice is pure derivation plus a manual live gate.

It adds no systemd/runtime wiring and no new continuous collector.

Initial infrastructure interaction remains read-only.

## Sensitive-data boundary

Do not project or persist:

- Kubernetes Secret values;
- environment values;
- container commands or args;
- PV backing paths or CSI handles;
- raw PVE VM config;
- disk or network details;
- credentials;
- application/database data;
- backup contents.

## Expected accepted live state

If live evidence remains unchanged from the accepted 2026-08-16 discovery:

```text
assets_total: 37
direct_workload_reference_observed: 22
direct_workload_reference_none_observed: 15
infrastructure_recovery_observed: 37
infrastructure_recovery_unknown: 0
underlying_vm_last_successful_backup_observed: 37
protection_unknown: 37
restore_verification_unknown: 37
integrity_verification_unknown: 37
failure_domain_unknown: 37
rpo_unknown: 37
rto_unknown: 37
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```
