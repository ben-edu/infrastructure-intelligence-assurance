# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live/discovery report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main before PR #49: 460f72320071291c3eeecd95a89c99cc5e1fe656
active branch: feature/m5-mariadb-infrastructure-recovery-context
package: 0.26.0
Milestone 5: active
mutation_allowed: false
management host: mgmt-automation
Kubernetes cluster: k3s-main
PVE source: pve-bm2 / delfan
```

PR #49 passed its live acceptance gate on 2026-08-16 and is ready to merge.

## Stable Milestone 5 evidence

### Kubernetes PVC foundation

```text
PVC assets: 37
protection UNKNOWN: 37
unprotected_claims: 0
```

This foundation intentionally does not yet join all PVCs to workload/VM recovery evidence.

### VM recovery evidence

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

### PostgreSQL infrastructure recovery context

PR #46 merged at:

```text
74a3c270e411a3823bd692abeb66e9fb3b6b6c04
```

Accepted Kubernetes PostgreSQL context:

```text
instances_total: 8
infrastructure_recovery_observed: 8
underlying_vm_last_successful_backup_observed: 8
postgresql_protection_unknown: 8
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
```

Management-host PostgreSQL is related to PVE VMID 109 with accepted strict VM last-successful-backup evidence. PR #47 merged at:

```text
cc0b8f36bc889a86cdd0181b90f48f8b21bc1da2
```

PostgreSQL database-aware mechanism, execution/result, artifact location, retention, restore, integrity, RPO, and RTO remain unknown.

### MariaDB/MySQL-compatible discovery

PR #48 merged at:

```text
460f72320071291c3eeecd95a89c99cc5e1fe656
```

Accepted candidates:

```text
bookstack/Deployment/mariadb
  persistence: OBSERVED
  storage node: k3s-worker-02
  VMID: 108

misp/Deployment/mariadb
  persistence: OBSERVED
  storage node: k3s-master-01
  VMID: 106

misp/Deployment/mariadb-v2
  persistence: UNKNOWN
  infrastructure recovery: UNKNOWN

moodle/StatefulSet/moodle-mariadb
  persistence: OBSERVED
  storage node: k3s-worker-02
  VMID: 108
```

Matching MariaDB/backup CronJobs and Jobs in the bounded inspected scope: `0`. This is bounded negative evidence only, not an `UNPROTECTED` claim.

### MariaDB infrastructure recovery context v0.1

Implementation:

```text
src/infra_assurance/mariadb_infrastructure_recovery_context.py
schemas/mariadb-infrastructure-recovery-context.schema.json
scripts/live_gates/m5_mariadb_infrastructure_recovery_context.py
docs/milestone-5-mariadb-infrastructure-recovery-context.md
docs/reports/2026-08-16-m5-mariadb-infrastructure-recovery-context-live-test-gate.md
```

Accepted gate:

```text
package: 0.26.0
repository tests: 305 passed in 1.16s
schema: PASS
instances_total: 4
persistence_observed: 3
persistence_unknown: 1
persistence_failed_to_observe: 0
infrastructure_recovery_observed: 3
infrastructure_recovery_unknown: 1
infrastructure_recovery_failed_to_observe: 0
underlying_vm_last_successful_backup_observed: 3
mariadb_protection_unknown: 4
mariadb_backup_mechanism_unknown: 4
mariadb_backup_execution_unknown: 4
mariadb_restore_verification_unknown: 4
mariadb_integrity_verification_unknown: 4
mariadb_rpo_unknown: 4
mariadb_rto_unknown: 4
unprotected_claims: 0
backup_stale_claims: 0
rpo_violation_claims: 0
accepted_vm_timestamps_match: true
acceptance_counters_match: true
gate_rc: 0
```

`misp/mariadb-v2` remains `UNKNOWN`, not `UNPROTECTED`.

MariaDB database-aware mechanism, execution/result, artifact location, retention, restore, integrity, RPO, and RTO remain unknown.

## Exact next step — PVC infrastructure recovery coverage discovery

Before adding more database-specific mechanism probes, close the next smallest cross-cutting Milestone 5 gap: determine how much of the existing 37-PVC foundation can be related to accepted infrastructure recovery evidence.

Discovery first. Do not promote PVC protection and do not implement runtime collection yet.

Required questions:

```text
For each of the 37 accepted PVC assets, can a current workload owner be safely identified?
Can the bound PV expose an explicit Kubernetes storage node without reading backing paths or CSI handles?
Can that Kubernetes node be related to an accepted PVE VMID?
Does that VMID have accepted LAST_SUCCESSFUL_BACKUP evidence?
Which PVCs have a complete infrastructure recovery chain?
Which remain UNKNOWN or FAILED_TO_OBSERVE?
```

Safe output may include namespace, PVC name, bound state, storage class, workload identity, storage node, PVE VMID, and accepted VM backup status/timestamp.

Do not expose Secret/env values, PV backing paths, CSI handles, raw VM config, disks, networks, credentials, application data, or backup contents.

A complete PVC -> node -> VM -> VM backup chain is infrastructure recovery context only. It must not promote application/database-consistent protection.

## Milestone 5 gaps still open

```text
PVC infrastructure recovery coverage beyond foundation
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
