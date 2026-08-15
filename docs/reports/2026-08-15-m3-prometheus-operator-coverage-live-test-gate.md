# Milestone 3 Prometheus Operator Coverage Live Test Gate — 2026-08-15

## Status

Pending management-host live acceptance.

## Scope

Validate the Prometheus Operator configuration-coverage slice against the real `k3s-main` cluster and enrich the existing workload operational inventory without claiming runtime scrape health.

## Required acceptance evidence

1. Repository tests pass.
2. Existing Kubernetes and Git observers remain healthy.
3. Observer RBAC gains only `get/list/watch` for `Prometheus`, `ServiceMonitor`, and `PodMonitor` resources in `monitoring.coreos.com`.
4. Secret access remains denied and no Kubernetes write verb is introduced.
5. The normal observer emits:

```text
/var/lib/infra-assurance/evidence/observability-coverage.json
/var/lib/infra-assurance/evidence/observability-coverage.md
```

6. `mutation_allowed` remains `false` in both coverage and inventory artifacts.
7. Coverage workload count matches the workload inventory entity count from the same run.
8. Prometheus, ServiceMonitor, and PodMonitor configuration observations are explicit and traceable by evidence ID.
9. A positive ServiceMonitor coverage path retains all inference boundaries:

```text
PROMETHEUS_MONITOR_SELECTION_INFERENCE
SERVICEMONITOR_SERVICE_SELECTOR_INFERENCE
SERVICE_SELECTOR_MATCH_INFERENCE
```

10. A positive PodMonitor coverage path retains:

```text
PROMETHEUS_MONITOR_SELECTION_INFERENCE
PODMONITOR_TEMPLATE_LABEL_INFERENCE
```

11. A failed or unavailable monitor observation produces `UNKNOWN`/`PARTIAL` rather than a false no-monitor claim.
12. `NO_OPERATOR_MONITOR_MATCH` is presented only as absence of a derived Prometheus Operator monitor path in the current scope, not as proof that the workload is unmonitored.
13. Persisted coverage excludes authentication/TLS/Secret-bearing monitor configuration, including bearer token fields, basic-auth references, passwords, OAuth configuration, TLS configuration, raw Secret payloads, and private keys.
14. The workload inventory attaches observability coverage without removing existing Git drift, topology ambiguity, history, or evidence references.
15. `iia-inventory list --observability-status ...` filters the generated artifact without making new infrastructure reads.

## Expected live interpretation

A non-zero count of Prometheus Operator resources is expected only if the cluster currently contains those CRDs and objects. The acceptance does not require a specific monitor count. If the source is `PARTIAL` or `FAILED_TO_OBSERVE`, the failure must be explained and must not be converted into absence.

Similarly, a workload with `OPERATOR_MONITOR_MATCH` is not automatically considered healthy. Actual target status, scrape success, metric freshness, and alert state require live Prometheus/Alertmanager evidence and remain outside this Milestone 3 slice.

## Trust boundary

This acceptance validates configuration coverage only. Prometheus remains authoritative for target and metric health. The inventory remains a derived projection over evidence rather than a replacement monitoring system or CMDB source of truth.
