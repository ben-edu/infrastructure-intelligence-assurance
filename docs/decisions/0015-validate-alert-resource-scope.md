# ADR 0015 — Validate Alert Resource Scope Against Observed Kubernetes Identity

Status: Accepted and live validated on 2026-08-15.

## Context

PR #18 introduced live-validated EndpointSlice/Pod/ReplicaSet routing ownership evidence. That evidence exposed an existing downstream scope defect: alert attention contained subjects such as:

```text
Service/keycloak/kube-prom-stack-kubelet
Service/monitoring/kube-prom-stack-kubelet
Service/moodle/kube-prom-stack-kubelet
```

while the only observed Kubernetes Service with that name was:

```text
Service/kube-system/kube-prom-stack-kubelet
```

The real kubelet Service routed to Node targetRefs. The alert labels `namespace` and `service` therefore represented different metric dimensions and were not a valid Kubernetes Service compound identity.

## Decision

Alert labels remain signal dimensions. They are not authoritative Kubernetes object identity by themselves.

A label-derived `Service`, `Node`, or `Namespace` scope is retained as an infrastructure subject only when the same-cycle Kubernetes snapshot validates that exact subject identity.

The correction runs as a local derived post-step. It performs no Kubernetes or telemetry query and requires no new RBAC.

Each attention record receives a separate `scope_validation` object so the existing `scope` shape remains compatible with Event correlation and incident grouping.

Supported validation statuses:

```text
VALIDATED_INFRASTRUCTURE_SUBJECT
UNVERIFIED_SIGNAL_DIMENSION
INFERRED_RELATION
PLATFORM_FALLBACK
```

### Service scope

For an original label-derived Service scope:

1. If the exact `Service/<namespace>/<name>` is observed in the current complete snapshot, retain Service scope and mark it validated.
2. If Service observation is complete and the exact Service is not observed, do not rewrite to a similarly named Service elsewhere.
3. If the alert namespace is itself observed, fall back to `Namespace/<namespace>` and mark the original Service claim as `UNVERIFIED_SIGNAL_DIMENSION`.
4. Otherwise fall back to Platform scope.
5. If Service observation is incomplete or failed, the fallback remains explicit and `source_status.kubernetes_scope` is not `COMPLETE`.

### Node and Namespace scope

Node and Namespace label-derived subjects are likewise retained only when the exact same-cycle object identity is observed. Otherwise scope falls back conservatively.

### Workload scope

Existing unique Prometheus-to-workload attribution remains explicitly an inference. This slice does not upgrade selector-based workload association to observed routing ownership.

## Runtime ordering

The systemd cycle is:

```text
main Kubernetes/observability collection
  -> routing ownership derived post-step
  -> alert scope validation + Event correlation rebuild
  -> incident candidate grouping
```

The scope validator reads only:

```text
alert-attention.json
kubernetes.json
kubernetes-event-runtime.json
```

It rewrites:

```text
alert-attention.json
alert-attention.md
kubernetes-event-correlation.json
kubernetes-event-correlation.md
```

before incident grouping runs.

## Trust semantics

- Complete Kubernetes observation plus missing exact identity supports `UNVERIFIED_SIGNAL_DIMENSION`; it does not support rewriting the signal to another resource.
- Failed/incomplete Kubernetes observation remains failed/incomplete observation, not absence.
- Scope validation does not establish root cause or business impact.
- Original allowlisted alert labels remain preserved as signal dimensions.
- No new infrastructure query, RBAC, logs, secrets, credentials, or full Pod object content is introduced.
- `mutation_allowed=false` remains unchanged.

## Live validation evidence

The accepted management-host gate established:

```text
156 passed in 0.89s
alert_attention_version: 0.2
Prometheus source: COMPLETE
Alertmanager source: COMPLETE
Kubernetes scope validation: COMPLETE
Alertmanager alerts: 11
Alert attention: 11
Event correlations: 11
SERVICE scopes: 0
NAMESPACE scopes: 9
PLATFORM scopes: 2
```

All six current kubelet-labelled alerts retained their original signal labels while synthetic Service identities were removed. There were no automatic rewrites to the real kube-system Service, no label mismatches, no sensitive projected keys, and no raw URL markers.

## Consequences

The current kubelet alerts no longer produce nonexistent Service subjects. Their observed namespace dimensions are retained as weaker Namespace scope while the stronger Service claim is explicitly unverified.

Routing ownership remains a separate accepted evidence plane. Its downstream integration is the next acceptance-gated slice rather than being folded into this identity-correction decision.
