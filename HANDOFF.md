# Project Handoff

This is the compact continuation checkpoint for the Infrastructure Intelligence & Assurance Platform. Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read the Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable checkpoint

- repository: `ben-edu/infrastructure-intelligence-assurance`
- stable branch: `main`
- current main checkpoint before PR #22 merge: `236751b9218ddfd93047ed1a4fb488727659bb49`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- cluster: `k3s-main`
- runtime user: `infra-assurance`
- oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

Milestones 0–3 are live validated for the evidence contract, Kubernetes observation/context/topology/preflight, history/diff, Git declared-state/drift, workload inventory, and Prometheus Operator coverage.

Milestone 4 accepted/live-validated slices:

- PR #10 — Prometheus runtime;
- PR #13 — Alertmanager handling correlation;
- PR #14 — Kubernetes Event correlation;
- PR #16 — incident candidates/drill-down;
- PR #18 — bounded EndpointSlice/Pod/ReplicaSet routing ownership;
- PR #20 — alert resource scope identity validation;
- PR #22 — routing ownership integration into inventory/incident context; accepted and ready to merge.

Known real drift remains intentionally unresolved:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Accepted routing/scope baseline

PR #18 routing ownership merged at:

```text
c26688e4f6cfe9d93fd0c91935a4034342b17fc5
```

Accepted routing source:

```text
COMPLETE
EndpointSlices: 79
Pod exact GETs: 60 / 60 present
ReplicaSet exact GETs: 37 / 37 present
resolved workload paths: 75
services with resolved workloads: 63
mutation_allowed: false
```

`Service/monitoring/loki-headless` routes to both `StatefulSet/monitoring/loki` and `DaemonSet/monitoring/loki-canary`.

`Service/kube-system/kube-prom-stack-kubelet` is `NON_POD_ROUTING` with Node targetRefs.

PR #20 alert scope validation merged at:

```text
62c75f863c053be5e353c15f62523c27a52be9d3
```

Accepted final scope facts:

```text
alert_attention_version: 0.2
Prometheus: COMPLETE
Alertmanager: COMPLETE
Kubernetes scope: COMPLETE
Alertmanager alerts: 11
Alert attention: 11
Event correlations: 11
NAMESPACE scopes: 9
PLATFORM scopes: 2
SERVICE scopes: 0
UNVERIFIED_SIGNAL_DIMENSION: 6
pseudo Service scopes: none
automatic kube-system rewrite: none
label mismatches: none
forbidden projected keys: none
raw URL markers: false
```

## PR #22 accepted routing context integration

- PR: `#22 Milestone 4 integrate routing ownership context`
- branch: `feature/m4-routing-ownership-integration`
- package version: `0.15.0`
- status: repository and live accepted; ready for squash merge
- base main: `236751b9218ddfd93047ed1a4fb488727659bb49`
- no RBAC change
- no new Kubernetes/Prometheus/Alertmanager/Loki query

Design:

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
```

The integration post-step reads only local artifacts:

```text
inventory.json
kubernetes-routing-ownership.json
incident-candidates.json
```

Selector inference remains separately visible under `relationships.services`. Complete exact routing is added under `relationships.routing_services` only when routing source overall is `COMPLETE`, route state is `RESOLVED_WORKLOAD_ROUTING`, and route scope is `COMPLETE`.

For exact Service incident candidates, complete routing is preferred over selector inference and all real backend controllers are retained. `NON_POD_ROUTING`, `NO_ENDPOINTS_OBSERVED`, partial/unknown states do not create workload ownership. Missing exact routing can retain selector inference as weaker fallback. Non-Service scopes are never promoted through Service routing.

Repository/live acceptance:

```text
RBAC changes: none
query-capable client markers: none
169 passed in 1.11s
inventory_version: 0.4
incident_candidates_version: 0.2
routing source: COMPLETE
inventory routing source: COMPLETE
incident routing source: COMPLETE
selector inference links: 77
routing ownership links: 64
workloads with routing relation: 51
routing_service_links: 64
routing_services_resolved: 63
routing_services_non_pod: 1
routing_services_unknown_or_partial: 1
routing_workloads_not_in_inventory: 0
non-complete promoted routing relations: none
mutation_allowed: false
forbidden projected keys: none
raw URL markers: false
```

Accepted route-state distribution:

```text
RESOLVED_WORKLOAD_ROUTING: 63
NO_ENDPOINTS_OBSERVED: 13
NON_POD_ROUTING: 1
UNKNOWN: 1
```

`Service/monitoring/loki-headless` remains complete observed routing to both:

```text
StatefulSet/monitoring/loki
DaemonSet/monitoring/loki-canary
```

`Service/kube-system/kube-prom-stack-kubelet` remains `NON_POD_ROUTING` with no workload routing relation.

Current live alert/incident scopes at acceptance were unchanged by integration:

```text
SUPPRESSED Namespace/keycloak    alerts=2 related_workloads=2
SUPPRESSED Namespace/monitoring  alerts=5 related_workloads=9
SUPPRESSED Namespace/moodle      alerts=2 related_workloads=2
ACTIVE     Platform/k3s-main     alerts=2 related_workloads=0
```

No Service-scoped incident existed in this live cycle. Service-candidate routing replacement is therefore acceptance-covered by repository regression tests; do not claim it was exercised by the current live alert set.

Relevant docs:

```text
docs/decisions/0016-prefer-observed-routing-over-selector-inference.md
docs/milestone-4-routing-ownership-integration.md
docs/reports/2026-08-15-m4-routing-ownership-integration-live-test-gate.md
```

## Exact next step

1. Squash PR #22 to one commit and merge it.
2. Update `main` Handoff with the actual merge commit.
3. Create a separate Milestone 4 scope-aware drill-down recommendation slice.
4. Drive that slice from the accepted live evidence: current active `Platform/k3s-main` contains `KubeCPUOvercommit` and `Watchdog` yet receives generic `LOKI_CANDIDATE` because there is no related Warning Event.
5. For Platform scope, prefer Prometheus rule/input and current cluster-state verification; do not recommend logs by default without a concrete Service/Workload log-bearing subject.
6. Preserve existing recommendations where evidence/scope supports them; do not suppress operator options globally.
7. Derived-only: no new telemetry source, infrastructure query, or RBAC in that slice.
8. Do not add Loki/OpenTelemetry ingestion yet.

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
