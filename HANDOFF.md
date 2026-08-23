# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #59: add76eba38441dd6bf23732d1297f1b494e742c1
active branch: agent/m5-failure-domain-access-path-discovery
package on accepted main: 0.27.0
Milestone 5: ACTIVE — NOT COMPLETE
mutation_allowed: false
management host: mgmt-automation
Kubernetes cluster: k3s-main
PVE source: pve-bm2 / delfan
```

PVE collection remains manual-only. Existing PVE credentials remain discovery-only and `runtime_credential_approved=false`.

## Stable Milestone 5 checkpoint

Current accepted evidence includes:

```text
VM assets: 12
VM last_successful_backup OBSERVED: 6
VM last_successful_backup UNKNOWN: 6
strict successful VZDUMP correlations: 9
current declared PVE backup jobs: 0
accepted PVE recovery-point storage: local
storage retention declaration: prune-backups=keep-all=1
retention effectiveness: UNKNOWN

PVC assets: 37
PVC infrastructure_recovery_observed: 37
PVC protection_unknown: 37
PVC restore/RPO/RTO: UNKNOWN

PostgreSQL Kubernetes instances: 8
PostgreSQL infrastructure_recovery_observed: 8
PostgreSQL database-aware backup mechanism: UNKNOWN 8/8
management-host PostgreSQL configured backup mechanism: UNKNOWN

MariaDB candidates: 4
MariaDB infrastructure_recovery_observed: 3
MariaDB infrastructure_recovery_unknown: 1
MariaDB database-aware backup mechanism: UNKNOWN 4/4
```

No accepted `UNPROTECTED`, stale-backup, or RPO-violation claims have been promoted from bounded signal absence.

## Accepted RPO/RTO declaration discovery

```text
RPO target: UNKNOWN
RTO target: UNKNOWN
RPO result: UNKNOWN
RTO result: UNKNOWN
```

No explicit target was observed in the bounded safe declared-state repository.

## Accepted external-backup-target discovery

PR #59 merged at:

```text
add76eba38441dd6bf23732d1297f1b494e742c1
```

Accepted state:

```text
backup-capable PVE targets: 1
safe target: local / dir
PBS-like enabled targets: 0
network-storage-like enabled targets: 0
external backup target: NONE_OBSERVED_IN_BOUNDED_PVE_STORAGE_SCOPE
physical failure-domain independence: UNKNOWN
```

## Accepted failure-domain access-path discovery

Report:

```text
docs/reports/2026-08-23-m5-failure-domain-access-path-discovery.md
```

Focused tests:

```text
4 passed in 0.06s
```

Accepted live result:

```text
/tmp/vm-backup-assurance.json: hash_match=True
accepted_assets_with_recovery_point_mechanism: 6
live_vm_config_observed: 6
live_vm_config_failed_to_observe: 0
same_pve_node_observed: 6
storage_id_overlap_observed: 6
not_separated_at_pve_node_and_storage_id: 6
logical_access_path_separation_unknown: 0
physical_failure_domain_independence_claims: 0
restore_verification_claims: 0
unprotected_claims: 0
rpo_violation_claims: 0
discovery_rc: 0
```

Accepted relationship for VMIDs `100,101,106,107,108,109`:

```text
same PVE node: OBSERVED
VM storage ID: local
accepted backup storage ID: local
storage-ID overlap: OBSERVED
logical access-path separation: NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID
physical failure-domain independence: UNKNOWN
```

Logical coupling is not proof that VM and backup data occupy the same physical disk or RAID group.

## Milestone 5 remaining gaps

```text
physical failure-domain independence beyond logical PVE node/storage coupling
retention effectiveness
accepted RPO/RTO targets and evaluation
restore/integrity verification and recovery exercises
```

The current read-only evidence lanes have now been exercised for VM/PVC/database recovery context, PVE policy/provenance/retention declaration, RPO/RTO declaration search, external-target discovery, and logical failure-domain relationship.

Further promotion of the remaining items requires at least one of:

```text
new authoritative policy/declaration evidence
stronger physical storage topology evidence
complete historical retention evidence with policy-effective period
controlled restore/integrity exercises
```

Restore/integrity exercises require future controlled mutation and explicit authorization. Do not create, restore, delete, move, prune, or alter backups under the current boundary.

## Exact next step

Create a documentation-only **Milestone 5 read-only discovery closure checkpoint**.

The checkpoint must state:

```text
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
remaining unknowns: explicit and preserved
mutation-required work: deferred
```

Do not manufacture additional probes merely to reduce `UNKNOWN`. After the checkpoint, the next useful project slice may move to Milestone 6 IaC Governance while Milestone 5 controlled-recovery work remains explicitly deferred.

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance remain separate;
- declared backup policy is not observed backup success;
- storage retention declaration is not retention effectiveness;
- infrastructure recovery evidence is not application/database-consistent backup evidence;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- stale/current/unknown semantics remain explicit;
- no RPO violation is inferred without an accepted target;
- logical node/storage coupling is not the same as physical media topology;
- unknowns are not forced closed without authoritative evidence;
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, dump data, WAL contents, backup contents, or complete connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
