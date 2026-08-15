# Milestone 4 Prometheus Rule Context Integration Live Test Gate — 2026-08-15

## Status

Pending repository and management-host live acceptance.

## Purpose

Validate that accepted local Prometheus rule context can enrich ACTIVE incident drill-down and refine the generic Platform evidence target without any new infrastructure query, RBAC expansion, sensitive-field exposure, or causal overstatement.

## Required repository evidence

1. Full pytest suite passes.
2. `deploy/kubernetes/observer-rbac.yaml` has no diff from `main`.
3. Package version is `0.18.0`.
4. The integration module contains no query-capable client or subprocess boundary.
5. Extension schema fixes final incident version `0.4`, integration version `0.1`, mode `EXACT_COMPLETE_ONLY`, and strict safe rule projection.
6. Tests prove:
   - complete exact Platform context refines `PROMETHEUS_KUBERNETES` to `PROMETHEUS_RULE_INPUTS`;
   - `PROMETHEUS_ALERTMANAGER` current-condition verification remains;
   - source PARTIAL/FAILED retains generic verification;
   - unmatched/mismatched/missing rule context is explicit and not promoted;
   - suppressed candidates are not enriched;
   - cluster/version/mutation guards are enforced;
   - PromQL/free-form/sensitive rule fields cannot enter the attached projection.

## Required runtime order

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

All stages must exit `0/SUCCESS`.

## Final incident checks

```text
incident_candidates_version: 0.4
prometheus_rule_context_integration.version: 0.1
prometheus_rule_context_integration.mode: EXACT_COMPLETE_ONLY
source_status.prometheus_rule_context: COMPLETE
mutation_allowed: false
```

If the current active Platform candidate remains `KubeCPUOvercommit + Watchdog` and PR #26 rule context remains complete, expected live behavior is:

```text
selection: COMPLETE_EXACT_RULE_MATCH
matched rules: 2
unmatched alert names: none
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
VERIFY_PROMETHEUS_RULE_INPUTS  -> PROMETHEUS_RULE_INPUTS
```

`VERIFY_PLATFORM_SIGNAL_INPUTS -> PROMETHEUS_KUBERNETES` must no longer remain on that candidate after complete exact integration.

Live alert state is temporal. Different active alert names are acceptable if the integration follows the current accepted rule artifact exactly.

## Fallback checks

If rule source is not COMPLETE or exact coverage is not complete, the integration must retain the generic Platform verification and emit an explicit integration unknown. No partial rule context may silently become causal evidence.

## Safe projection guard

Attached candidate `matched_rules[]` may contain only:

```text
rule_id
evidence_id
alertname
group_name
rule_type
state
health
duration_seconds
keep_firing_for_seconds
evaluation_time_seconds
last_evaluation
expression_persisted
```

`expression_persisted` must remain `false`.

The final incident artifact must not introduce:

```text
query
expr
expression
labels
annotations
file
alerts
lastError
runbook_url
dashboard_url
generatorURL
password
token
authorization
private_key
privateKey
secret_payload
```

No raw `http://` or `https://` marker may be introduced by the integration projection.

## Recommendation summary

Recalculate `recommended_next_evidence_targets` from final candidate checks. In the expected current Platform case, `PROMETHEUS_RULE_INPUTS` should replace `PROMETHEUS_KUBERNETES` while the Alertmanager target remains.

## Interpretation

A successful integration proves that the accepted rule-context source exactly matched the current active candidate and that the platform narrowed the next evidence target. It does not prove current PromQL input values, root cause, business impact, or remediation.
