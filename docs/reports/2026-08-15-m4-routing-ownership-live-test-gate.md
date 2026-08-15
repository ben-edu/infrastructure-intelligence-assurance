# Milestone 4 Routing Ownership Live Test Gate — 2026-08-15

## Status

Repository test gate passed. Live bootstrap/runtime acceptance still pending.

## Scope

Validate bounded read-only EndpointSlice/Pod/ReplicaSet routing ownership evidence before allowing it to influence topology, inventory, or incident candidates.

## First management-host attempt

The first run stopped at pytest before bootstrap or any infrastructure/RBAC change was applied.

```text
1 failed, 145 passed in 0.98s
```

Failed test:

```text
tests/test_routing_ownership_wiring.py::test_rbac_allows_endpointslice_list_but_only_exact_get_capability_for_pods_and_replicasets
```

Cause: regression-test parsing defect, not an RBAC implementation defect. The test used a text split that included later rules from the same ClusterRole and therefore attributed unrelated `list/watch` verbs to the Pod rule.

The test was corrected to inspect each rule independently.

Because pytest failed, `bootstrap-observer.sh` did not execute in the first attempt. No live RBAC/runtime claim is derived from that attempt.

## Corrected repository test gate

The corrected branch was fast-forwarded on `mgmt-automation` and the complete repository test suite passed:

```text
146 passed in 0.92s
```

Branch checkpoint tested:

```text
44a13b0 record first PR 18 live gate failure
```

This establishes repository-level correctness for the current branch. It does not yet establish live Kubernetes RBAC or routing evidence; bootstrap and runtime acceptance remain required.

## Required live acceptance evidence

1. Existing observer collection, Prometheus, Alertmanager, Event, inventory, incident candidate, Git, history, and drift flows remain healthy.
2. New RBAC is exactly bounded to:

```text
EndpointSlice: list
Pod:           get
ReplicaSet:    get
```

3. The observer still cannot:

```text
get EndpointSlices directly
list/watch Pods
list/watch ReplicaSets
read Secrets
mutate Kubernetes resources
```

4. Normal systemd execution emits:

```text
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.json
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.md
```

5. Routing ownership executes before the existing incident candidate post-step.
6. Incident candidates do not yet consume routing ownership evidence.
7. EndpointSlice collection status is explicit and current.
8. Pod and ReplicaSet source modes report `SELECTIVE_GET_PROJECTED` and their exact requested/executed/skipped counts.
9. GET bounds remain:

```text
max Pod GETs:        500
max ReplicaSet GETs: 250
```

10. Bound exhaustion or failed exact observation becomes `PARTIAL`/`UNKNOWN`, not absence.
11. Exact NotFound is the only failed exact-read case that can establish absence for that exact target.
12. Pod-backed routes resolve only through targetRef plus ownerReference chains.
13. Deployment routes use Pod -> ReplicaSet -> Deployment controller owner references, never Pod-name parsing.
14. StatefulSet/DaemonSet direct controller owner references can resolve without ReplicaSet inference.
15. Non-Pod targetRefs remain explicitly non-Pod; they are not forced into workload ownership.
16. Cluster-scoped targetRefs such as Node retain `namespace=null`.
17. `Service/monitoring/loki-headless` is inspected specifically because selector inference was previously ambiguous.
18. Current Service-scoped `kube-prom-stack-kubelet` incident candidates are inspected specifically to determine whether their actual EndpointSlice targets are Pods, Nodes, or another object class.
19. Endpoint addresses/IPs, Pod IPs, specs, status payloads, labels, annotations, environment/container configuration, Secret references, UIDs, logs, and service-account tokens are absent from the persisted artifact.
20. `mutation_allowed=false`.
21. No previous selector ambiguity is considered resolved until the live artifact supports the stronger relation.

## Expected interpretation

A `NON_POD_ROUTING` result is valid evidence, not a failed test.

A `PARTIAL` source can be acceptable if the reason is explicit and bounded, but missing routes must remain unknown and downstream integration must remain blocked for those paths.

A Service can legitimately resolve to multiple workload controllers if live EndpointSlices actually route to Pods owned by different controllers. That is stronger evidence than selector ambiguity but is still not a business-ownership statement.

The gate does not require every Service to have an EndpointSlice or every endpoint to target a Pod.

## Trust boundary

This slice observes routing/ownership metadata only. It does not ingest Pod content or logs and does not change existing incident reasoning until a separate integration slice passes its own live gate.
