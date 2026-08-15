# Milestone 4 Routing Ownership Live Test Gate — 2026-08-15

## Status

Pending management-host live acceptance.

## Scope

Validate bounded read-only EndpointSlice/Pod/ReplicaSet routing ownership evidence before allowing it to influence topology, inventory, or incident candidates.

## Required acceptance evidence

1. Full repository tests pass.
2. Existing observer collection, Prometheus, Alertmanager, Event, inventory, incident candidate, Git, history, and drift flows remain healthy.
3. New RBAC is exactly bounded to:

```text
EndpointSlice: list
Pod:           get
ReplicaSet:    get
```

4. The observer still cannot:

```text
list/watch Pods
list/watch ReplicaSets
read Secrets
mutate Kubernetes resources
```

5. Normal systemd execution emits:

```text
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.json
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.md
```

6. Routing ownership executes before the existing incident candidate post-step.
7. Incident candidates do not yet consume routing ownership evidence.
8. EndpointSlice collection status is explicit and current.
9. Pod and ReplicaSet source modes report `SELECTIVE_GET_PROJECTED` and their exact requested/executed/skipped counts.
10. GET bounds remain:

```text
max Pod GETs:        500
max ReplicaSet GETs: 250
```

11. Bound exhaustion or failed exact observation becomes `PARTIAL`/`UNKNOWN`, not absence.
12. Exact NotFound is the only failed exact-read case that can establish absence for that exact target.
13. Pod-backed routes resolve only through targetRef plus ownerReference chains.
14. Deployment routes use Pod -> ReplicaSet -> Deployment controller owner references, never Pod-name parsing.
15. StatefulSet/DaemonSet direct controller owner references can resolve without ReplicaSet inference.
16. Non-Pod targetRefs remain explicitly non-Pod; they are not forced into workload ownership.
17. `Service/monitoring/loki-headless` is inspected specifically because selector inference was previously ambiguous.
18. Current Service-scoped `kube-prom-stack-kubelet` incident candidates are inspected specifically to determine whether their actual EndpointSlice targets are Pods, Nodes, or another object class.
19. Endpoint addresses/IPs, Pod IPs, specs, status payloads, labels, annotations, environment/container configuration, Secret references, UIDs, logs, and service-account tokens are absent from the persisted artifact.
20. `mutation_allowed=false`.
21. No previous selector ambiguity is considered resolved until the live artifact supports the stronger relation.

## Expected interpretation

A `NON_POD_ROUTING` result is valid evidence, not a failed test.

A `PARTIAL` source can be acceptable if the reason is explicit and bounded, but the missing routes must remain unknown and downstream integration must remain blocked for those paths.

A Service can legitimately resolve to multiple workload controllers if live EndpointSlices actually route to Pods owned by different controllers. That is stronger evidence than a selector ambiguity but is still not a business-ownership statement.

The gate does not require every Service to have an EndpointSlice or every endpoint to target a Pod.

## Trust boundary

This slice observes routing/ownership metadata only. It does not ingest Pod content or logs and does not change existing incident reasoning until a separate integration slice passes its own live gate.
