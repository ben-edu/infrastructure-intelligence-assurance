# ADR 0018 — Collect Bounded Prometheus Alert-Rule Context

Status: Accepted after repository and management-host live acceptance on 2026-08-15.

## Context

After scope-aware drill-down, the active `Platform/k3s-main` candidate retained Prometheus/Alertmanager and cluster-state verification. The existing Prometheus observer already accesses `monitoring/kube-prom-stack-prometheus:9090` through the reviewed read-only Kubernetes Service proxy.

Prometheus rule metadata can make `VERIFY_PLATFORM_SIGNAL_INPUTS` more concrete without adding a new telemetry engine. Querying or persisting all rule content would unnecessarily broaden evidence exposure. Rule expressions, annotations, arbitrary labels, embedded alert payloads, file paths, last-error text, URLs, and raw API responses can contain operational or sensitive context that is not required for this slice.

## Decision

Maintain an independent `prometheus-rule-context.json` artifact after final incident recommendation refinement.

Use the existing Prometheus Service-proxy boundary and query only alerting rules for current ACTIVE incident alert names. The request is bounded to at most 20 distinct safe alert names and uses the Prometheus Rules API filters:

```text
type=alert
exclude_alerts=true
rule_name[]=<exact active alert name>
```

No fuzzy rule-name matching is allowed.

The accepted slice does not modify `incident-candidates.json`.

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

A rule match means Prometheus rule metadata was observed for that exact current alert name. It is not proof that any specific metric value caused the current alert.

For a matched candidate, emit separate required live verification:

```text
PROMETHEUS_RULE_INPUTS
```

This indicates that current PromQL input values remain unobserved by this slice.

## Failure semantics

- successful bounded Rules API observation: `COMPLETE`;
- alert-name bound truncation: `PARTIAL`;
- Rules API/proxy failure: `FAILED_TO_OBSERVE`;
- an unmatched exact alert name remains explicit and is not converted into a causal inference;
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

No RBAC expansion was required. The slice reuses the existing Prometheus Service-proxy permission.

## Live acceptance evidence

Repository/live acceptance passed with:

```text
192 passed in 1.07s
RBAC changes: none
source.status: COMPLETE
active alert names requested: 2
active alert names matched: 2
unmatched alert names: 0
rule health OK: 2
rules FIRING: 2
forbidden projected keys: none
raw URL markers: false
unknowns: none
errors: none
mutation_allowed: false
```

The live active rules were:

```text
KubeCPUOvercommit | kubernetes-resources | FIRING | health=OK
Watchdog          | general.rules        | FIRING | health=OK
```

Both exact matches retained `PROMETHEUS_RULE_INPUTS` as a separate required live verification target.

## Consequences

The operator gains bounded, provenance-bearing Prometheus rule metadata for current active alerts while rule expressions and sensitive/free-form fields remain outside evidence.

Rule metadata can now be used in a separately accepted derived integration slice to improve incident drill-down. That integration must preserve the distinction between observed rule metadata and unobserved current metric input values, and must not introduce root-cause, business-impact, or remediation claims without additional evidence.
