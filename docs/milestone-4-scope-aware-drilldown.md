# Milestone 4 — Scope-Aware Drill-down Recommendations

## Purpose

Reduce operator cognitive load by making incident-candidate next-evidence recommendations depend on the validated scope and evidence strength already available.

This slice is derived-only. It does not collect new telemetry.

## Input

The post-step consumes the final local artifact after routing integration:

```text
/var/lib/infra-assurance/evidence/incident-candidates.json
```

Expected input version:

```text
incident_candidates_version: 0.2
```

## Output

The same artifact is atomically rewritten as:

```text
incident_candidates_version: 0.3
drilldown_policy.version: 0.1
drilldown_policy.mode: SCOPE_AWARE
mutation_allowed: false
```

The Markdown summary is regenerated from the refined artifact.

## Scope policy

### Workload

An existing log recommendation may remain for an active Workload candidate when alert and Kubernetes Event source evidence are complete.

### Service

An existing log recommendation may remain only when final routing context identifies complete preferred workload routing:

```text
selection: PREFERRED_ROUTING_EVIDENCE
state: RESOLVED_WORKLOAD_ROUTING
related_workloads_total > 0
```

The recommendation text names the routed workload backends rather than treating the Service itself as a log source.

### Namespace

No default log recommendation. Namespace membership remains breadth context and is not a concrete workload-selection rule.

### Node

No default Loki recommendation. Existing Node workload-placement verification remains the relevant evidence request.

### Platform

No default log recommendation. Preserve Prometheus/Alertmanager current-condition verification and Prometheus/Kubernetes rule-input/cluster-state verification.

## Evidence completeness

Default log drill-down requires both:

```text
source_status.alert_attention = COMPLETE
source_status.kubernetes_events = COMPLETE
```

If either is incomplete, existing refresh recommendations remain and the log recommendation is withheld.

## Preserved semantics

The slice does not modify:

- candidate grouping;
- candidate state;
- alert records;
- scope identity;
- related Warning Events;
- routing ownership;
- related workload impact context;
- exact recent change;
- exact drift;
- remediation state.

Event/change/drift verification recommendations are preserved unchanged.

## Runtime order

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
routing_context_integration
scope_aware_drilldown
```

## Trust boundary

No Kubernetes, Prometheus, Alertmanager, Loki, OpenTelemetry, Git, or network query is performed by this post-step. No RBAC change is required.

A recommendation is a request for the next evidence source, not a root-cause conclusion or remediation instruction.
