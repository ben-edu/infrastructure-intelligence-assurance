# Milestone 4 Routing Ownership Integration Live Test Gate — 2026-08-15

## Status

Accepted. Repository and management-host live acceptance passed on 2026-08-15.

## Purpose

Validate that accepted EndpointSlice/Pod/controller routing ownership improves downstream context only through exact complete evidence-backed joins while preserving selector inference as a visibly weaker relation.

## Accepted repository evidence

The management-host gate reported:

```text
RBAC changes: none
query-capable client markers: none
169 passed in 1.11s
```

Package version is `0.15.0`.

Regression coverage confirms:

- selector inference remains separate from routing evidence;
- `loki-headless` multi-controller routing retains both controllers;
- exact complete Service routing is preferred for a Service incident candidate in unit coverage;
- observed `NON_POD_ROUTING` suppresses selector-based workload ownership;
- Namespace candidates are not promoted by similarly named Service routing;
- missing exact routing data can retain selector inference as a weaker fallback;
- globally partial routing does not upgrade an otherwise resolved-looking route;
- raw routing paths and sensitive/full-object fields are excluded.

No RBAC change and no query-capable client were introduced by the integration module.

## Accepted runtime evidence

`bootstrap-observer.sh` completed successfully. The systemd oneshot returned to `inactive (dead)` after all stages exited `0/SUCCESS`, which is expected for this oneshot.

Observed order:

```text
kubernetes_runtime          status=0/SUCCESS
routing_ownership           status=0/SUCCESS
alert_scope_runtime         status=0/SUCCESS
incident_runtime            status=0/SUCCESS
routing_context_integration status=0/SUCCESS
```

Git declared-state observation also remained `COMPLETE` with 27 normalized records at revision:

```text
5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
```

## Accepted trust and version facts

```text
inventory_version: 0.4
incident_candidates_version: 0.2
alert_attention_version: 0.2
routing source: COMPLETE
inventory routing source: COMPLETE
incident routing source: COMPLETE
inventory mutation_allowed: false
incident mutation_allowed: false
alert attention mutation_allowed: false
```

## Accepted inventory routing facts

```text
routing_service_links: 64
workloads_with_routing_service: 51
routing_services_resolved: 63
routing_services_non_pod: 1
routing_services_unknown_or_partial: 1
routing_workloads_not_in_inventory: 0
```

Route-state distribution:

```text
RESOLVED_WORKLOAD_ROUTING: 63
NO_ENDPOINTS_OBSERVED: 13
NON_POD_ROUTING: 1
UNKNOWN: 1
```

Selector and routing evidence remain separately visible:

```text
selector inference links: 77
routing ownership links: 64
workloads with routing relation: 51
```

No non-complete routing relation was promoted into `relationships.routing_services`.

## Accepted Loki headless evidence

Exact Service:

```text
Service/monitoring/loki-headless
```

remained:

```text
state: RESOLVED_WORKLOAD_ROUTING
scope_completeness: COMPLETE
```

with both real backend controllers retained:

```text
StatefulSet/monitoring/loki
DaemonSet/monitoring/loki-canary
```

Both workloads also retain the original selector-inference relation separately. No heuristic single-controller choice is made.

## Accepted kubelet non-Pod guard

Exact Service:

```text
Service/kube-system/kube-prom-stack-kubelet
```

remained:

```text
state: NON_POD_ROUTING
resolved workloads: none
workload routing relations: none
```

This is positive routing evidence against inventing a Pod/workload ownership path for this Service.

## Accepted incident-scope regression

Current alert-attention scopes and final incident scopes matched exactly:

```text
Namespace/keycloak
Namespace/monitoring
Namespace/moodle
Platform/k3s-main
```

No Service candidate existed in this live cycle, so Service-candidate routing replacement is acceptance-covered by repository regression tests rather than claimed as exercised by current live alerts.

No non-Service candidate received a `service_routing` projection.

Current incident state at acceptance:

```text
alert attention records: 11
incident candidates: 4
active candidates: 1
suppressed candidates: 3
unknown candidates: 0
candidates with related Warning Events: 1
candidates with related workload context: 3
```

Current candidates:

```text
SUPPRESSED Namespace/keycloak    alerts=2 related_workloads=2
SUPPRESSED Namespace/monitoring  alerts=5 related_workloads=9
SUPPRESSED Namespace/moodle      alerts=2 related_workloads=2
ACTIVE     Platform/k3s-main     alerts=2 related_workloads=0
```

The Namespace workload counts remain breadth context only; they are not impact claims.

## Data-minimization acceptance

The final sanitized routing projection reported:

```text
forbidden projected keys: none
raw URL markers: false
```

Raw EndpointSlice paths, addresses, Pod IPs, Pod specs, labels, annotations, environment data, Secret references, credentials, and similar sensitive/full-object content are not projected into the integrated inventory/incident context.

## Interpretation

A routing relation means current Service backend routing and controller ownership were observed through the accepted bounded evidence path. It does not prove application health, alert causality, root cause, or business impact.

A multi-controller Service can legitimately have multiple routing relations.

A `NON_POD_ROUTING` Service is positive evidence against inventing Pod/workload routing from selector similarity.

If the routing source is partial/failed, missing routes remain uncertain and selector inference is not upgraded to routing ownership.

## Follow-up evidence from this gate

The current active Platform candidate (`Platform/k3s-main`, alerts `KubeCPUOvercommit` and `Watchdog`) still receives a generic `LOKI_CANDIDATE` recommendation because it is active and has no directly related Warning Event. That recommendation is not wrong as an optional fallback, but it is insufficiently scope-aware: a Platform scope has no concrete Service/Workload log subject.

A separate next slice should refine drill-down recommendations so Platform-scoped alerts prefer Prometheus rule/input and cluster-state verification and do not recommend logs by default without a concrete log-bearing subject. This follow-up requires no new telemetry or RBAC.
