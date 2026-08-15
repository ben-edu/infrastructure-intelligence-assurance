# Milestone 4 Prometheus Rule Context Live Test Gate — 2026-08-15

## Status

Accepted.

Repository and management-host live acceptance passed on 2026-08-15 for PR #26.

## Purpose

Validate that bounded Prometheus alert-rule metadata can be collected for current ACTIVE incident alert names through the existing read-only Service-proxy boundary without widening RBAC or persisting PromQL/free-form rule payloads.

## Accepted repository evidence

```text
RBAC changes: none
missing required boundary markers: none
unexpected external client markers: none
192 passed in 1.07s
package version: 0.17.0
```

Regression coverage confirms:

- only ACTIVE incident alert names enter the query;
- `type=alert`, `exclude_alerts=true`, and exact repeated `rule_name[]` filters are used;
- suppressed alert names are not queried;
- PromQL, labels, annotations, files, embedded alerts, last-error text, URLs, and raw payloads are not projected;
- exact rule-name correlation only;
- no active candidate causes no Prometheus query;
- alert-name truncation is explicit `PARTIAL`;
- proxy failure is `FAILED_TO_OBSERVE`, not absence;
- current rule-input metric values remain separate required live verification.

## Accepted runtime order

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
scope_aware_drilldown
prometheus_rule_context
```

All stages exited `0/SUCCESS`.

## Accepted trust/source facts

```text
prometheus_rule_context_version: 0.1
mutation_allowed: false
source.type: prometheus_http_api
source.access: kubernetes_service_proxy
source.namespace: monitoring
source.service: kube-prom-stack-prometheus
source.port: 9090
source.operation: GET_RULES_BY_EXACT_ACTIVE_ALERTNAME
source.status: COMPLETE
source.queried: true
max_active_alert_names: 20
active_alert_names_total: 2
active_alert_names_requested: 2
active_alert_names_truncated: false
```

## Accepted current live correlation

Current ACTIVE incident alert names were exactly:

```text
KubeCPUOvercommit
Watchdog
```

Artifact request scope exactly matched those names.

Both names matched Prometheus alert rules; none were unmatched:

```text
KubeCPUOvercommit | group=kubernetes-resources | state=FIRING | health=OK | duration=600s | keep_firing=0s
Watchdog          | group=general.rules        | state=FIRING | health=OK | duration=0s   | keep_firing=0s
```

Summary:

```text
active_alert_names_requested: 2
active_candidates: 1
active_candidates_with_rule_match: 1
alert_names_matched_to_rules: 2
alert_names_unmatched: 0
rule_records: 2
rule_health_ok: 2
rule_health_error: 0
rule_health_unknown: 0
rules_firing: 2
rules_pending: 0
rules_inactive: 0
rules_state_unknown: 0
```

The active candidate was:

```text
Platform/k3s-main
alerts: KubeCPUOvercommit, Watchdog
matched rules: 2
unmatched alerts: none
required live verification: PROMETHEUS_RULE_INPUTS
```

## Projection and sensitive-data guard

Persisted `rules[]` remained within the compact schema projection.

```text
forbidden projected keys: none
raw URL markers: false
all rules expression_persisted=false
unknowns: none
errors: none
```

No PromQL expression/query, labels, annotations, file paths, embedded alert payloads, last-error text, runbook/dashboard URLs, raw API payloads, credentials, tokens, or connection strings were persisted.

## Downstream guard

The rule-context slice did not modify or enrich `incident-candidates.json`.

Accepted downstream state remained:

```text
incident_candidates_version: 0.3
drilldown_policy.mode: SCOPE_AWARE
mutation_allowed: false
```

Current incident candidates remained four total: three SUPPRESSED Namespace candidates and one ACTIVE Platform candidate. The active Platform candidate retained the existing checks:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PLATFORM_SIGNAL_INPUTS  -> PROMETHEUS_KUBERNETES
```

## Interpretation

An exact rule match proves that the queried Prometheus instance returned alert-rule metadata for the same current alert name. Rule health `OK` and state `FIRING` describe Prometheus rule evaluation state at observation time. They do not prove current PromQL input values, root cause, business impact, or required remediation.

Current rule inputs therefore remain separate required live evidence under `PROMETHEUS_RULE_INPUTS`.
