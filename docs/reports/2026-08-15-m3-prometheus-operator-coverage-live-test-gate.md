# Milestone 3 Prometheus Operator Coverage Live Test Gate — 2026-08-15

## Status

Accepted on the real `k3s-main` management-host evidence loop.

## Scope

Validate the Prometheus Operator configuration-coverage slice against the real `k3s-main` cluster and enrich the existing workload operational inventory without claiming runtime scrape health.

## Live acceptance evidence

Repository regression suite passed:

```text
89 passed in 0.71s
```

The normal observer completed successfully and continued to refresh Git declared state before the Kubernetes evidence run. Git source observation remained `COMPLETE` at revision `5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4`.

Observer RBAC was verified from the dedicated runtime identity:

```text
list prometheuses.monitoring.coreos.com --all-namespaces      yes
list servicemonitors.monitoring.coreos.com --all-namespaces  yes
list podmonitors.monitoring.coreos.com --all-namespaces      yes
list secrets --all-namespaces                                no
create servicemonitors.monitoring.coreos.com -n monitoring   no
```

No mutating Kubernetes permission or Secret access was introduced.

The live coverage source was `COMPLETE`, `mutation_allowed=false`, with these current observations:

```text
Prometheus:      1
ServiceMonitor: 11
PodMonitor:      0
Namespace:      25 supporting metadata observations
Service:        78 supporting metadata observations
```

Prometheus selection evaluation found 9 selected ServiceMonitors. Workload coverage matched the operational inventory cardinality exactly:

```text
coverage workloads: 68
inventory entities: 68
counts match: true
```

Current coverage classifications were:

```text
OPERATOR_MONITOR_MATCH:    7
NO_OPERATOR_MONITOR_MATCH: 61
UNKNOWN:                   0
```

All 7 positive workload paths retained the full ServiceMonitor inference chain:

```text
PROMETHEUS_MONITOR_SELECTION_INFERENCE
SERVICEMONITOR_SERVICE_SELECTOR_INFERENCE
SERVICE_SELECTOR_MATCH_INFERENCE
```

Each sampled path retained five supporting evidence IDs, including selector-support metadata evidence where needed. Real examples included CoreDNS, Grafana, kube-state-metrics, Prometheus Operator, node-exporter, Alertmanager, and Prometheus workloads.

No PodMonitor existed in the current cluster observation, so no positive PodMonitor path was expected or claimed.

No coverage unknowns or collector errors were present in this run.

Sensitive-field guard found none of the forbidden authentication, TLS, Secret-payload, password, or private-key fields in the persisted coverage artifact.

The workload inventory was upgraded to version `0.2`, retained `mutation_allowed=false`, and preserved the existing Git drift/topology/history context while adding observability coverage.

## Interpretation

`OPERATOR_MONITOR_MATCH` means a current evidence-backed Prometheus Operator configuration path was derived. It does not mean the target is currently up, being scraped successfully, or emitting expected metrics.

`NO_OPERATOR_MONITOR_MATCH` means no ServiceMonitor/PodMonitor path was derived inside the current Prometheus Operator evidence scope. It is not equivalent to `UNMONITORED`; other scrape configuration may exist outside this slice.

Actual target health, scrape success, metric freshness, and alert state require authoritative Prometheus/Alertmanager runtime evidence and remain outside this Milestone 3 acceptance.

## Trust boundary

This acceptance validates configuration coverage only. Prometheus remains authoritative for target and metric health. The inventory remains a derived projection over evidence rather than a replacement monitoring system or CMDB source of truth.
