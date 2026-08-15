# ADR 0019 — Integrate Exact Prometheus Rule Context into Incident Drill-down

Status: Accepted after repository and management-host live validation.

## Context

PR #26 established an accepted, bounded Prometheus rule-context source for current ACTIVE incident alert names. The source is read-only, reuses the existing Prometheus Kubernetes Service-proxy boundary, and intentionally excludes PromQL expressions, labels, annotations, raw payloads, URLs, credentials, and current rule-input metric values.

The active Platform candidate previously carried a generic verification target:

```text
VERIFY_PLATFORM_SIGNAL_INPUTS -> PROMETHEUS_KUBERNETES
```

The accepted rule artifact can reduce that search space when it is complete and exactly covers the active candidate, without issuing another infrastructure query.

## Decision

Add a derived-only post-step after `prometheus_rule_context`.

The integration reads only:

```text
incident-candidates.json
prometheus-rule-context.json
```

It performs no Kubernetes, Prometheus, Alertmanager, Loki, OpenTelemetry, network, or subprocess query.

Promote rule metadata into an ACTIVE incident candidate only when all of the following hold:

1. incident input version is `0.3`;
2. rule-context input version is `0.1`;
3. both artifacts identify the same cluster;
4. both artifacts keep `mutation_allowed=false`;
5. rule source status is `COMPLETE`;
6. the existing `candidate_id` joins exactly;
7. candidate alert names exactly equal the rule-context candidate alert names;
8. no alert name is unmatched;
9. all referenced rule IDs exist;
10. the matched rule records cover the exact candidate alert-name set.

The successful selection is:

```text
COMPLETE_EXACT_RULE_MATCH
```

No fuzzy matching is allowed.

## Safe candidate projection

For accepted exact matches, attach only:

- rule ID and evidence ID;
- alert name;
- sanitized group name;
- alerting rule type;
- normalized rule state and health;
- duration / keep-firing / evaluation-time metadata;
- last-evaluation timestamp;
- `expression_persisted=false`;
- exact-match basis and evidence IDs.

Do not attach PromQL/query, labels, annotations, file paths, embedded alerts, last-error text, raw payloads, URLs, credentials, tokens, or connection strings.

## Recommendation refinement

For an ACTIVE Platform candidate with `COMPLETE_EXACT_RULE_MATCH`, replace only:

```text
VERIFY_PLATFORM_SIGNAL_INPUTS -> PROMETHEUS_KUBERNETES
```

with:

```text
VERIFY_PROMETHEUS_RULE_INPUTS -> PROMETHEUS_RULE_INPUTS
```

Preserve:

```text
VERIFY_ALERT_CONDITION_CURRENT -> PROMETHEUS_ALERTMANAGER
```

The new target remains a required live verification. Rule metadata does not prove current input metric values, root cause, business impact, or remediation.

## Failure semantics

If the rule source is `PARTIAL` or `FAILED_TO_OBSERVE`, candidate context is missing, alert sets differ, a rule record is missing, or any active alert name is unmatched:

- do not promote the candidate to complete rule context;
- retain the generic `PROMETHEUS_KUBERNETES` Platform verification;
- record an explicit integration unknown;
- do not infer absence or cause.

Suppressed candidates are not enriched by this slice.

## Accepted live evidence

Repository/live acceptance on `mgmt-automation` established:

```text
RBAC changes: none
query-capable markers: none
204 passed in 1.29s
all runtime stages: status=0/SUCCESS
incident_candidates_version: 0.4
integration mode: EXACT_COMPLETE_ONLY
rule source: COMPLETE
active candidates considered: 1
complete exact candidate contexts: 1
integration unknowns: 0
forbidden projected keys: none
raw URL markers: false
```

The current active `Platform/k3s-main` candidate exactly matched `KubeCPUOvercommit` and `Watchdog`, retained `PROMETHEUS_ALERTMANAGER`, and narrowed the generic Platform evidence target to `PROMETHEUS_RULE_INPUTS`.

## Runtime order

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

## Consequences

The operator gets exact rule identity/state context directly beside the active incident candidate and a narrower next evidence target, while current metric inputs remain explicitly unobserved. The slice introduces no RBAC expansion, no new telemetry query, no Loki/OpenTelemetry ingestion, and no mutation capability.

This accepted slice is sufficient for Milestone 4's evidence-first drill-down boundary: recommended live checks may remain delegated to authoritative observability systems rather than being automatically executed by the platform.
