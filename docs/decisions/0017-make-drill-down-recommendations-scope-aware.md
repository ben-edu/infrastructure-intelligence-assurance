# ADR 0017 — Make Drill-down Recommendations Scope-Aware

Status: Accepted on 2026-08-15 after repository and management-host live validation.

## Context

Incident candidates previously emitted `CHECK_SCOPE_LOGS_IF_NEEDED` for any active candidate with no directly related recent Kubernetes Warning Event. The accepted PR #22 live cycle exposed a poor recommendation:

```text
Platform/k3s-main
alerts: KubeCPUOvercommit, Watchdog
recommended target: LOKI_CANDIDATE
```

Platform scope has no concrete Service or Workload log-bearing subject. A generic log recommendation therefore increases operator search space instead of reducing it.

Routing ownership is available downstream. For an exact Service candidate, the platform can distinguish a Service with complete observed workload routing from selector inference, missing routing, or `NON_POD_ROUTING`.

## Decision

Apply a final derived-only scope-aware recommendation policy after routing ownership integration.

Runtime order:

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
scope_aware_drilldown
```

The post-step reads and rewrites only the local final `incident-candidates.json` artifact. It performs no infrastructure or telemetry query and requires no RBAC change.

### Default log recommendation eligibility

Retain an already-generated `LOKI_CANDIDATE` only when all of the following are true:

1. candidate state is `ACTIVE`;
2. alert-attention source is `COMPLETE`;
3. Kubernetes Event source is `COMPLETE`;
4. scope is either:
   - exact `WORKLOAD`; or
   - exact `SERVICE` whose final routing context is `PREFERRED_ROUTING_EVIDENCE`, route state is `RESOLVED_WORKLOAD_ROUTING`, and at least one concrete workload backend is present.

Do not retain a default log recommendation for `PLATFORM`, `NAMESPACE`, or `NODE` scope.

Do not retain a Service log recommendation when routing is selector fallback, partial, missing, non-Pod, or otherwise not preferred complete workload routing.

The policy does not invent a new log recommendation when the incident builder did not emit one, for example when a directly related Warning Event already exists.

### Platform scope

For an active Platform candidate, preserve the existing evidence requests:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PLATFORM_SIGNAL_INPUTS  -> PROMETHEUS_KUBERNETES
```

Do not recommend Loki by default without a concrete log-bearing subject.

### Other evidence requests

Event, exact recent-change, exact drift, alert refresh, Event refresh, Service ownership, Node placement, and Platform signal verification checks remain unchanged.

## Failure semantics

If alert or Kubernetes Event evidence is incomplete, withhold the default log recommendation rather than advancing to a lower-context evidence source. Existing refresh recommendations remain authoritative.

Withholding a default log recommendation is not evidence that logs are irrelevant. It means the current candidate scope/evidence does not justify making logs the next default drill-down target.

## Artifact contract

The final incident artifact is:

```text
incident_candidates_version: 0.3
drilldown_policy.version: 0.1
drilldown_policy.mode: SCOPE_AWARE
mutation_allowed: false
```

Recommendation target counts are recomputed after refinement.

## Acceptance evidence

Repository/live gate:

```text
RBAC changes: none
query-capable client markers: none
181 passed in 0.99s
scope_aware_drilldown: status=0/SUCCESS
incident_candidates_version: 0.3
drilldown_policy.mode: SCOPE_AWARE
scope_aware_log_recommendations_retained: 0
scope_aware_log_recommendations_removed: 1
platform_active_candidates_without_default_log_recommendation: 1
Platform candidates with Loki: none
Service Loki recommendations without preferred routing: none
forbidden projected keys: none
raw URL markers: false
```

The active live Platform candidate retained only `PROMETHEUS_ALERTMANAGER` and `PROMETHEUS_KUBERNETES` verification targets. Event verification remained attached to the Moodle Namespace candidate.

No eligible Workload- or preferred-routing Service-scoped active candidate existed in this live cycle; positive Loki-retention behavior is therefore validated by repository regressions rather than claimed as exercised live.

## Consequences

The operator receives a smaller, more defensible next-evidence set. Platform-level alerts stay focused on Prometheus rule inputs and cluster state; concrete Workload or routing-backed Service candidates may still recommend logs when structured evidence is complete.

This decision does not add Loki ingestion, OpenTelemetry, remediation, root-cause claims, or business-impact claims.
