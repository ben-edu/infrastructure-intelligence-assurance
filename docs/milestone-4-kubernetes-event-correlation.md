# Milestone 4 — Kubernetes Event Correlation

## Purpose

Add bounded recent Kubernetes Event evidence to the existing Prometheus/Alertmanager operational context without turning Events into a log store or treating temporal correlation as root cause.

## Source

Read-only Kubernetes core/v1 Events:

```text
kubectl get events --all-namespaces -o json
```

RBAC addition:

```text
core/v1 events: get, list, watch
```

No Event write capability is added.

## Runtime artifacts

```text
/var/lib/infra-assurance/evidence/kubernetes-event-runtime.json
/var/lib/infra-assurance/evidence/kubernetes-event-runtime.md
/var/lib/infra-assurance/evidence/kubernetes-event-correlation.json
/var/lib/infra-assurance/evidence/kubernetes-event-correlation.md
```

Default bounds:

```text
recent window: 3600 seconds
maximum persisted recent events: 500
```

## Event projection

Persisted fields are deliberately narrow:

- event type;
- safe reason token;
- involved-object identity;
- first/last occurrence;
- occurrence count;
- evidence IDs and observation freshness.

Raw Event messages, source host/reporting instance, arbitrary metadata, UIDs, credentials, and Secret values are not persisted.

## Alert-attention relation

Only recent Warning Events are used for this first correlation slice.

Supported:

- exact Service/Node/Workload object identity;
- Namespace membership for Namespace-scoped alert attention.

Not supported:

- broad platform-alert-to-all-events correlation;
- Pod-name-to-controller heuristics;
- causal/root-cause claims.

A matched Event is supporting context only.

## Partiality

If Event observation fails, source state is `FAILED_TO_OBSERVE`.

If the configured maximum recent Event count is exceeded, source state is `PARTIAL` and no-match correlation becomes `UNKNOWN`.

Only a complete Event read can support `NO_DIRECT_EVENT_MATCH`.

## Acceptance

See:

```text
docs/reports/2026-08-15-m4-kubernetes-event-correlation-live-test-gate.md
```
