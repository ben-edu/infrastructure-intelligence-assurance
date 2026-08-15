# ADR 0016 — Prefer Complete Observed Routing Over Selector Inference

Status: Accepted; repository and live validated on 2026-08-15.

## Context

The platform originally related Services to controllers using selector matching. That relation is useful but remains an inference: matching a Service selector to a workload pod template does not prove that current Service backends route to Pods owned by that workload.

PR #18 introduced bounded read-only routing ownership evidence from:

```text
Service
  <- kubernetes.io/service-name
EndpointSlice
  -> targetRef
Pod
  -> controller ownerReference
ReplicaSet
  -> controller ownerReference
Deployment / StatefulSet / DaemonSet
```

The live gate proved both important directions:

- `Service/monitoring/loki-headless` currently routes to two real controller subjects, `StatefulSet/monitoring/loki` and `DaemonSet/monitoring/loki-canary`;
- `Service/kube-system/kube-prom-stack-kubelet` is `NON_POD_ROUTING` and targets Nodes, so selector-like or similarly named workload inference must not create workload ownership.

PR #20 separately corrected alert scope identity so signal labels cannot invent Service subjects.

## Decision

Routing ownership remains a separate evidence plane and is integrated downstream only through exact subject joins.

### Inventory

The existing selector relation remains visible as:

```text
relationships.services
basis = SERVICE_SELECTOR_MATCH_INFERENCE
```

A separate relation is added only for complete accepted routing:

```text
relationships.routing_services
state = RESOLVED_WORKLOAD_ROUTING
scope_completeness = COMPLETE
```

The selector relation is not deleted. Keeping both makes evidence strength visible to the operator.

### Incident impact context

For an exact validated `SERVICE` candidate:

1. if routing source status is `COMPLETE`, the exact Service route is `RESOLVED_WORKLOAD_ROUTING`, and route scope is `COMPLETE`, routing ownership is preferred over selector inference;
2. every observed backend controller is retained; multiple controllers are not reduced to one heuristic winner;
3. `NON_POD_ROUTING`, `NO_ENDPOINTS_OBSERVED`, `PARTIAL_ROUTING`, `SERVICE_NOT_OBSERVED`, and `UNKNOWN` do not support a workload ownership claim;
4. if no exact Service routing record exists, existing selector inference may remain as a weaker fallback;
5. if the routing source itself is partial/failed, no strong routing upgrade is made.

Namespace, Platform, Node, or Workload candidates are not promoted through similarly named Service routing. In particular, PR #20 Namespace fallbacks for kubelet-labelled alerts remain Namespace scoped.

## Runtime ordering

The final local derived stage is:

```text
kubernetes_runtime
  -> routing_ownership
  -> alert_scope_runtime
  -> incident_runtime
  -> routing_context_integration
```

The integration step reads only local artifacts:

```text
inventory.json
kubernetes-routing-ownership.json
incident-candidates.json
```

It performs no Kubernetes, Prometheus, Alertmanager, Loki, or other network query and requires no RBAC change.

## Failure semantics

- `routing_ownership.source_status.overall=COMPLETE` is required before routing relations are promoted into workload inventory.
- An incomplete routing source does not become evidence of absence.
- A complete exact `NON_POD_ROUTING` route is positive evidence that the Service routing observed by this slice is not Pod-backed; it must not be replaced with selector-based workload ownership.
- Missing exact routing data is distinct from non-Pod routing: missing data can retain weaker selector inference, while observed non-Pod routing suppresses a workload ownership claim.

## Data minimization

The downstream projection does not copy raw EndpointSlice paths, backend addresses, Pod IPs, host IPs, Pod specs, labels, annotations, environment variables, Secret references, logs, or credentials.

It persists only compact Service state, resolved workload subject, pod-target count, evidence basis, and evidence IDs.

## Live validation

PR #22 management-host acceptance established:

```text
169 passed in 1.11s
RBAC changes: none
query-capable client markers: none
routing source: COMPLETE
inventory_version: 0.4
incident_candidates_version: 0.2
selector inference links: 77
routing ownership links: 64
workloads with routing relation: 51
non-complete promoted routing relations: none
routing workloads not in inventory: 0
```

`Service/monitoring/loki-headless` retained both observed controllers under complete routing evidence. `Service/kube-system/kube-prom-stack-kubelet` remained `NON_POD_ROUTING` with no workload routing relation.

Current live incident scopes were Namespace/Platform only; those scopes were preserved exactly and no non-Service candidate received Service routing context. Service-candidate replacement semantics are covered by repository regression tests rather than falsely claimed as exercised by that live alert set.

Sensitive/free-form projection guards passed with no forbidden projected keys and no raw URL markers. `mutation_allowed=false` remained unchanged.

## Consequences

The platform gains a visible evidence-strength upgrade without hiding the original inference or claiming application health/business impact.

This integration does not establish root cause, does not mean every routed workload is affected by a Service-scoped alert, and does not introduce Loki/OpenTelemetry.
