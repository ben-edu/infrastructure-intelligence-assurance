# ADR 0018 — Collect Bounded Prometheus Alert-Rule Context

Status: Proposed; pending repository and management-host live acceptance.

## Context

After scope-aware drill-down, the current active `Platform/k3s-main` candidate retains only Prometheus/Alertmanager and cluster-state verification. The existing Prometheus observer already accesses `monitoring/kube-prom-stack-prometheus:9090` through the reviewed read-only Kubernetes Service proxy.

Prometheus rule metadata can make `VERIFY_PLATFORM_SIGNAL_INPUTS` more concrete without adding a new telemetry engine. However, querying or persisting all rule content would unnecessarily broaden evidence exposure. Rule expressions, annotations, arbitrary labels, embedded alert payloads, file paths, last-error text, URLs, and raw API responses can contain operational or sensitive context that is not required for this first slice.

## Decision

Add an independent `prometheus-rule-context.json` artifact after final incident recommendation refinement.

Use the existing Prometheus Service-proxy boundary and query only alerting rules for current ACTIVE incident alert names. The request is bounded to at most 20 distinct safe alert names and uses the Prometheus Rules API filters:

```text
type=alert
exclude_alerts=true
rule_name[]=<exact active alert name>
```

No fuzzy rule-name matching is allowed.

The slice does not modify `incident-candidates.json`. Rule context must pass live acceptance before downstream integration.

## Persisted projection

Persist only:

- exact alert/rule name;
- sanitized rule-group identity;
- alerting-rule type;
- normalized rule state and health;
- numeric duration / keep-firing / evaluation-time metadata where present;
- last-evaluation timestamp where present;
- evidence IDs, observation timestamps, source status, collector provenance, and bounds.

Set:

```text
expression_persisted: false
```

Do not persist:

- PromQL expression/query;
- rule labels or annotations;
- rule file paths;
- embedded active alerts;
- last-error text;
- dashboards/runbook URLs;
- raw API payloads;
- credentials, tokens, or connection strings.

## Correlation semantics

Correlate ACTIVE incident alert names to rule records by exact `alertname == rule.name` only.

A rule match means the Prometheus rule metadata was observed for that exact current alert name. It is not proof that any specific metric value caused the current alert.

For a matched candidate, emit separate required live verification:

```text
PROMETHEUS_RULE_INPUTS
```

This indicates that current PromQL input values remain unobserved by this slice.

## Failure semantics

- successful bounded Rules API observation: `COMPLETE`;
- alert-name bound truncation: `PARTIAL`;
- Rules API/proxy failure: `FAILED_TO_OBSERVE`;
- an unmatched exact alert name is explicit context and must not be silently converted into a causal inference;
- no ACTIVE incident alert names means no Rules API request is necessary for that cycle.

## Runtime order

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
scope_aware_drilldown
prometheus_rule_context
```

No RBAC expansion is intended. The slice reuses the existing Prometheus Service-proxy permission.

## Consequences

The operator gains bounded, provenance-bearing Prometheus rule metadata for current active alerts while keeping rule expressions and sensitive/free-form fields outside evidence. A later, separately accepted slice may use this artifact to enrich Platform drill-down; this ADR does not establish root cause, business impact, or remediation.
