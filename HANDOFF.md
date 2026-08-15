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
- current main HEAD after post-PR24 continuity merge: `401e400371e9e223a8e210051d9b96f86592c312`
- accepted PR #24 code merge: `a3a2217095fb0f76fcae987c3c07b744f13e082e`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- cluster: `k3s-main`
- runtime user: `infra-assurance`
- oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

Milestones 0–3 are live validated for evidence contract, Kubernetes observation/context/topology/preflight, history/diff, Git declared-state/drift, workload inventory, and Prometheus Operator coverage.

Milestone 4 accepted/live-validated slices:

- PR #10 — Prometheus runtime;
- PR #13 — Alertmanager handling correlation;
- PR #14 — Kubernetes Event correlation;
- PR #16 — incident candidates/drill-down;
- PR #18 — bounded EndpointSlice/Pod/ReplicaSet routing ownership;
- PR #20 — alert resource scope identity validation;
- PR #22 — routing ownership integration into inventory/incident context;
- PR #24 — scope-aware drill-down recommendations.

Known real drift remains intentionally unresolved:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Accepted M4 baseline relevant to current work

Final incident contract after PR #24:

```text
incident_candidates_version: 0.3
drilldown_policy.version: 0.1
drilldown_policy.mode: SCOPE_AWARE
mutation_allowed: false
```

Accepted current live candidate set:

```text
SUPPRESSED Namespace/keycloak    alerts=2 related_workloads=2
SUPPRESSED Namespace/monitoring  alerts=5 related_workloads=9
SUPPRESSED Namespace/moodle      alerts=2 related_workloads=2 related_warning_events=1
ACTIVE     Platform/k3s-main     alerts=2 names=KubeCPUOvercommit,Watchdog related_workloads=0
```

The active Platform candidate now retains only:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PLATFORM_SIGNAL_INPUTS  -> PROMETHEUS_KUBERNETES
```

Default Loki recommendation is absent for Platform scope.

## Active work — PR #26 bounded Prometheus rule context

- PR: `#26 Milestone 4 bounded Prometheus rule context`
- branch: `feature/m4-prometheus-rule-context`
- base main: `401e400371e9e223a8e210051d9b96f86592c312`
- package version: `0.17.0`
- status: Draft; pending repository and management-host live acceptance
- intended RBAC change: none
- source: existing `monitoring/kube-prom-stack-prometheus:9090` Kubernetes Service proxy
- no Loki/OpenTelemetry
- no incident-candidate mutation/integration in this slice

Runtime order becomes:

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
scope_aware_drilldown
prometheus_rule_context
```

Final new artifacts:

```text
/var/lib/infra-assurance/evidence/prometheus-rule-context.json
/var/lib/infra-assurance/evidence/prometheus-rule-context.md
```

Contract:

```text
prometheus_rule_context_version: 0.1
mutation_allowed: false
source.operation: GET_RULES_BY_EXACT_ACTIVE_ALERTNAME
max_active_alert_names: 20
```

### Query minimization

Only distinct safe alert names from ACTIVE incident candidates are requested. Suppressed candidates are excluded.

The Rules API request uses:

```text
type=alert
exclude_alerts=true
rule_name[]=<exact current active alert name>
```

No fuzzy matching is used. If more than 20 active alert names exist, request scope is truncated deterministically and source status becomes `PARTIAL`.

If there are no ACTIVE alert names, the slice performs no Rules API request for that cycle.

### Safe projection

Persist only compact rule identity/state metadata and provenance:

- alertname;
- sanitized group name;
- ALERTING type;
- normalized state/health;
- duration / keep-firing / evaluation-time numeric metadata where available;
- last-evaluation timestamp where present;
- observation/evidence/provenance fields.

Every persisted rule records:

```text
expression_persisted: false
```

Do not persist PromQL expression/query, labels, annotations, file paths, embedded active alerts, last-error text, dashboards/runbook URLs, raw API payloads, credentials, tokens, or connection strings.

### Correlation and interpretation

ACTIVE candidate alert names join to rule records by exact alert name only.

An exact rule match means Prometheus returned rule metadata for that current alert name. It is not proof of the current metric values or root cause.

Matched rule context therefore emits separate required live verification:

```text
PROMETHEUS_RULE_INPUTS
```

The new artifact remains independent in PR #26. Do not attach it to `incident-candidates.json` until this source passes live acceptance.

### Failure semantics

- Rules API request succeeds without truncation: `COMPLETE`;
- alert-name bound truncation: `PARTIAL`;
- Service-proxy/Rules API failure: `FAILED_TO_OBSERVE`;
- unmatched names remain explicit; no fuzzy substitution;
- observation failure is not absence.

Relevant files:

```text
src/infra_assurance/prometheus_rule_context.py
schemas/prometheus-rule-context.schema.json
docs/decisions/0018-collect-bounded-prometheus-rule-context.md
docs/milestone-4-prometheus-rule-context.md
docs/reports/2026-08-15-m4-prometheus-rule-context-live-test-gate.md
```

## Exact next step

Run PR #26 repository/live gate on `mgmt-automation`:

1. verify no RBAC diff vs `origin/main`;
2. run full pytest;
3. if green, bootstrap observer;
4. confirm `prometheus_rule_context` is the final post-step and exits `0/SUCCESS`;
5. validate rule-context schema/trust fields;
6. verify request scope equals current ACTIVE incident alert names only and remains bounded;
7. if `KubeCPUOvercommit` / `Watchdog` remain active, inspect their exact rule matches;
8. verify PromQL/free-form/sensitive fields and raw URLs are absent;
9. verify every rule says `expression_persisted=false`;
10. verify matched candidates require separate `PROMETHEUS_RULE_INPUTS` live verification;
11. confirm incident artifact remains v0.3 and unmodified by rule-context collection.

Do not merge PR #26 before live acceptance.

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
