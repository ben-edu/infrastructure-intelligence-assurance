# Milestone 5 PVC Infrastructure Recovery Context Live Test Gate — 2026-08-16

## Status

Accepted on `mgmt-automation` after bounded retries.

## Implementation accepted

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
tests/test_pvc_infrastructure_recovery_context_privileged_runner.py
scripts/live_gates/m5_pvc_infrastructure_recovery_context.py
scripts/live_gates/run_m5_pvc_infrastructure_recovery_context.sh
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

## Gate history

### Retry 1 — repository regression detected

The first live-gate attempt correctly rejected before infrastructure correlation because an older MariaDB wiring test hard-coded package version `0.26.0` while the active branch was `0.27.0`.

```text
package: 0.27.0
repository tests: 325 passed, 1 failed
failure: test_mariadb_infrastructure_recovery_context_wiring.py package version assertion
gate_rc: 2
```

The test was corrected to verify package-version synchronization rather than freezing a historical version.

### Retry 2 — stored evidence permission boundary detected

The second attempt passed the full repository suite but could not read normalized stored Kubernetes evidence as the non-root shell user.

```text
repository tests: 326 passed
repository gate: PASS
stage: Kubernetes evidence
detail: FAILED_TO_READ PermissionError
gate_rc: 2
```

No permission or ownership change was made. A bounded wrapper was added that uses `sudo cat` only for the two normalized evidence artifacts and runs the actual gate as the current non-root user.

### Accepted retry

Command:

```text
bash scripts/live_gates/run_m5_pvc_infrastructure_recovery_context.sh
```

Accepted evidence:

```text
package: 0.27.0
repository tests: 328 passed in 1.41s
repository gate: PASS
foundation schema: PASS
foundation_assets: 37
live_pvc_assets: 37
storage_nodes_to_map: 3
PVE GET /cluster/resources?type=vm: HTTP 200
runtime_credential_approved: false
relationship_source_status: COMPLETE
VM Backup Assurance v0.2 schema: PASS
PVC context schema: PASS
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
accepted_vm_timestamps_match: true
acceptance_counters_match: true
gate_rc: 0
```

## Interpretation

`infrastructure_recovery=OBSERVED` means only:

```text
PVC foundation asset observed
+ Bound PVC / explicit Kubernetes storage node observed
+ Kubernetes node -> PVE VMID observed
+ accepted VM LAST_SUCCESSFUL_BACKUP=OBSERVED
+ STRICT_SUCCESS_TASK_MATCH evidence
```

It does not establish application-consistent or database-consistent backup, retention effectiveness, integrity verification, restore verification, failure-domain independence, RPO, or RTO.

`NO_DIRECT_CONTROLLER_REFERENCE_OBSERVED` for 15 PVCs is bounded relationship context only. It is not an orphan or `UNPROTECTED` classification.

Timestamp age alone does not produce `BACKUP_STALE` or `RPO_VIOLATION` without an accepted target.

## Privilege boundary

The accepted wrapper used privileged access only to read:

```text
/var/lib/infra-assurance/evidence/kubernetes.json
/var/lib/infra-assurance/evidence/topology.json
```

Temporary copies were created under `/tmp`, read by the non-root gate, and removed when the wrapper exited.

No file permission or ownership changes were made. The actual Kubernetes/PVE gate remained non-root.

## Safety

No Kubernetes Secret values, environment values, container commands/args, PV backing paths, CSI handles, application/database data, backup contents, raw PVE VM config, disk/network details, or credentials were projected.

No infrastructure mutation occurred.

## Acceptance decision

PVC Infrastructure Recovery Context v0.1 is accepted.
