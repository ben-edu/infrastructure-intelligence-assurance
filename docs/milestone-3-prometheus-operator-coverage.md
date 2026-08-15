# Milestone 3 — Prometheus Operator Coverage

## Goal

Connect workload inventory entities to current Prometheus Operator configuration evidence without claiming runtime scrape health.

## Flow

```text
Kubernetes API
  -> Prometheus / ServiceMonitor / PodMonitor observation
  -> narrow Namespace / Service label observations for selector provenance
  -> selector and namespace evaluation
  -> workload configuration coverage
  -> observability-coverage.json / .md
  -> workload inventory enrichment
```

## What this slice answers

For a workload:

- Is there a current Prometheus Operator monitor path that can be derived?
- Which Prometheus resource selects the monitor object?
- Is the path based on ServiceMonitor or PodMonitor?
- Which evidence IDs support monitor, Namespace/Service selector, and workload attribution decisions?
- Is coverage evaluation complete or partial?

## What this slice does not answer

It does not answer:

- whether Prometheus currently has a target for the workload;
- whether the target is `UP`;
- whether scrapes are succeeding;
- whether expected metrics are present;
- whether alert rules cover the workload;
- whether alerts are firing;
- whether another monitoring system covers the workload.

Those questions require authoritative runtime observability evidence and belong to later slices.

## Coverage states

```text
OPERATOR_MONITOR_MATCH
NO_OPERATOR_MONITOR_MATCH
UNKNOWN
```

`NO_OPERATOR_MONITOR_MATCH` is deliberately scoped. It is not equivalent to `UNMONITORED`.

Malformed or unsupported selector content is not ignored in a way that could broaden selection. Unsafe selector evaluation becomes `UNKNOWN`/`PARTIAL`.

## Persisted artifacts

```text
/var/lib/infra-assurance/evidence/observability-coverage.json
/var/lib/infra-assurance/evidence/observability-coverage.md
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/inventory.md
```

The coverage artifact includes narrow supporting Namespace/Service metadata observations when their labels are needed for selector reasoning. It does not persist raw Namespace, Service, or monitor objects.

## Permissions

The existing Kubernetes observer gains only `get/list/watch` access to:

```text
prometheuses.monitoring.coreos.com
servicemonitors.monitoring.coreos.com
podmonitors.monitoring.coreos.com
```

Its existing Namespace and Service read access is reused. Secrets remain inaccessible and no mutating Kubernetes verb is introduced.

## Sensitive-data handling

Monitor endpoint authentication and TLS configuration are not projected. Raw monitor manifests are not persisted.

## Acceptance

Live acceptance should verify:

1. tests pass;
2. Kubernetes observer remains read-only;
3. Prometheus Operator CRDs are observed successfully;
4. coverage artifact is generated;
5. workload count matches inventory count;
6. real selector paths retain supporting evidence IDs;
7. configuration coverage is not labeled as scrape health;
8. failed monitor observation produces `UNKNOWN`, never a false absence claim;
9. inventory CLI can filter by observability coverage status without new infrastructure reads;
10. prohibited authentication/Secret fields are absent from the persisted coverage artifact.
