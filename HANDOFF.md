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

Report:

```text
docs/reports/2026-08-23-m5-external-backup-target-discovery.md
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

A `dir` target cannot establish physical locality or physical independence.

## Open Milestone 5 roadmap gaps

```text
failure-domain assurance beyond same-PVE-storage relationship
retention effectiveness
accepted RPO/RTO targets and evaluation
restore tests / verified recovery exercises
```

Restore tests and recovery exercises remain intentionally deferred while infrastructure interaction is read-only.

## Active slice — failure-domain access-path discovery

Implementation:

```text
scripts/discovery/m5_failure_domain_access_path_discovery.py
tests/test_failure_domain_access_path_discovery.py
```

The discovery uses the hash-verified accepted VM assurance artifact and GET/read-only PVE VM configuration metadata.

For assets with accepted recovery-point mechanism evidence, it safely derives:

```text
subject PVE node
backup mechanism PVE node
current VM disk storage IDs
accepted backup mechanism storage IDs
storage-ID overlap
logical access-path separation
```

Allowed logical classifications:

```text
NOT_SEPARATED_AT_PVE_NODE_AND_STORAGE_ID
NOT_SEPARATED_AT_PVE_NODE_LAYER
SEPARATED_AT_OBSERVED_NODE_AND_STORAGE_ID_LAYER
UNKNOWN
```

These are logical PVE relationship statements only.

Always preserve:

```text
physical failure-domain independence: UNKNOWN
```

unless future authoritative evidence establishes physical disk/RAID/mount/host/facility topology.

Raw VM config values, disk volume names, paths, device identifiers, serials, mountpoints, endpoints, credentials, and backup contents must not be printed or persisted.

## Exact next step

On `mgmt-automation`:

1. run `tests/test_failure_domain_access_path_discovery.py`;
2. run `scripts/discovery/m5_failure_domain_access_path_discovery.py` with `PYTHONPATH=src`;
3. accept only safe node/storage-ID relationship projections;
4. do not promote physical failure-domain independence from logical coupling or separation.

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
- no secrets, raw sensitive config/state, raw task logs, raw VM config, database data, dump data, WAL contents, backup contents, or complete connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
