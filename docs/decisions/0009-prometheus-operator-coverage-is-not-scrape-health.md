# ADR 0009 — Prometheus Operator Coverage Is Not Scrape Health

## Status

Accepted for Milestone 3 implementation pending live validation.

## Context

The Dynamic Operational Inventory needs to connect workloads to observability without replacing Prometheus or prematurely entering Milestone 4 signal intelligence.

The cluster already uses Prometheus Operator resources. The Operator API defines:

- `Prometheus` resources that select monitoring configuration objects;
- `ServiceMonitor` resources that select Services/Endpoints for target discovery;
- `PodMonitor` resources that select Pods for target discovery.

These configuration objects are useful evidence for operational inventory coverage, but they do not prove that a scrape target currently exists, is up, is being scraped successfully, or is producing expected metrics.

The platform must therefore avoid collapsing configuration intent into runtime health.

## Decision

Add a read-only Prometheus Operator configuration-coverage projection to Milestone 3.

### Source scope

Observe:

```text
monitoring.coreos.com/v1 Prometheus
monitoring.coreos.com/v1 ServiceMonitor
monitoring.coreos.com/v1 PodMonitor
```

The observer also reads Kubernetes Namespace and Service metadata to evaluate label and namespace selectors. It persists only narrow label-only supporting observations for those resources so selector decisions remain traceable by evidence ID. Raw Namespace and Service objects are not copied into the observability artifact.

### RBAC

Extend the existing observer identity with read-only:

```text
get
list
watch
```

for:

```text
prometheuses
servicemonitors
podmonitors
```

The existing Namespace and Service read permissions are reused. No write verb is added.

### Selector semantics

Follow Kubernetes and Prometheus Operator selector semantics:

- Prometheus resource selector `null` selects no monitor objects;
- Prometheus resource selector `{}` selects all matching monitor objects in eligible namespaces;
- Prometheus monitor namespace selector `null` selects the Prometheus object's own namespace;
- Prometheus monitor namespace selector `{}` selects all namespaces;
- `ServiceMonitor` and `PodMonitor` target namespace selection defaults to the monitor object's namespace unless `any` or `matchNames` expands the scope;
- label selectors support `matchLabels` and `In`, `NotIn`, `Exists`, `DoesNotExist` match expressions.

A selector that cannot be normalized safely becomes unknown. Unsupported or malformed selector content is never silently discarded in a way that broadens a match.

### Coverage classification

For each workload entity:

```text
OPERATOR_MONITOR_MATCH
NO_OPERATOR_MONITOR_MATCH
UNKNOWN
```

`OPERATOR_MONITOR_MATCH` means a current Prometheus Operator configuration path was derived.

It does **not** mean:

```text
target UP
scrape successful
metrics present
alerts configured
alerts firing correctly
```

`NO_OPERATOR_MONITOR_MATCH` means only that no selected `ServiceMonitor`/`PodMonitor` path was derived inside the current Prometheus Operator scope. It does not rule out external Prometheus, static scrape configuration, `additionalScrapeConfigs`, OpenTelemetry, another monitoring stack, or other observability mechanisms.

`UNKNOWN` is used when required configuration observation or selector evaluation failed or cannot be evaluated safely.

### Relationship trust

ServiceMonitor path:

```text
Prometheus
  -> ServiceMonitor
  -> Service
  -> workload controller
```

The Prometheus-to-monitor and ServiceMonitor-to-Service selector decisions retain supporting evidence IDs, including Namespace or Service metadata observations when those labels participate in selection.

The final Service-to-workload edge remains the existing selector-based inference. Therefore a ServiceMonitor path does not prove current Pod/EndpointSlice routing.

PodMonitor path:

```text
Prometheus
  -> PodMonitor
  -> workload pod-template labels
```

The workload match is an inference from the controller pod template. It does not prove current live Pod membership or scrape target status.

### Sensitive-data boundary

The coverage observer persists only fields needed for selection reasoning:

- metadata labels required for resource/namespace selection;
- label selectors;
- namespace selectors;
- non-sensitive endpoint fields such as port/path/scheme/interval.

It excludes authentication and transport-secret configuration including bearer token fields, basic-auth references, OAuth configuration, TLS Secret references/material, credentials, private keys, and raw monitor manifests.

### Inventory integration

The workload inventory is enriched with an `observability` section and remains derived state. The supporting coverage artifact is emitted separately:

```text
/var/lib/infra-assurance/evidence/observability-coverage.json
/var/lib/infra-assurance/evidence/observability-coverage.md
```

Prometheus remains the authoritative engine for actual target and metric health.

## Deferred to Milestone 4

- Prometheus HTTP API target health;
- `up` and scrape-error evidence;
- Alertmanager firing alerts;
- PrometheusRule-to-workload reasoning;
- Loki signal integration;
- OpenTelemetry signal integration;
- incident grouping and correlation;
- health scoring.
