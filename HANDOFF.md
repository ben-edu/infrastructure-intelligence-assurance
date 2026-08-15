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
- current main HEAD before PR #24 merge: `0499362ab4703847aca69b7d3692ae42c0c18e47`
- accepted PR #22 code merge: `bd496c3a88c63f2ded7180d0dcb459009a778bcd`
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
- PR #24 — scope-aware drill-down recommendations; accepted and ready to merge.

Known real drift remains intentionally unresolved:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Accepted M4 baseline

PR #20 final alert-scope semantics:

```text
alert_attention_version: 0.2
Prometheus: COMPLETE
Alertmanager: COMPLETE
Kubernetes scope: COMPLETE
pseudo Service scopes: none
automatic kube-system rewrite: none
mutation_allowed: false
```

PR #22 accepted routing integration:

```text
inventory_version: 0.4
incident_candidates_version: 0.2
routing source: COMPLETE
selector inference links: 77
routing ownership links: 64
workloads with routing relation: 51
resolved Service routes: 63
NON_POD_ROUTING Services: 1
routing workloads not in inventory: 0
non-complete promoted routing relations: none
mutation_allowed: false
```

`Service/monitoring/loki-headless` has complete observed routing to both `StatefulSet/monitoring/loki` and `DaemonSet/monitoring/loki-canary`.

`Service/kube-system/kube-prom-stack-kubelet` remains `NON_POD_ROUTING` with no workload routing relation.

## PR #24 accepted scope-aware drill-down

- PR: `#24 Milestone 4 scope-aware drill-down recommendations`
- branch: `feature/m4-scope-aware-drilldown`
- base main: `0499362ab4703847aca69b7d3692ae42c0c18e47`
- package version: `0.16.0`
- status: repository and live accepted; ready for squash merge
- no RBAC change
- no new infrastructure/telemetry query
- no Loki/OpenTelemetry ingestion

Runtime order:

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
scope_aware_drilldown
```

Final contract:

```text
incident_candidates_version: 0.3
drilldown_policy.version: 0.1
drilldown_policy.mode: SCOPE_AWARE
mutation_allowed: false
```

Accepted repository/live evidence:

```text
RBAC changes: none
query-capable client markers: none
181 passed in 0.99s
all runtime stages: status=0/SUCCESS
alert_attention: COMPLETE
kubernetes_events: COMPLETE
routing_ownership: COMPLETE
scope_aware_log_recommendations_retained: 0
scope_aware_log_recommendations_removed: 1
platform_active_candidates_without_default_log_recommendation: 1
Platform candidates with Loki: none
Service Loki recommendations without preferred routing: none
forbidden projected keys: none
raw URL markers: false
```

Accepted live candidate set:

```text
SUPPRESSED Namespace/keycloak    alerts=2 related_workloads=2
SUPPRESSED Namespace/monitoring  alerts=5 related_workloads=9
SUPPRESSED Namespace/moodle      alerts=2 related_workloads=2 related_warning_events=1
ACTIVE     Platform/k3s-main     alerts=2 names=KubeCPUOvercommit,Watchdog related_workloads=0
```

The Platform candidate now retains only:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PLATFORM_SIGNAL_INPUTS  -> PROMETHEUS_KUBERNETES
```

The Moodle candidate preserves `VERIFY_RELATED_EVENT_OBJECT_STATE -> KUBERNETES_OBJECT`.

Current accepted target summary:

```text
KUBERNETES_OBJECT: 1
PROMETHEUS_ALERTMANAGER: 1
PROMETHEUS_KUBERNETES: 1
```

No eligible active Workload or preferred-routing Service candidate existed in this live cycle, so valid positive Loki-retention behavior remains regression-tested rather than claimed as live-exercised.

Relevant docs:

```text
docs/decisions/0017-make-drill-down-recommendations-scope-aware.md
docs/milestone-4-scope-aware-drilldown.md
docs/reports/2026-08-15-m4-scope-aware-drilldown-live-test-gate.md
```

## Exact next step after PR #24 merge

Create a small Milestone 4 Prometheus rule/input context slice driven by the current active Platform candidate.

Why this is next:

- `Platform/k3s-main` currently needs `PROMETHEUS_ALERTMANAGER` and `PROMETHEUS_KUBERNETES` verification;
- Loki is no longer a justified default evidence source for that scope;
- the existing Prometheus observer already uses the read-only Kubernetes Service proxy and currently reads `/api/v1/targets` and `/api/v1/alerts`;
- Prometheus rule context can make `VERIFY_PLATFORM_SIGNAL_INPUTS` concrete without adding a new specialized engine.

Smallest intended scope:

1. reuse the existing `monitoring/kube-prom-stack-prometheus:9090` Service-proxy access; no RBAC expansion unless live verification disproves this assumption;
2. read bounded Prometheus rule metadata, preferably `/api/v1/rules`, through the same source boundary;
3. correlate current active alert names to exact Prometheus rule records; do not join by fuzzy name;
4. project only safe rule metadata needed for investigation: alert/rule name, group identity, rule type/state/health where available, bounded PromQL expression only after explicit sensitive-label/value review, duration/keep-firing metadata where available, and evidence provenance;
5. do not persist annotations, dashboards/runbook URLs, arbitrary labels, raw API payloads, credentials, tokens, or connection strings;
6. distinguish rule observation from evaluation input values: a rule expression is declared/evaluated logic, not proof of the current metric values that triggered it;
7. if current rule inputs require live metric verification, emit that as a separate required evidence target rather than claiming cause;
8. integrate rule context first into Platform incident drill-down; do not add Loki/OpenTelemetry in the same slice;
9. keep `mutation_allowed=false` and live-validate before using rule context in stronger hypothesis/cause language.

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
