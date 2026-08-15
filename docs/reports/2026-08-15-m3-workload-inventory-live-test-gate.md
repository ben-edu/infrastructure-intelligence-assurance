# Milestone 3 Workload Operational Inventory Live Test Gate — 2026-08-15

## Status

Accepted on `mgmt-automation` against the live `k3s-main` evidence loop.

## Scope

Validate the first workload-centric Dynamic Operational Inventory / CMDB projection against the real `k3s-main` evidence loop.

## Acceptance evidence

Repository tests passed:

```text
76 passed in 0.67s
```

The existing Kubernetes and Git observers remained healthy. The Git observer reported `COMPLETE` at revision:

```text
5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
```

No Kubernetes RBAC permission was added. The existing read-only checks remained in bootstrap.

The normal scheduled observer emitted:

```text
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/inventory.md
```

and installed:

```text
/usr/local/bin/iia-inventory
```

Current live inventory summary:

```text
workloads_total: 68
namespaces_total: 19
declared_workloads: 9
workloads_in_sync: 9
workloads_outside_declared_scope: 59
workloads_with_attention: 3
service_links: 77
ingress_route_candidates: 26
pvc_links: 18
related_drift_subjects: 1
workloads_changed_in_latest_diff: 0
```

The inventory contained exactly 68 entities for 68 currently observed Deployment, StatefulSet, and DaemonSet resources.

`mutation_allowed` remained `false`.

`Deployment/validation/nginx-validation` was correctly represented with:

```text
observed freshness: CURRENT
declared coverage: DECLARED
direct comparison: IN_SYNC
service relationship basis: SELECTOR_MATCH_INFERENCE
ingress route basis: COMPOSED_INFERENCE
```

The related `Ingress/validation/nginx-validation` host drift was surfaced as attention on the workload without changing the workload's direct `IN_SYNC` comparison.

The existing `Service/monitoring/loki-headless` ambiguity was surfaced on both related workload entities:

```text
DaemonSet/monitoring/loki-canary
StatefulSet/monitoring/loki
```

with severity `AMBIGUOUS`. The inventory did not choose one controller as authoritative.

Workloads outside the configured Git scope remained `OUTSIDE_DECLARED_SCOPE`; they were not automatically classified as drift.

The sensitive-key guard found no projected keys from the prohibited set:

```text
env
envFrom
stringData
secret_payload
password
private_key
privateKey
```

The read-only `iia-inventory` CLI successfully returned the inventory summary and attention-only workload list without additional infrastructure reads.

## Acceptance conclusion

The workload-centric operational inventory is accepted as the first Dynamic Operational Inventory / CMDB slice. It reduces operator lookup cost by joining existing evidence while preserving the trust boundaries of the underlying Kubernetes, Git, topology, history, and drift artifacts.

## Trust boundary

This acceptance validates a derived projection only. Kubernetes evidence, Git declared evidence, topology, history, and drift remain the authoritative supporting artifacts. Service-to-workload links remain selector-based inferences, and composed Ingress route candidates do not prove current EndpointSlice or Pod routing.