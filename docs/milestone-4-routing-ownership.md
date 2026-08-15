# Milestone 4 — Kubernetes Routing Ownership Evidence

## Purpose

Strengthen Service backend ownership evidence without broad Pod enumeration and without changing existing incident semantics before live acceptance.

This slice addresses a structural uncertainty exposed by accepted Milestone 4 incident candidates:

```text
Service -> workload selector inference
```

is not equivalent to current Service routing.

## Inputs

The slice uses:

- the current normalized Kubernetes snapshot for Service and workload-controller identity;
- a projected cluster-wide EndpointSlice list;
- exact-name Pod controller-owner GETs only for Pod targetRefs found in EndpointSlices;
- exact-name ReplicaSet controller-owner GETs only when a selected Pod is owned by a ReplicaSet.

## Outputs

```text
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.json
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.md
```

Package/implementation version:

```text
0.13.0
```

Routing ownership artifact version:

```text
0.1
```

## Read-only access change

New observer permissions:

```text
EndpointSlice: list
Pod:           get
ReplicaSet:    get
```

Explicitly not granted:

```text
Pod:        list/watch
ReplicaSet: list/watch
Secrets:    any access
mutation:   create/update/patch/delete
```

Pod and ReplicaSet GETs are selective and bounded, not enumeration paths.

## Persisted safe projection

EndpointSlice projection retains:

- namespace;
- EndpointSlice name;
- Service association label;
- endpoint targetRef identity;
- endpoint readiness/serving/terminating conditions.

Pod/ReplicaSet projection retains only controller ownerReference identity:

- API group;
- kind;
- name.

The artifact does not retain EndpointSlice addresses, Pod IPs, Pod specs/status, labels, annotations, container/env data, logs, volumes, Secret references, service-account tokens, or owner UIDs.

## Ownership resolution

Supported direct chains:

```text
Service -> EndpointSlice -> Pod -> StatefulSet
Service -> EndpointSlice -> Pod -> DaemonSet
```

Supported Deployment chain:

```text
Service -> EndpointSlice -> Pod -> ReplicaSet -> Deployment
```

Every hop is evidence-backed by a current reference or exact observation.

Pod-name parsing is forbidden.

Non-Pod EndpointSlice targetRefs remain explicit `NON_POD_TARGET` evidence.

## Bounds and failure semantics

Per-cycle defaults:

```text
max_pod_gets = 500
max_replicaset_gets = 250
```

Bound exhaustion produces `PARTIAL`, never false absence.

Exact GET NotFound can establish absence for that exact target. Forbidden, timeout, parse failure, or other failed observation remains `UNKNOWN`.

## Downstream isolation

This is an acceptance-gated evidence slice.

The current `topology.json`, `inventory.json`, and `incident-candidates.json` continue using their already accepted semantics during this PR.

The new artifact is generated before the existing incident post-step but is not passed to it.

Only after live acceptance may a subsequent slice replace weaker selector inference with current routing ownership where the new evidence is sufficiently complete.

## Expected live questions

The first live run should answer:

1. How many current EndpointSlices exist?
2. How many endpoint targetRefs are Pods vs non-Pod objects?
3. How many exact Pod/ReplicaSet GETs are actually required?
4. Which Services resolve to current workload controllers?
5. Does `Service/monitoring/loki-headless` become less ambiguous?
6. Are the current `kube-prom-stack-kubelet` Service candidates actually Pod-backed or non-Pod-backed?
7. Which paths remain unknown/partial and why?

## Not in this slice

- changing incident candidate ownership/context;
- changing existing topology relation precedence;
- Loki ingestion;
- OpenTelemetry ingestion;
- Pod logs;
- Pod/container health expansion;
- Pod placement inventory;
- business ownership or business-impact modeling;
- any mutation.
