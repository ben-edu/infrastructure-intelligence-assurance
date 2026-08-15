# Milestone 4 Routing Ownership Live Test Gate — 2026-08-15

## Status

Accepted on `mgmt-automation`.

## Scope

Validate bounded read-only EndpointSlice/Pod/ReplicaSet routing ownership evidence before allowing it to influence topology, inventory, or incident candidates.

## Repository gate

The first management-host attempt stopped at pytest before bootstrap because a regression test incorrectly parsed multiple ClusterRole rules as one Pod rule:

```text
1 failed, 145 passed in 0.98s
```

No live RBAC/runtime change was applied in that failed attempt.

After correcting the test parser, the complete repository suite passed:

```text
146 passed in 0.92s
```

## Live acceptance

Bootstrap completed successfully and the normal systemd oneshot finished with all stages successful:

```text
ExecStartPre Git declared observer: SUCCESS
ExecStart Kubernetes runtime:       SUCCESS
ExecStartPost routing ownership:    SUCCESS
ExecStartPost incident candidates:  SUCCESS
```

Git declared-state source remained `COMPLETE` with 27 normalized records at revision:

```text
5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
```

The oneshot returned to `inactive (dead)` after `status=0/SUCCESS`, as expected.

## Accepted RBAC

Observed authorization:

```text
List EndpointSlices : yes
Get EndpointSlices  : no
Get Pods            : yes
List Pods           : no
Watch Pods          : no
Get ReplicaSets     : yes
List ReplicaSets    : no
Watch ReplicaSets   : no
List Secrets        : no
Create Deployment   : no
```

This validates the intended least-privilege boundary:

```text
EndpointSlices: list
Pods:           get only
ReplicaSets:    get only
```

Pod and ReplicaSet objects are not enumerable by the observer. Exact GET remains technically capable of returning a named object because Kubernetes RBAC is not field-level; the collector mitigates this by following only observed target/owner references, applying strict bounds, projecting only owner metadata, and persisting no full Pod/ReplicaSet object content.

## Source status and bounds

Accepted source status:

```text
overall: COMPLETE
EndpointSlices: COMPLETE / LIST_PROJECTED / 79 items
Pods:           COMPLETE / SELECTIVE_GET_PROJECTED
  requested: 60
  present: 60
  absent: 0
  unknown: 0
  skipped_by_bound: 0
ReplicaSets:    COMPLETE / SELECTIVE_GET_PROJECTED
  requested: 37
  present: 37
  absent: 0
  unknown: 0
  skipped_by_bound: 0
```

Configured bounds remained:

```text
max Pod GETs:        500
max ReplicaSet GETs: 250
```

No bound exhaustion occurred.

## Accepted routing result

```text
EndpointSlices:                  79
Endpoint paths:                  79
Pod targets:                     75
Non-Pod targets:                  3
TargetRef missing:                1
Resolved workload paths:         75
Services with EndpointSlices:    78
Services with resolved workloads:63
Services non-Pod only:            1
Services unknown/partial:         1
```

Service route states:

```text
RESOLVED_WORKLOAD_ROUTING: 63
NON_POD_ROUTING:             1
NO_ENDPOINTS_OBSERVED:      13
UNKNOWN:                     1
```

Path resolutions:

```text
RESOLVED_WORKLOAD: 75
NON_POD_TARGET:      3
TARGET_REF_MISSING:  1
```

The only unknown route was `Service/default/kubernetes`, whose EndpointSlice path had no targetRef. The collector kept it `UNKNOWN`; it did not infer or fabricate ownership.

## Loki selector ambiguity resolved by stronger evidence

`Service/monitoring/loki-headless` was previously ambiguous under selector-based controller matching. Live EndpointSlice/owner-reference evidence now shows actual routing to both:

```text
StatefulSet/monitoring/loki
DaemonSet/monitoring/loki-canary
```

Observed route state:

```text
RESOLVED_WORKLOAD_ROUTING
scope_completeness: COMPLETE
EndpointSlices: 2
resolved endpoint paths: 4
```

This is stronger evidence than the previous selector ambiguity. It does not imply business ownership; it establishes current Kubernetes routing/controller relationships.

## Kubelet routing result

The actual Kubernetes Service is:

```text
Service/kube-system/kube-prom-stack-kubelet
```

Its three EndpointSlice targets are cluster-scoped Node objects:

```text
Node/k3s-master-01
Node/k3s-worker-01
Node/k3s-worker-02
```

Accepted route state:

```text
NON_POD_ROUTING
```

All Node targetRefs correctly persisted with `namespace=null`.

The current incident projection still contains Service-scoped subjects named:

```text
Service/keycloak/kube-prom-stack-kubelet
Service/monitoring/kube-prom-stack-kubelet
Service/moodle/kube-prom-stack-kubelet
```

No corresponding routing Service exists in those namespaces. The live routing evidence therefore exposes a downstream alert-scope identity problem: alert labels must not automatically be interpreted as a Kubernetes Service identity by combining `namespace + service`. This issue is outside PR #18 and must be corrected before routing ownership is integrated into incident candidates.

## Downstream isolation

PR #18 deliberately does not feed routing ownership into incident candidates.

Live guard:

```text
incident consumes routing artifact: False
```

This prevented the newly discovered kubelet scope mismatch from being silently converted into false Service-to-workload attribution.

## Sensitive/full-object guard

Accepted live guard:

```text
forbidden projected keys: none
raw URL markers: false
mutation_allowed: false
```

Persisted routing evidence excludes EndpointSlice addresses/IPs, Pod IPs/spec/status, labels, annotations, containers/env, volumes, UIDs, Secret references, service-account tokens, credentials, and logs.

## Acceptance decision

PR #18 routing ownership evidence is accepted.

The next slice must not immediately wire routing ownership into existing incident Service scopes. First validate and correct alert attention scope identity against observed Kubernetes objects so metric labels such as `namespace` and `service` are not treated as an authoritative Kubernetes Service key when they describe different metric dimensions.

Only after that correction should complete routing ownership be used to strengthen topology/inventory/incident context.
