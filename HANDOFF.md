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
- current main HEAD before PR #26 merge: `401e400371e9e223a8e210051d9b96f86592c312`
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
- PR #24 — scope-aware drill-down recommendations;
- PR #26 — bounded Prometheus rule context; repository/live accepted and ready to merge.

Known real drift remains intentionally unresolved:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Accepted incident baseline

```text
incident_candidates_version: 0.3
drilldown_policy.version: 0.1
drilldown_policy.mode: SCOPE_AWARE
mutation_allowed: false
```

Current accepted live candidate set:

```text
SUPPRESSED Namespace/keycloak    alerts=2 related_workloads=2
SUPPRESSED Namespace/monitoring  alerts=5 related_workloads=9
SUPPRESSED Namespace/moodle      alerts=2 related_workloads=2 related_warning_events=1
ACTIVE     Platform/k3s-main     alerts=2 names=KubeCPUOvercommit,Watchdog related_workloads=0
```

The active Platform candidate currently retains:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PLATFORM_SIGNAL_INPUTS  -> PROMETHEUS_KUBERNETES
```

Default Loki recommendation is absent for Platform scope.

## PR #26 accepted bounded Prometheus rule context

- PR: `#26 Milestone 4 bounded Prometheus rule context`
- branch: `feature/m4-prometheus-rule-context`
- base main: `401e400371e9e223a8e210051d9b96f86592c312`
- package version: `0.17.0`
- status: repository/live accepted; ready for squash merge
- RBAC change: none
- source: existing `monitoring/kube-prom-stack-prometheus:9090` Kubernetes Service proxy
- no Loki/OpenTelemetry
- no incident-candidate mutation/integration in this slice

Runtime order:

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
scope_aware_drilldown
prometheus_rule_context
```

New artifacts:

```text
/var/lib/infra-assurance/evidence/prometheus-rule-context.json
/var/lib/infra-assurance/evidence/prometheus-rule-context.md
```

Accepted contract:

```text
prometheus_rule_context_version: 0.1
mutation_allowed: false
source.operation: GET_RULES_BY_EXACT_ACTIVE_ALERTNAME
source.status: COMPLETE
max_active_alert_names: 20
```

Query minimization remains:

```text
type=alert
exclude_alerts=true
rule_name[]=<exact current ACTIVE alert name>
```

Only distinct safe alert names from ACTIVE incident candidates are requested. Suppressed candidates are excluded. No fuzzy matching is used. More than 20 active names produces explicit `PARTIAL`. No active names means no Rules API request.

Safe projection excludes PromQL expression/query, labels, annotations, file paths, embedded alerts, last-error text, dashboards/runbook URLs, raw API payloads, credentials, tokens, and connection strings. Every rule records `expression_persisted=false`.

### Accepted live evidence

```text
RBAC changes: none
192 passed in 1.07s
all runtime stages: status=0/SUCCESS
active alert names total/requested: 2/2
active alert names truncated: false
requested: KubeCPUOvercommit, Watchdog
matched: KubeCPUOvercommit, Watchdog
unmatched: none
rule records: 2
rule health OK: 2
rules FIRING: 2
unknowns: none
errors: none
forbidden projected keys: none
raw URL markers: false
incident artifact remained v0.3 / SCOPE_AWARE
```

Accepted exact rule metadata:

```text
KubeCPUOvercommit | group=kubernetes-resources | state=FIRING | health=OK | duration=600s | keep_firing=0s
Watchdog          | group=general.rules        | state=FIRING | health=OK | duration=0s   | keep_firing=0s
```

Both rule names exactly matched the active `Platform/k3s-main` candidate. The rule artifact therefore emits separate required live verification:

```text
PROMETHEUS_RULE_INPUTS
```

Interpretation: exact rule metadata and rule health/state are observed facts from Prometheus. Current metric values inside the rule expression are still unobserved. Rule metadata does not establish root cause, business impact, or remediation.

Relevant docs:

```text
docs/decisions/0018-collect-bounded-prometheus-rule-context.md
docs/milestone-4-prometheus-rule-context.md
docs/reports/2026-08-15-m4-prometheus-rule-context-live-test-gate.md
```

## Exact next step after PR #26 merge

Create a small derived-only Milestone 4 rule-context integration slice.

Purpose: make the accepted Prometheus rule evidence directly useful in incident drill-down without adding any new infrastructure query.

Smallest intended scope:

1. read only local `incident-candidates.json` and accepted `prometheus-rule-context.json` after rule-context collection;
2. require rule source `COMPLETE` before promoting exact rule metadata into incident context;
3. correlate by existing `candidate_id` plus exact alert-name evidence only; no fuzzy matching;
4. attach bounded safe rule context to ACTIVE candidates: alertname, group name, normalized state/health, duration/keep-firing/evaluation metadata, and evidence IDs only;
5. never attach PromQL expression, labels, annotations, raw payloads, URLs, credentials, or other excluded fields;
6. for complete exact rule matches, refine the generic Platform next-evidence request toward `PROMETHEUS_RULE_INPUTS` while preserving `VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER`;
7. retain the generic `PROMETHEUS_KUBERNETES` verification when rule context is missing, partial, failed, or unmatched; unknown must remain explicit;
8. do not query rule input metric values in the integration slice;
9. do not add Loki/OpenTelemetry;
10. no RBAC change, no mutation, and live acceptance before rule context influences stronger hypothesis/cause language.

The integration is derived evidence only. It must reduce operator search space, not claim that a firing/healthy rule proves the underlying cause.

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
