# Milestone 5 PVC Infrastructure Recovery Coverage Discovery — 2026-08-16

## Status

Accepted bounded read-only discovery on `mgmt-automation`.

## Scope

Determine how much of the accepted 37-PVC Kubernetes backup-assurance foundation can be related to infrastructure-level VM recovery evidence without promoting application/database backup protection.

## Accepted live evidence

```text
kubectl context: default
accepted_foundation_pvc_assets: 37
live_pvc_assets: 37
foundation_count_match: true
```

All 37 live PVCs were `Bound` and used `local-path` in the observed scope.

PVE node mapping covered three Kubernetes storage nodes:

```text
k3s-master-01
k3s-worker-01
k3s-worker-02
```

The bounded PVE observation used `GET /cluster/resources?type=vm` with `runtime_credential_approved=false`.

Accepted VM source verification passed for both previously accepted source artifacts:

```text
/tmp/vm-backup-assurance.json: hash_match=true
/tmp/proxmox-ve-backup-task-results.json: hash_match=true
```

## Coverage summary

```text
pvc_assets_total: 37
pvc_bound: 37
current_workload_reference_observed: 22
current_workload_reference_none_observed: 15
explicit_storage_node_observed: 37
explicit_storage_node_unknown: 0
storage_node_failed_to_observe: 0
pve_vm_mapping_observed: 37
pve_vm_mapping_unknown: 0
underlying_vm_last_successful_backup_observed: 37
underlying_vm_last_successful_backup_unknown: 0
infrastructure_recovery_observed: 37
infrastructure_recovery_unknown: 0
infrastructure_recovery_failed_to_observe: 0
protection_promotions: 0
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

## Workload-reference interpretation

Twenty-two PVCs had a current direct controller reference observed in the bounded relationship scope. Fifteen had no current direct controller reference observed.

`NONE_OBSERVED` is bounded negative evidence only. It is not an orphan classification, because Pod-level mounts, generated StatefulSet claims, Jobs, ephemeral controller relationships, or other consumers may be outside the direct-controller relationship model.

Workload-reference presence was not required to promote infrastructure recovery context. The accepted infrastructure chain was:

```text
PVC Bound
+ explicit PV storage node observed
+ Kubernetes node -> PVE VMID observed
+ accepted VM LAST_SUCCESSFUL_BACKUP=OBSERVED
+ strict VM success-task evidence
= infrastructure recovery context OBSERVED
```

## Trust boundary

`infrastructure_recovery=OBSERVED` means only that the PVC's bound storage relationship can be related to a Kubernetes storage node, a PVE VMID, and accepted strict VM last-successful-backup evidence.

It does not establish:

```text
application-consistent backup
database-consistent backup
backup mechanism
backup execution/result at application level
retention effectiveness
backup integrity verification
restore verification
failure-domain independence
RPO
RTO
```

No PVC protection status was promoted. No PVC was classified `UNPROTECTED`, `BACKUP_STALE`, or `RPO_VIOLATION`.

Timestamp age remains evidence only; no stale/RPO classification is allowed without an accepted target.

## Safety

The discovery did not read or print Kubernetes Secret values, environment values, container commands/args, PV backing paths, CSI handles, raw PVE VM config, disk/network details, credentials, application/database data, or backup contents.

Only read-only observations were used. No infrastructure mutation occurred.

## Next bounded slice

Implement a pure-derived PVC Infrastructure Recovery Context artifact that joins the accepted PVC foundation with bounded PVC -> storage-node -> PVE-VM -> accepted VM last-successful-backup evidence.

The derived artifact must preserve:

```text
assets_total: 37
infrastructure_recovery_observed: 37
protection_unknown: 37
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

No runtime/systemd wiring and no new live collector should be added in that slice.
