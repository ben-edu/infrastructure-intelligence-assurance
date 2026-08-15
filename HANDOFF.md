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
- current main HEAD after PR #28 merge: `9b32c7657a648c04081c9bcc4f5112872c2ecd2c`
- accepted PR #28 code merge: `9b32c7657a648c04081c9bcc4f5112872c2ecd2c`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- cluster: `k3s-main`
- runtime user: `infra-assurance`
- oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

Milestones 0–3 are live validated.

Milestone 4 accepted/live-validated slices now cover:

- Prometheus runtime;
- Alertmanager handling correlation;
- Kubernetes Event correlation;
- incident candidate grouping and drill-down;
- bounded EndpointSlice/Pod/ReplicaSet routing ownership;
- validated alert infrastructure identities;
- routing ownership integration;
- scope-aware drill-down recommendations;
- bounded Prometheus alert-rule context;
- exact Prometheus rule-context integration into incident drill-down, merged in PR #28 at `9b32c7657a648c04081c9bcc4f5112872c2ecd2c`.

Known intentional drift remains:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Accepted PR #28 Prometheus rule-context integration

Package version: `0.18.0`.

No RBAC change, infrastructure/telemetry query, Loki/OpenTelemetry integration, or mutation was added.

Accepted final contract:

```text
incident_candidates_version: 0.4
prometheus_rule_context_integration.version: 0.1
prometheus_rule_context_integration.mode: EXACT_COMPLETE_ONLY
source_status.prometheus_rule_context: COMPLETE
mutation_allowed: false
```

Accepted repository/live evidence:

```text
RBAC changes: none
query-capable markers: none
204 passed in 1.29s
all runtime stages: status=0/SUCCESS
active candidates: 1
active Platform candidate: Platform/k3s-main
active alert names: KubeCPUOvercommit, Watchdog
selection: COMPLETE_EXACT_RULE_MATCH
matched rules: 2
unmatched: none
integration unknowns: none
non-active candidates enriched: none
forbidden projected keys: none
raw URL markers: false
```

Accepted current Platform drill-down:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PROMETHEUS_RULE_INPUTS  -> PROMETHEUS_RULE_INPUTS
```

The previous generic `PROMETHEUS_KUBERNETES` Platform target is removed only because the rule source is COMPLETE and exact coverage is complete. Partial/failed/unmatched/mismatched rule evidence keeps the generic fallback.

Accepted exact rule metadata:

```text
Watchdog          | group=general.rules        | state=FIRING | health=OK | duration=0s
KubeCPUOvercommit | group=kubernetes-resources | state=FIRING | health=OK | duration=600s
```

Rule state/health is not current PromQL input evidence and is not root-cause proof. `PROMETHEUS_RULE_INPUTS` remains a recommended live verification delegated to the authoritative metrics system.

Relevant accepted docs:

```text
docs/decisions/0019-integrate-exact-prometheus-rule-context.md
docs/milestone-4-prometheus-rule-context-integration.md
docs/reports/2026-08-15-m4-prometheus-rule-context-integration-live-test-gate.md
```

## Milestone 4 closure boundary

The Delivery Roadmap requires observability intelligence capabilities such as signal correlation, incident grouping, impact summaries, alert enrichment, evidence/confidence reporting, and recommended drill-down/live checks. It does not require the platform to execute every recommended Prometheus metric query.

Do not add an arbitrary PromQL executor merely to consume `PROMETHEUS_RULE_INPUTS` unless later evidence demonstrates a clear operator need and a safe bounded design.

Treat the current evidence-first Milestone 4 vertical path as sufficiently complete to begin Milestone 5.

## Exact next step — Milestone 5 first vertical slice

Create a small read-only Backup and Recovery Assurance foundation slice using evidence already available locally before adding any backup-system credential or API integration.

Purpose:

Identify stateful assets that require protection and represent the absence of backup evidence correctly as `UNKNOWN`, never as `UNPROTECTED`.

Smallest intended scope:

1. derive Kubernetes stateful asset candidates from accepted local inventory/evidence only;
2. start with PVCs and their observed workload relationships where available;
3. create an independent backup-assurance artifact; do not modify infrastructure;
4. distinguish asset existence from protection evidence;
5. when no authoritative backup source has been observed, set protection/restore state to `UNKNOWN`, not `UNPROTECTED`;
6. attach provenance/evidence IDs and current/stale semantics from upstream evidence;
7. do not infer that a PVC is backed up from workload type, StorageClass, snapshots, labels, names, or annotations unless authoritative evidence exists;
8. do not add PBS/Proxmox/PostgreSQL/MariaDB credentials or APIs in the same first slice;
9. define explicit future evidence targets for backup mechanism, last success, retention, failure domain, integrity verification, and restore test;
10. keep `mutation_allowed=false` and live-validate before any stronger protection classification.

Suggested assurance vocabulary remains compatible with Project Sources:

```text
PROTECTED
PARTIALLY_PROTECTED
UNPROTECTED
UNKNOWN
BACKUP_STALE
RESTORE_UNVERIFIED
RPO_VIOLATION
RTO_UNKNOWN
```

For the first derived-only slice, expect `UNKNOWN` protection unless an already accepted authoritative source proves otherwise.

This is intentionally a foundation for later authoritative backup-source integration, not a claim that Kubernetes observation can determine backup success.

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
