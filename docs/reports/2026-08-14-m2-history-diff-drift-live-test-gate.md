# Milestone 2 History / Diff / Drift Live Test Gate — 2026-08-14

## Status

Pending management-host acceptance.

## Scope

Validate the first durable Milestone 2 slice against the live `k3s-main` observer runtime.

The acceptance test remains read-only against Kubernetes.

## Required acceptance evidence

1. The complete repository test suite passes from the management-host checkout.
2. Bootstrap refresh succeeds without adding Kubernetes RBAC permissions.
3. Existing Milestone 1 latest evidence is migrated into history when history is initially empty.
4. A new collection produces at least two immutable history snapshots.
5. `iia-k8s-history status` reports bounded retention and latest snapshot metadata.
6. `diff.json` and `diff.md` compare the latest two snapshots.
7. No resource is classified as removed from failed, stale, partial, or missing current collection evidence.
8. `drift.json` explicitly reports `DECLARED_STATE_UNAVAILABLE` if no normalized Git-declared evidence has been configured yet.
9. `change-context.json` and `change-context.md` remain compact and set `mutation_allowed=false`.
10. No credential, kubeconfig content, Secret payload, sensitive connection string, or secret-bearing environment value is written to history or projections.

## Expected initial drift result

A real Git source candidate has been identified in `ben-edu/api-cluster-infra`, but automated private-repository ingestion is intentionally not configured in this first runtime acceptance.

Therefore the expected initial drift status is:

```text
DECLARED_STATE_UNAVAILABLE
```

This is an explicit unknown source state, not an assertion of zero drift.

## Trust statement

The history store persists only normalized evidence already allowed by the Milestone 0/1 collector boundary. It does not archive raw Kubernetes API payloads.
