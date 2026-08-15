# Project Handoff

This is the compact continuation checkpoint for the Infrastructure Intelligence & Assurance Platform. Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable checkpoint

- repository: `ben-edu/infrastructure-intelligence-assurance`
- stable branch: `main`
- current main HEAD after post-PR28 continuity merge: `434079ec90edc0cccd94b4e697f92b615aa87cd1`
- accepted PR #28 code merge: `9b32c7657a648c04081c9bcc4f5112872c2ecd2c`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- cluster: `k3s-main`
- runtime user: `infra-assurance`
- oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

Milestones 0–3 are live validated. The current evidence-first Milestone 4 vertical path is accepted and sufficiently complete to proceed to Milestone 5. `PROMETHEUS_RULE_INPUTS` remains a recommended live verification delegated to Prometheus; do not add an arbitrary PromQL executor without a separately justified need.

Known intentional drift remains:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Accepted Milestone 4 endpoint

Final incident contract:

```text
incident_candidates_version: 0.4
prometheus_rule_context_integration.version: 0.1
prometheus_rule_context_integration.mode: EXACT_COMPLETE_ONLY
mutation_allowed: false
```

Accepted current Platform drill-down:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PROMETHEUS_RULE_INPUTS  -> PROMETHEUS_RULE_INPUTS
```

PR #28 live gate passed with `204 passed`, all runtime stages `0/SUCCESS`, complete exact `KubeCPUOvercommit` / `Watchdog` rule context, no integration unknowns, no non-active candidate enrichment, and clean sensitive/raw-URL guards.

## Active work — PR #30 Milestone 5 Kubernetes backup assurance foundation

- PR: `#30 Milestone 5 Kubernetes backup assurance foundation`
- branch: `feature/m5-kubernetes-backup-assurance-foundation`
- base main: `434079ec90edc0cccd94b4e697f92b615aa87cd1`
- package version: `0.19.0`
- status: Draft; pending repository and management-host live acceptance
- intended RBAC change: none
- new infrastructure/backup/database query: none
- new credentials: none
- mutation: none

Purpose: identify Kubernetes PVC stateful assets that require backup/recovery assurance while representing missing authoritative backup evidence as `UNKNOWN`, never as `UNPROTECTED`.

New derived artifacts:

```text
/var/lib/infra-assurance/evidence/backup-assurance.json
/var/lib/infra-assurance/evidence/backup-assurance.md
```

Inputs are local accepted artifacts only:

```text
/var/lib/infra-assurance/evidence/kubernetes.json
/var/lib/infra-assurance/evidence/topology.json
```

Runtime final stage:

```text
prometheus_rule_context_integration
backup_assurance_foundation
```

Contract:

```text
backup_assurance_version: 0.1
scope.asset_type: KUBERNETES_PVC
scope.derived_only: true
scope.authoritative_backup_source_integrated: false
mutation_allowed: false
```

PVC assets are emitted only from complete PRESENT observed `PersistentVolumeClaim` evidence. Safe storage projection is limited to phase, StorageClass, access modes, requested storage, capacity, and volume name.

Workload context may use only accepted topology `WORKLOAD_REFERENCES_PVC` / `OBSERVED_REFERENCE` relations. No direct controller relation is explicitly not an orphan classification. Relationship scope is partial if PVC/Deployment/StatefulSet/DaemonSet collection scope is incomplete.

Because this first slice has no authoritative backup source, schema v0.1 hard-fixes every asset to:

```text
protection_status: UNKNOWN
backup_freshness_status: UNKNOWN
integrity_verification_status: UNKNOWN
restore_verification_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

Global invariants:

```text
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
```

StorageClass, Bound phase, capacity, volume name, workload kind, labels, annotations, snapshots, or naming conventions are not backup-protection evidence.

Each asset requires future authoritative evidence for:

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

Relevant files:

```text
src/infra_assurance/backup_assurance_foundation.py
schemas/backup-assurance-foundation.schema.json
docs/decisions/0020-derive-kubernetes-pvc-backup-assurance-foundation.md
docs/milestone-5-kubernetes-backup-assurance-foundation.md
docs/reports/2026-08-15-m5-kubernetes-backup-assurance-foundation-live-test-gate.md
```

## Exact next step

Run PR #30 repository/live gate on `mgmt-automation`:

1. verify no RBAC diff;
2. verify the foundation module is derived-only and has no query-capable client;
3. run full pytest;
4. bootstrap if green;
5. confirm package `0.19.0` and `backup_assurance_foundation` exits `0/SUCCESS` as final post-step;
6. compare asset count exactly with complete PRESENT PVC evidence in the same snapshot;
7. verify each asset's freshness and direct workload relations are traceable to upstream evidence;
8. verify every protection/restore/RPO state remains unknown by design and `unprotected_claims=0`;
9. verify all eight future authoritative evidence targets exist per asset;
10. verify labels/annotations/secrets/credentials/raw URLs are absent.

Do not merge PR #30 before live acceptance. Do not add PBS/Proxmox/PostgreSQL/MariaDB backup credentials or APIs in this slice.

## Trust invariants

- observation credentials remain separate from future control credentials;
- infrastructure interaction remains read-only;
- collector failure is explicit;
- stale is not current;
- unknown is not absent;
- inference is not fact;
- declared and observed state remain separate;
- specialized systems remain authoritative;
- no passwords, tokens, private keys, raw Kubernetes Secret values, sensitive Terraform state, or complete sensitive connection strings enter evidence/AI context;
- current generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
