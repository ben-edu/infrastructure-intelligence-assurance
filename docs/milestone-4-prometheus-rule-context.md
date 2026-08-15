# Milestone 4 — Bounded Prometheus Rule Context

## Goal

Provide a small, read-only Prometheus alert-rule evidence slice for current ACTIVE incident alert names so Platform drill-down can reference exact rule metadata before considering broader telemetry.

This does not replace Prometheus, evaluate PromQL inputs, establish root cause, or modify incident candidates.

## Input

```text
/var/lib/infra-assurance/evidence/incident-candidates.json
```

The final scope-aware incident artifact is read after routing and recommendation refinement.

## Source

Existing reviewed Prometheus Kubernetes Service proxy:

```text
monitoring/kube-prom-stack-prometheus:9090
```

Rules request is limited to current ACTIVE alert names:

```text
GET /api/v1/rules
  type=alert
  exclude_alerts=true
  rule_name[]=<exact alert name>
```

Maximum requested distinct alert names per cycle: 20.

## Output

```text
/var/lib/infra-assurance/evidence/prometheus-rule-context.json
/var/lib/infra-assurance/evidence/prometheus-rule-context.md
```

Contract version:

```text
prometheus_rule_context_version: 0.1
mutation_allowed: false
```

## Safe projection

The artifact retains compact rule identity/state metadata and provenance. It does not persist PromQL expressions, labels, annotations, rule file paths, embedded alerts, last-error text, URLs, raw payloads, credentials, tokens, or connection strings.

Each persisted rule explicitly records:

```text
expression_persisted: false
```

## Correlation

ACTIVE candidate alert names join to rule records by exact name only.

For exact matches, candidate context records rule IDs and evidence IDs. It also records required live verification target:

```text
PROMETHEUS_RULE_INPUTS
```

because the rule definition/state does not prove the current metric values that caused evaluation.

## Failure semantics

- `COMPLETE`: bounded rule request succeeded without truncation;
- `PARTIAL`: alert-name request scope was truncated;
- `FAILED_TO_OBSERVE`: Prometheus Service-proxy/Rules API request failed;
- unmatched names remain explicit and do not become fuzzy matches;
- no ACTIVE alert names results in no query and an empty current-scope artifact.

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

## Acceptance boundary

Live acceptance must confirm:

- no RBAC diff;
- full pytest passes;
- final post-step exits `0/SUCCESS`;
- source uses the same Prometheus Service proxy;
- requested names are only current ACTIVE incident alert names and remain bounded;
- current Platform alert names, if still present, exact-match appropriate rule metadata or remain explicitly unmatched;
- no forbidden/free-form rule fields are persisted;
- no raw URL markers appear;
- `mutation_allowed=false`;
- `incident-candidates.json` remains version 0.3 and is not enriched by this slice.

Only after this artifact is accepted should a separate integration slice consider attaching rule context to incident drill-down.
