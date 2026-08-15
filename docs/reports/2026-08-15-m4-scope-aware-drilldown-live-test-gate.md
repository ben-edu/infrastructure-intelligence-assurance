# Milestone 4 Scope-Aware Drill-down Live Test Gate — 2026-08-15

## Status

Accepted.

Repository and management-host live acceptance passed on 2026-08-15.

## Purpose

Validate that final incident recommendation targets are scope-aware and reduce unsupported default log drill-down without changing evidence collection, scope identity, candidate grouping, or impact context.

## Accepted repository evidence

```text
RBAC changes: none
query-capable client markers: none
181 passed in 0.99s
package version: 0.16.0
```

Regression coverage confirms:

- Platform active/no-Event drops `LOKI_CANDIDATE` and keeps Prometheus evidence requests;
- direct Workload scope may retain/refine the log recommendation;
- Service scope retains logs only with preferred complete workload routing;
- `NON_POD_ROUTING` Service does not get a log recommendation;
- Namespace/Node scopes do not get default log recommendations;
- incomplete alert/Event evidence withholds logs;
- Event/change/drift checks are preserved;
- the policy never invents a log check that was not already emitted.

## Accepted runtime order

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
scope_aware_drilldown
```

Every stage exited `0/SUCCESS`. The oneshot returned to `inactive (dead)` after successful completion, as expected.

## Accepted final artifact

```text
incident_candidates_version: 0.3
mutation_allowed: false
drilldown_policy:
  version: 0.1
  mode: SCOPE_AWARE
  requires_complete_alert_and_event_evidence: true
```

Source status at acceptance:

```text
alert_attention: COMPLETE
kubernetes_events: COMPLETE
routing_ownership: COMPLETE
inventory: COMPLETE
change_context: COMPLETE
drift: EVALUATED
```

Policy counters:

```text
scope_aware_log_recommendations_retained: 0
scope_aware_log_recommendations_removed: 1
platform_active_candidates_without_default_log_recommendation: 1
```

## Accepted live candidates

```text
SUPPRESSED Namespace/keycloak    alerts=2 names=CPUThrottlingHigh,InfoInhibitor related_workloads=2
SUPPRESSED Namespace/monitoring  alerts=5 names=CPUThrottlingHigh,InfoInhibitor related_workloads=9
SUPPRESSED Namespace/moodle      alerts=2 names=CPUThrottlingHigh,InfoInhibitor related_workloads=2 related_warning_events=1
ACTIVE     Platform/k3s-main     alerts=2 names=KubeCPUOvercommit,Watchdog related_workloads=0
```

The Moodle Namespace candidate preserved:

```text
VERIFY_RELATED_EVENT_OBJECT_STATE -> KUBERNETES_OBJECT
```

The active Platform candidate preserved:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PLATFORM_SIGNAL_INPUTS  -> PROMETHEUS_KUBERNETES
```

and no longer contains a default `LOKI_CANDIDATE`.

## Accepted target summary

```text
KUBERNETES_OBJECT: 1
PROMETHEUS_ALERTMANAGER: 1
PROMETHEUS_KUBERNETES: 1
```

The recomputed target summary exactly matched candidate checks.

## Scope guards

```text
Platform candidates with Loki: none
Service Loki recommendations without preferred routing: none
retained log recommendations in current live cycle: none
```

No Workload- or preferred-routing Service-scoped active candidate existed in this live cycle, so positive retention of a valid Loki recommendation is covered by repository regression tests rather than claimed as exercised by this live alert set.

## Data minimization

```text
forbidden projected keys: none
raw URL markers: false
```

No raw logs were queried, collected, or persisted. No new infrastructure/telemetry query or RBAC permission was introduced.

## Interpretation

Withholding a default Loki recommendation is not a claim that logs have no value. It means the current scope and evidence do not justify logs as the default next operator drill-down.

The current active Platform candidate now points only to Prometheus/Alertmanager and cluster-state verification. This makes Prometheus rule/input context the smallest evidence-driven follow-up rather than adding Loki without a concrete log-bearing subject.
