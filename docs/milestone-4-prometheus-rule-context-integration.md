# Milestone 4 — Prometheus Rule Context Integration

## Status

Accepted after repository and management-host live validation.

## Goal

Make the accepted bounded Prometheus rule evidence from PR #26 directly useful in incident drill-down without adding a new infrastructure query.

## Inputs

```text
/var/lib/infra-assurance/evidence/incident-candidates.json
/var/lib/infra-assurance/evidence/prometheus-rule-context.json
```

The post-step runs after rule-context collection and rewrites only the local incident artifact and its Markdown summary.

## Accepted output contract

```text
incident_candidates_version: 0.4
prometheus_rule_context_integration.version: 0.1
prometheus_rule_context_integration.mode: EXACT_COMPLETE_ONLY
mutation_allowed: false
```

`source_status.prometheus_rule_context` records the rule source status used by the integration.

## Promotion rule

An ACTIVE candidate receives `COMPLETE_EXACT_RULE_MATCH` only when:

- rule source is `COMPLETE`;
- candidate ID joins exactly;
- current candidate alert names exactly match the rule-context candidate alert names;
- unmatched alert names are empty;
- every referenced rule ID exists;
- matched rule records cover the exact current candidate alert-name set.

Any deviation remains explicit and does not receive the stronger recommendation refinement.

## Candidate context

For complete exact matches, persist only the accepted safe rule projection:

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
expression_persisted=false
```

No PromQL, labels, annotations, file paths, embedded alert payloads, last-error text, raw API payloads, URLs, credentials, or connection strings are introduced.

## Drill-down refinement

For an ACTIVE Platform candidate with complete exact rule context:

```text
VERIFY_PLATFORM_SIGNAL_INPUTS -> PROMETHEUS_KUBERNETES
```

becomes:

```text
VERIFY_PROMETHEUS_RULE_INPUTS -> PROMETHEUS_RULE_INPUTS
```

The existing current-condition verification remains:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
```

This narrows the next evidence target. It does not claim that rule state or health explains the alert.

## Conservative fallback

Keep `PROMETHEUS_KUBERNETES` when:

- source is partial or failed;
- candidate context is absent;
- candidate alert set differs;
- matched rule record is missing;
- one or more alert names are unmatched;
- matched rules do not cover the candidate alert set.

Each such case is recorded in `prometheus_rule_context_integration_unknowns`.

Suppressed candidates remain unchanged.

## Safety boundary

This slice is derived-only:

- no RBAC change;
- no subprocess or `kubectl` invocation;
- no Prometheus/Alertmanager/Kubernetes/Loki/OpenTelemetry query;
- no mutation;
- no new cause or impact claim.

## Package and runtime

Package version: `0.18.0`.

Runtime order ends with:

```text
scope_aware_drilldown
prometheus_rule_context
prometheus_rule_context_integration
```

## Accepted repository/live evidence

```text
RBAC changes: none
query-capable markers: none
204 passed in 1.29s
all runtime stages: status=0/SUCCESS
rule source: COMPLETE
active candidate: Platform/k3s-main
active alert names: KubeCPUOvercommit, Watchdog
selection: COMPLETE_EXACT_RULE_MATCH
matched rules: 2
unmatched: none
PROMETHEUS_ALERTMANAGER preserved
PROMETHEUS_RULE_INPUTS selected
PROMETHEUS_KUBERNETES removed from eligible Platform candidate
non-active candidates enriched: none
integration unknowns: none
target summary matches checks: true
forbidden projected keys: none
raw URL markers: false
```

## Milestone interpretation

Milestone 4 now has accepted evidence for runtime signals, alert handling, Kubernetes Events, incident grouping, impact context, validated scope identities, observed routing ownership, scope-aware drill-down, bounded Prometheus rule metadata, and exact rule-context integration.

The final `PROMETHEUS_RULE_INPUTS` recommendation is intentionally a live verification target delegated to the authoritative metrics engine. Automatically evaluating arbitrary PromQL is not required to close this evidence-first Milestone 4 slice and would be a separate design decision if later operational evidence justifies it.
