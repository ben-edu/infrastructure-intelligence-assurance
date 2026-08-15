# Milestone 4 Prometheus Rule Context Live Test Gate — 2026-08-15

## Status

Pending repository and management-host live acceptance.

## Purpose

Validate that bounded Prometheus alert-rule metadata can be collected for current ACTIVE incident alert names through the existing read-only Service-proxy boundary without widening RBAC or persisting PromQL/free-form rule payloads.

## Required repository evidence

1. Full pytest suite passes.
2. `deploy/kubernetes/observer-rbac.yaml` has no diff from `main`.
3. Package version is `0.17.0`.
4. Rule-context schema validates artifact version `0.1`.
5. Tests prove:
   - only ACTIVE incident alert names enter the query;
   - `type=alert`, `exclude_alerts=true`, and exact repeated `rule_name[]` filters are used;
   - suppressed alert names are not queried;
   - PromQL, labels, annotations, files, embedded alerts, last-error text, URLs, and raw payloads are not projected;
   - exact rule-name correlation only;
   - no active candidate causes no Prometheus query;
   - alert-name truncation is explicit `PARTIAL`;
   - proxy failure is `FAILED_TO_OBSERVE`, not absence;
   - current rule-input metric values remain separate required live verification.

## Required runtime order

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
scope_aware_drilldown
prometheus_rule_context
```

All stages must exit `0/SUCCESS` for live acceptance.

## Final artifact checks

```text
prometheus_rule_context_version: 0.1
mutation_allowed: false
source.type: prometheus_http_api
source.access: kubernetes_service_proxy
source.namespace: monitoring
source.service: kube-prom-stack-prometheus
source.port: 9090
source.operation: GET_RULES_BY_EXACT_ACTIVE_ALERTNAME
```

Record source status, bounds, requested names, matched/unmatched names, rule count, rule health/state summary, and candidate rule matches.

If the currently accepted Platform candidate remains live, expected requested names include:

```text
KubeCPUOvercommit
Watchdog
```

Live alerts are temporal. Different current ACTIVE names are acceptable if the artifact exactly follows the current incident candidate set.

## Rule projection guard

Persisted `rules[]` may contain only compact normalized fields defined by the schema. In particular these raw/API fields must be absent anywhere in the artifact:

```text
query
labels
annotations
file
alerts
lastError
runbook_url
dashboard
```

Every rule must contain:

```text
expression_persisted: false
```

Raw `http://` / `https://` markers must be absent.

## Candidate semantics

For each ACTIVE candidate:

- exact alert names are listed;
- matching rule IDs use `EXACT_ALERTNAME_PROMETHEUS_RULE_MATCH`;
- unmatched names remain explicit;
- matched rule context emits `PROMETHEUS_RULE_INPUTS` as required live verification;
- rule metadata does not establish cause.

## Downstream guard

This slice must not modify or enrich `incident-candidates.json`. Its accepted version must remain `0.3` with `drilldown_policy.mode=SCOPE_AWARE`.

## Interpretation

A successful exact rule match means the currently queried Prometheus instance returned alert-rule metadata for the same alert name. It does not prove the current PromQL input values or root cause. Those inputs remain a separate evidence requirement.
