# ADR 0012 — Kubernetes Events Are Bounded Supporting Evidence

## Status

Accepted for Milestone 4 implementation pending live validation.

## Context

Prometheus and Alertmanager now provide current metric-target, alert-evaluation, and alert-handling evidence. The next useful observability signal is the Kubernetes Event stream.

Kubernetes Events can add context for scheduling, image pulls, volume attachment, health probes, admission, node conditions, and other control-plane/runtime activity. They are also transient, noisy, and can contain free-form messages produced by arbitrary components.

The platform must consume Event evidence without turning Event text into a new log store and without promoting temporal proximity into root cause.

## Decision

Add a separate read-only Kubernetes Event runtime source using:

```text
kubectl get events --all-namespaces -o json
```

The observer receives only:

```text
core/v1 events: get, list, watch
```

No Event mutation capability is introduced.

The first slice keeps a bounded current window:

```text
window: 3600 seconds
maximum persisted records: 500
```

Both are configurable runtime bounds.

If the recent Event set exceeds the record bound, the source becomes `PARTIAL`. A no-match correlation cannot then be presented as complete.

## Persisted Event fields

Only structured fields are retained:

- normalized `WARNING | NORMAL | UNKNOWN` type;
- sanitized reason;
- involved-object API version, kind, namespace, and name;
- derived subject label;
- first occurrence time;
- last occurrence time;
- occurrence count;
- evidence ID and observation/expiry timestamps.

The stable Event ID may hash Kubernetes metadata identity internally, but raw Kubernetes UIDs are not serialized as required operator context.

## Explicit exclusions

The first Event slice does not persist:

- `message` / `note` free-form Event text;
- source host / reporting instance;
- arbitrary annotations or labels;
- object UID values;
- credentials, tokens, Secret values, or connection strings.

A reason value that does not fit the narrow safe token format is replaced with `REDACTED_REASON` rather than persisting free-form text.

## Recency semantics

An Event must have a usable occurrence timestamp and fall inside the configured recent window before it becomes current Event evidence.

The normalizer considers the supported Event timestamp fields and does not treat an Event with unknown time as recent.

A missing/invalid occurrence timestamp becomes explicit unknown evidence.

## Correlation semantics

Only recent `WARNING` Events participate in the first alert-attention correlation projection.

Supported relations:

### Direct object identity

For workload, node, or Service attention:

```text
DIRECT_OBJECT_IDENTITY
RECENT_KUBERNETES_WARNING_EVENT
```

The Event involved-object subject must exactly equal the alert-attention subject.

### Namespace scope membership

For Namespace-scoped attention, a Warning Event involving an object in the same namespace can be related using:

```text
NAMESPACE_SCOPE_MEMBERSHIP
RECENT_KUBERNETES_WARNING_EVENT
```

This is scope context only. It does not prove one common cause.

### Deliberately unsupported broad correlation

Platform-scoped alerts are not automatically correlated with every Warning Event in the cluster. That would create a broad relationship that looks causal while carrying little evidence.

Pod Events are not promoted to Deployment/StatefulSet/DaemonSet ownership by Pod-name heuristics. A future slice may add Pod owner-reference evidence if that additional Kubernetes observation is justified.

## Failure and partiality

Event API failure produces:

```text
FAILED_TO_OBSERVE
```

and alert-attention correlations with no observed match become `UNKNOWN`, never `NO_DIRECT_EVENT_MATCH`.

A truncated Event window produces:

```text
PARTIAL
```

and the same no-match rule applies.

Only a `COMPLETE` Event source can support `NO_DIRECT_EVENT_MATCH`.

## Consequences

Positive:

- operators gain recent Kubernetes runtime context beside Prometheus/Alertmanager evidence;
- free-form Event messages do not become an uncontrolled evidence/log surface;
- source failure/truncation cannot become false absence;
- Event correlation remains evidence-linked and bounded;
- workload ownership is not inferred from Pod names;
- no Kubernetes mutation capability is introduced.

Tradeoffs:

- excluding Event message text removes some diagnostic detail;
- a one-hour window is a deliberately narrow first operational horizon;
- Pod-level events often cannot yet be joined to controller workload entities;
- platform alerts may have no automatic Event match even when a human operator could see a plausible relationship.

These are preferred to over-collection and false causal inference in the first slice.

## Deferred

- reviewed message sanitization/tokenization policy;
- Pod owner-reference collection and controller correlation;
- Kubernetes `events.k8s.io/v1` dual-source handling if needed;
- longer-term Event history;
- Loki correlation;
- OpenTelemetry trace correlation;
- cross-signal incident grouping/root-cause hypotheses.
