# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live/discovery report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Active execution checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #50: 5f28edc31f4ac5e9e34e697a502329c5df024bbd
active branch: feature/m5-pvc-infrastructure-recovery-context
package on active branch: 0.27.0
Milestone 5: active
mutation_allowed: false
management host: mgmt-automation
Kubernetes cluster: k3s-main
PVE source: pve-bm2 / delfan
```

The PVC Infrastructure Recovery Context v0.1 implementation is present but not accepted until the full repository suite and manual live gate pass.

PVE collection remains manual-only. Existing PVE credentials remain discovery-only and `runtime_credential_approved=false`.

## Stable Milestone 5 evidence

### Kubernetes PVC foundation

```text
PVC assets: 37
protection UNKNOWN: 37
unprotected_claims: 0
```

### Accepted VM recovery evidence

VM Backup Assurance v0.2 remains `STRICT_CORRELATION_ONLY` and accepts only `STRICT_SUCCESS_TASK_MATCH` evidence.

```text
assets: 12
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
protection UNKNOWN: 12
restore/integrity/failure-domain/RPO/RTO: UNKNOWN
unprotected_claims: 0
```

Relevant accepted timestamps:

```text
106 -> 2026-08-14T16:39:53Z
107 -> 2026-08-14T17:39:32Z
108 -> 2026-04-15T12:36:38Z
109 -> 2026-04-13T10:36:41Z
```

Accepted source inputs:

```text
/tmp/vm-backup-assurance.json
sha256: 14ccd7a082a6c901df6941e4c0540d24bd13ff96f29146a0e6ad689d4f824c1a

/tmp/proxmox-ve-backup-task-results.json
sha256: 18aaa4ad1a2dd260b4d0678e830f3c9267b2afaa1014b3563ec0e78a2b0135de
```

### Accepted database infrastructure contexts

PostgreSQL Kubernetes context PR #46:

```text
74a3c270e411a3823bd692abeb66e9fb3b6b6c04
instances_total: 8
infrastructure_recovery_observed: 8
postgresql_protection_unknown: 8
```

Management-host PostgreSQL relationship PR #47:

```text
cc0b8f36bc889a86cdd0181b90f48f8b21bc1da2
mgmt-automation -> PVE VMID 109
VM LAST_SUCCESSFUL_BACKUP=OBSERVED
local PostgreSQL infrastructure recovery=OBSERVED
```

MariaDB source discovery PR #48:

```text
460f72320071291c3eeecd95a89c99cc5e1fe656
```

MariaDB Infrastructure Recovery Context v0.1 PR #49:

```text
b836ebbedea5027a7107e17db2d19ba6f38c37ad
repository tests: 305 passed
instances_total: 4
persistence_observed: 3
persistence_unknown: 1
infrastructure_recovery_observed: 3
infrastructure_recovery_unknown: 1
mariadb_protection_unknown: 4
unprotected_claims: 0
```

Database-aware PostgreSQL and MariaDB backup mechanism, execution/result, artifact location, retention, restore, integrity, RPO, and RTO remain unknown.

## Accepted PVC infrastructure recovery coverage discovery

PR #50 merged at:

```text
5f28edc31f4ac5e9e34e697a502329c5df024bbd
```

Report:

```text
docs/reports/2026-08-16-m5-pvc-infrastructure-recovery-coverage-discovery.md
```

Accepted live discovery:

```text
accepted_foundation_pvc_assets: 37
live_pvc_assets: 37
foundation_count_match: true
pvc_bound: 37
current_workload_reference_observed: 22
current_workload_reference_none_observed: 15
explicit_storage_node_observed: 37
pve_vm_mapping_observed: 37
underlying_vm_last_successful_backup_observed: 37
infrastructure_recovery_observed: 37
infrastructure_recovery_unknown: 0
protection_promotions: 0
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

The 15 `NONE_OBSERVED` workload-reference results are bounded negative evidence only and are not orphan classifications.

## Active slice — PVC Infrastructure Recovery Context v0.1

Implementation:

```text
src/infra_assurance/pvc_infrastructure_recovery_context.py
schemas/pvc-infrastructure-recovery-context.schema.json
tests/test_pvc_infrastructure_recovery_context.py
tests/test_pvc_infrastructure_recovery_context_wiring.py
scripts/live_gates/m5_pvc_infrastructure_recovery_context.py
docs/milestone-5-pvc-infrastructure-recovery-context.md
docs/reports/2026-08-16-m5-pvc-infrastructure-recovery-context-live-test-gate.md
```

Inputs remain separate:

```text
PVC Backup Assurance Foundation v0.1
PVC infrastructure relationship evidence v0.1
VM Backup Assurance v0.2
```

Promotion rule:

```text
PVC foundation asset observed
+ Bound PVC / explicit storage node observed
+ Kubernetes node -> PVE VMID observed
+ accepted VM LAST_SUCCESSFUL_BACKUP=OBSERVED
+ STRICT_SUCCESS_TASK_MATCH
= infrastructure_recovery OBSERVED
```

A direct workload reference is context only and is not required for the storage-node/VM recovery chain.

The strict schema keeps all application-level assurance unknown:

```text
protection: UNKNOWN
backup freshness: UNKNOWN
backup mechanism: UNKNOWN
retention effectiveness: UNKNOWN
failure domain: UNKNOWN
integrity verification: UNKNOWN
restore verification: UNKNOWN
RPO: UNKNOWN
RTO: RTO_UNKNOWN
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

## Exact next action — live acceptance gate

Run:

```text
scripts/live_gates/m5_pvc_infrastructure_recovery_context.py
```

Expected counters if live state remains unchanged:

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
schema: PASS
```

Do not force expected values if live evidence differs; fail closed and review the change.

## Milestone 5 gaps still open

```text
PVC Infrastructure Recovery Context acceptance
PostgreSQL database-aware backup evidence
MariaDB database-aware backup evidence
PBS (future)
external backup targets
failure-domain assurance beyond storage-ID relationship
retention effectiveness
RPO/RTO
restore tests
```

## Later roadmap

```text
Milestone 6: IaC Governance
Milestone 7: Operational Intelligence Layer
Milestone 8: Reliability and Hardening
```

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance remain separate;
- infrastructure recovery evidence is not application/database-consistent backup evidence;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- observation credentials remain separate from control credentials;
- stale/current/unknown semantics remain explicit;
- no RPO violation is inferred without an accepted target;
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, or raw dump contents enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
