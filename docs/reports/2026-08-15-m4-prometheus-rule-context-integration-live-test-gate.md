# Milestone 4 Prometheus Rule Context Integration Live Test Gate — 2026-08-15

## Status

Accepted — repository and management-host live acceptance passed. Ready for squash merge.

## Purpose

Validate that accepted local Prometheus rule context can enrich ACTIVE incident drill-down and refine the generic Platform evidence target without any new infrastructure query, RBAC expansion, sensitive-field exposure, or causal overstatement.

## Accepted repository evidence

```text
RBAC changes: none
query-capable markers: none
204 passed in 1.29s
package version: 0.18.0
```

The integration module remains derived-only and contains no infrastructure/telemetry query boundary.

## Accepted runtime order

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
scope_aware_drilldown
prometheus_rule_context
prometheus_rule_context_integration
```

All runtime stages exited `0/SUCCESS`, including `prometheus_rule_context` and `prometheus_rule_context_integration`.

## Accepted final incident contract

```text
incident_candidates_version: 0.4
prometheus_rule_context_integration.version: 0.1
prometheus_rule_context_integration.mode: EXACT_COMPLETE_ONLY
source_status.prometheus_rule_context: COMPLETE
mutation_allowed: false
```

The accepted rule source remained:

```text
prometheus_rule_context_version: 0.1
source.status: COMPLETE
requested: KubeCPUOvercommit, Watchdog
matched: KubeCPUOvercommit, Watchdog
unmatched: none
```

## Accepted active candidate behavior

Current active candidates: `1`.

```text
PLATFORM Platform/k3s-main
alerts: KubeCPUOvercommit, Watchdog
selection: COMPLETE_EXACT_RULE_MATCH
matched rules: 2
unmatched: none
```

Accepted safe rule projections:

```text
Watchdog          | group=general.rules        | state=FIRING | health=OK | duration=0s
KubeCPUOvercommit | group=kubernetes-resources | state=FIRING | health=OK | duration=600s
```

Required live verification remains:

```text
PROMETHEUS_RULE_INPUTS
```

The Platform recommendation was refined exactly as intended:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PROMETHEUS_RULE_INPUTS  -> PROMETHEUS_RULE_INPUTS
```

The previous generic Platform target is absent after complete exact integration:

```text
VERIFY_PLATFORM_SIGNAL_INPUTS -> PROMETHEUS_KUBERNETES
```

## Suppressed candidate guard

No non-ACTIVE candidate was enriched with Prometheus rule context.

## Accepted summary

```text
active_candidates_considered_for_prometheus_rule_context: 1
active_candidates_with_complete_prometheus_rule_context: 1
platform_checks_refined_to_prometheus_rule_inputs: 1
prometheus_rule_integration_unknowns: 0
```

Final recommendation target summary matched the final checks exactly:

```text
KUBERNETES_OBJECT: 1
PROMETHEUS_ALERTMANAGER: 1
PROMETHEUS_RULE_INPUTS: 1
```

## Projection and safety guards

```text
forbidden projected keys: none
raw URL markers: false
```

PromQL/query, labels, annotations, files, embedded alerts, last-error text, URLs, credentials, tokens, private keys, and secret payloads were not introduced by the integration.

Every attached rule retains:

```text
expression_persisted: false
```

## Interpretation

This acceptance proves that complete exact Prometheus rule metadata can narrow the next evidence target for the current active candidate without introducing another telemetry query or claiming cause. The current PromQL input values remain intentionally unobserved. Rule state/health is evidence about the rule, not proof of root cause, business impact, or remediation.
