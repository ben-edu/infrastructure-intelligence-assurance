# ADR 0014 — Bounded EndpointSlice and Pod Routing Ownership Evidence

## Status

Accepted for implementation pending live validation.

## Context

The current Kubernetes topology intentionally models Service-to-workload relationships as selector-based controller inference:

```text
Service selector
  -> workload pod-template labels
  -> SELECTOR_MATCH_INFERENCE
```

That relation is useful but weaker than current routing evidence because Kubernetes Services route to endpoints rather than directly to Deployment, StatefulSet, or DaemonSet objects.

Live Milestone 4 incident-candidate evidence exposed three Service-scoped candidates that could not be attributed safely to workloads and therefore recommended:

```text
KUBERNETES_ENDPOINTSLICE_POD
```

The existing topology also contains a known multiple-controller selector ambiguity for `Service/monitoring/loki-headless`.

A stronger evidence path is therefore needed before selector inference is allowed to influence more incident reasoning.

## Decision

Add an acceptance-gated routing ownership artifact that derives current Service backend ownership from a bounded chain:

```text
Service
  <- kubernetes.io/service-name - EndpointSlice
  -> endpoint targetRef
  -> exact Pod metadata GET
  -> controller ownerReference
  -> exact ReplicaSet metadata GET when required
  -> controller ownerReference
  -> currently observed workload controller
```

The resulting artifacts are:

```text
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.json
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.md
```

The new evidence does not replace selector-based topology or alter incident candidates until a separate live-accepted integration slice.

## Observation boundary

### EndpointSlice

The observer receives:

```text
apiGroup: discovery.k8s.io
resource: endpointslices
verb: list
```

The collector uses a JSONPath projection and persists only:

- namespace;
- EndpointSlice name;
- `kubernetes.io/service-name`;
- endpoint `targetRef` API group, kind, namespace, and name;
- endpoint `ready`, `serving`, and `terminating` conditions.

It does not persist:

- endpoint addresses or IPs;
- hostname;
- nodeName;
- zone;
- arbitrary labels;
- annotations;
- UIDs.

### Pods

The observer receives only:

```text
apiGroup: core
resource: pods
verb: get
```

It does not receive Pod `list` or `watch`.

A Pod GET is issued only for an exact Pod name already present in an EndpointSlice `targetRef`.

The kubectl output is projected with JSONPath to controller `ownerReferences` only:

- apiVersion;
- kind;
- name.

The collector does not request or persist Pod specs, status, container configuration, environment variables, labels, annotations, IP addresses, logs, volumes, Secret references, service-account tokens, or owner UIDs.

### ReplicaSets

Deployments normally own ReplicaSets, while ReplicaSets own Pods. To avoid Pod-name parsing, the observer therefore receives only:

```text
apiGroup: apps
resource: replicasets
verb: get
```

It does not receive ReplicaSet `list` or `watch`.

A ReplicaSet GET occurs only for an exact controller ownerReference found in an already-selected Pod. The output is again projected to controller ownerReference apiVersion/kind/name only.

## Least-privilege tradeoff

Kubernetes RBAC is resource-level, not field-level. `get pods` technically authorizes retrieval of a named Pod object if the observer credential is used outside the intended collector.

The mitigation in this slice is:

- no Pod list/watch permission;
- no ReplicaSet list/watch permission;
- exact-name reads only after an EndpointSlice targetRef supplies the name;
- JSONPath output projection in the collector;
- bounded GET counts;
- non-mutating verbs only;
- observer identity remains separate from any future control identity;
- persisted artifacts exclude sensitive/full-object fields.

This is narrower than granting cluster-wide Pod enumeration and is sufficient for the ownership question being answered.

## Bounds

Default per cycle:

```text
max Pod exact GETs:        500
max ReplicaSet exact GETs: 250
```

If a bound is exceeded, the artifact becomes `PARTIAL`. Skipped targets remain explicit and are never converted into absence.

## Resolution semantics

A route can resolve to a workload only when the evidence chain is complete enough.

Examples:

```text
EndpointSlice -> Pod -> StatefulSet
EndpointSlice -> Pod -> DaemonSet
EndpointSlice -> Pod -> ReplicaSet -> Deployment
```

The collector never infers a Deployment, StatefulSet, or DaemonSet from a Pod name.

If `targetRef.kind` is not `Pod`, the path is classified as:

```text
NON_POD_TARGET
```

This is important for infrastructure Services whose endpoints can refer to Nodes or other objects.

If exact-name observation fails, the result remains `UNKNOWN` unless the exact GET authoritatively returns NotFound, which is recorded as absence for that exact referenced object.

## Service route states

```text
RESOLVED_WORKLOAD_ROUTING
PARTIAL_ROUTING
NON_POD_ROUTING
NO_ENDPOINTS_OBSERVED
SERVICE_NOT_OBSERVED
UNKNOWN
```

`RESOLVED_WORKLOAD_ROUTING` means all projected endpoint paths for that Service resolved to currently observed workload controllers through the accepted reference chain. It is not an application-health statement.

`NON_POD_ROUTING` means all projected endpoints use non-Pod target references. It is not a failure.

## Evidence basis

Possible path basis entries include:

```text
ENDPOINTSLICE_SERVICE_NAME_LABEL
ENDPOINT_TARGET_REF
POD_CONTROLLER_OWNER_REFERENCE
REPLICASET_CONTROLLER_OWNER_REFERENCE
CURRENT_WORKLOAD_OBSERVATION
```

These labels describe the evidence chain and must not be promoted into a causal conclusion.

## Acceptance boundary

This slice only creates and validates the new routing ownership artifact.

Until live acceptance succeeds:

- existing selector-based topology remains unchanged;
- inventory relationships remain unchanged;
- incident candidates do not consume the new artifact;
- no previous ambiguity is considered resolved merely because the implementation exists.

A later slice may prefer accepted routing ownership evidence over selector inference where the stronger evidence is current and complete.

## Consequences

Positive:

- live Service routing can be related to workload controllers without Pod-name guessing;
- Pod/ReplicaSet enumeration remains unavailable;
- EndpointSlice IP/address data is not persisted;
- non-Pod routing becomes explicit;
- selector ambiguities can be tested against a stronger evidence chain;
- incident recommendations can later become more precise.

Tradeoffs:

- exact Pod GET permission is still stronger than having no Pod access at all;
- one cycle may perform many exact GETs, so explicit bounds are required;
- workloads owned by unsupported controller kinds remain unresolved;
- targetRefs without Pod ownership remain unknown/non-Pod rather than guessed;
- this slice intentionally does not integrate the result into downstream reasoning yet.

## Revisit when

Revisit the design if:

- EndpointSlice cardinality makes selective exact GETs operationally expensive;
- Kubernetes API field-level authorization becomes available in the environment;
- another trusted source can provide equivalent backend/controller ownership with less privilege;
- live evidence shows ownerReference chains are insufficient for important workload types.
