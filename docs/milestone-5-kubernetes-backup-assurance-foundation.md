# Milestone 5 — Kubernetes Backup and Recovery Assurance Foundation

## Goal

Start Backup and Recovery Assurance with the smallest trustworthy vertical slice: identify current Kubernetes PVC stateful assets and explicitly separate asset observation from backup protection evidence.

## Inputs

```text
/var/lib/infra-assurance/evidence/kubernetes.json
/var/lib/infra-assurance/evidence/topology.json
```

No new live infrastructure query is performed by this slice.

## Outputs

```text
/var/lib/infra-assurance/evidence/backup-assurance.json
/var/lib/infra-assurance/evidence/backup-assurance.md
```

Contract:

```text
backup_assurance_version: 0.1
scope.asset_type: KUBERNETES_PVC
scope.derived_only: true
scope.authoritative_backup_source_integrated: false
mutation_allowed: false
```

## Asset discovery

A PVC asset is emitted only when the current Kubernetes snapshot contains a `PersistentVolumeClaim` envelope with:

```text
plane: observed
existence: PRESENT
observation_status: COMPLETE
```

PVC collection observation status remains explicit at artifact level.

If PVC collection fails, the artifact must report `FAILED_TO_OBSERVE` and must not reinterpret the missing asset list as a complete zero-PVC result.

## Safe asset context

Each PVC asset includes only bounded Kubernetes storage facts already present in the accepted snapshot:

```text
phase
storage_class
access_modes
requested_storage
capacity
volume_name
```

Freshness is calculated from the existing observation expiry.

## Workload relationship context

Existing topology relations of type:

```text
WORKLOAD_REFERENCES_PVC
```

may be attached with basis `OBSERVED_REFERENCE`.

This relationship is controller-spec context, not proof of exclusive ownership or current Pod-level use.

If no direct relation is observed, use:

```text
NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED
```

Do not call the PVC orphaned.

If one or more PVC/Deployment/StatefulSet/DaemonSet collection scopes are incomplete, use:

```text
RELATION_SCOPE_INCOMPLETE
```

and preserve any observed PVC assets independently.

## Assurance boundary

Because no authoritative backup source is integrated in this slice, every PVC asset must remain:

```text
protection_status: UNKNOWN
backup_freshness_status: UNKNOWN
integrity_verification_status: UNKNOWN
restore_verification_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

The artifact must report:

```text
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
```

StorageClass, Bound phase, capacity, workload kind, labels, annotations, snapshot naming, and volume names are not protection evidence.

## Future evidence requirements

Each asset carries bounded requirements for later authoritative sources:

```text
BACKUP_MECHANISM
LAST_SUCCESSFUL_BACKUP
BACKUP_RETENTION
BACKUP_FAILURE_DOMAIN
BACKUP_INTEGRITY_VERIFICATION
RESTORE_TEST
RPO_TARGET_AND_RESULT
RTO_TARGET_AND_RESULT
```

The platform should later satisfy these from specialized backup/database systems rather than implementing backup execution itself.

## Runtime

Package version: `0.19.0`.

The new derived post-step runs after the accepted Milestone 4 chain:

```text
prometheus_rule_context_integration
backup_assurance_foundation
```

The slice requires no RBAC expansion.

## Acceptance boundary

Live validation must prove:

- no RBAC diff;
- no query-capable client in the foundation module;
- full tests pass;
- systemd stage exits `0/SUCCESS`;
- current PVC count matches the complete Kubernetes snapshot;
- every emitted asset is `PRESENT` from complete observation;
- freshness matches upstream expiry semantics;
- direct workload relations, when present, use accepted topology evidence only;
- all protection/restore/RPO states remain unknown by design;
- `unprotected_claims=0`;
- no labels/annotations/secrets/credentials/raw URLs enter the artifact.

Do not integrate PBS/Proxmox/database backup credentials in the same slice.
