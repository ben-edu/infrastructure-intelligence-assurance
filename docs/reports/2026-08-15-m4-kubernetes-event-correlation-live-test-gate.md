# Milestone 4 Kubernetes Event Correlation Live Test Gate — 2026-08-15

## Status

Pending management-host live acceptance.

## Scope

Validate bounded recent Kubernetes Event observation and conservative correlation with the already accepted Prometheus/Alertmanager alert-attention projection.

## Required acceptance evidence

1. Full repository tests pass.
2. Existing Kubernetes, Git, history, drift, inventory, Prometheus Operator, Prometheus runtime, and Alertmanager runtime sources remain healthy.
3. Observer can list Kubernetes Events cluster-wide.
4. Observer cannot create Kubernetes Events.
5. Secret listing and Kubernetes mutation remain denied.
6. Normal runtime emits:

```text
/var/lib/infra-assurance/evidence/kubernetes-event-runtime.json
/var/lib/infra-assurance/evidence/kubernetes-event-runtime.md
/var/lib/infra-assurance/evidence/kubernetes-event-correlation.json
/var/lib/infra-assurance/evidence/kubernetes-event-correlation.md
```

7. Event source state is explicit: `COMPLETE`, `PARTIAL`, or `FAILED_TO_OBSERVE`.
8. Default recent window is one hour with a maximum of 500 persisted records.
9. If the Event window is truncated, source state becomes `PARTIAL`.
10. Raw Event `message`/`note`, source host/reporting instance, arbitrary annotations/labels, raw object UIDs, credentials, and Secret values are absent from persisted evidence.
11. Event reason is either a safe bounded token or `REDACTED_REASON`.
12. Only recent Warning Events are attached to alert-attention records in this slice.
13. Exact Service/Node/Workload identity can correlate directly.
14. Namespace-scoped attention can receive namespace-membership Event context with an explicit `NAMESPACE_SCOPE_MEMBERSHIP` basis.
15. Platform-scoped alerts are not automatically related to every cluster Event.
16. Pod Events are not mapped to Deployment/StatefulSet/DaemonSet by Pod-name heuristics.
17. A related Event is described as supporting context, not root cause.
18. A failed/partial Event source makes unsupported no-match correlation `UNKNOWN`, not false `NO_DIRECT_EVENT_MATCH`.
19. `mutation_allowed=false` remains in generated Event artifacts.

## Expected interpretation

The gate does not require zero Warning Events or a specific number of Event/alert matches.

Real recent Warning Events are evidence under test. A complete source with no direct matches is valid. A partial source due to the configured record bound is also valid if partiality is explicit and no-match results become unknown.

The first live run should be used to decide whether the one-hour/500-record defaults are appropriate for this cluster; they are not assumed to be final long-term retention policy.

## Trust boundary

Kubernetes remains authoritative for Event records. Prometheus and Alertmanager remain authoritative for their respective signals. This slice adds bounded structured Event context and conservative relations only; it does not replace logging, infer Pod controller ownership, or claim root cause.
