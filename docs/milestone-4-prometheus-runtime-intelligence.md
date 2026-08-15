# Milestone 4 — Prometheus Runtime Intelligence

## Goal

Consume authoritative current Prometheus target and alert state, relate it to existing workload inventory entities, and preserve uncertainty and inference boundaries.

This is the first Milestone 4 Observability Intelligence vertical slice.

## Source

The first runtime source is the existing Prometheus instance exposed through:

```text
monitoring/kube-prom-stack-prometheus:9090
```

The observer reaches it through the Kubernetes API Service proxy using the existing observer identity plus a namespace-scoped read-only Role.

The only Prometheus API reads in this slice are:

```text
/api/v1/targets?state=active
/api/v1/alerts
```

## Persisted artifacts

```text
/var/lib/infra-assurance/evidence/prometheus-runtime.json
/var/lib/infra-assurance/evidence/prometheus-runtime.md
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/inventory.md
```

The workload inventory is enriched after Prometheus Operator configuration coverage is attached.

## Target evidence

The runtime observer stores a narrow target projection:

- `UP | DOWN | UNKNOWN`;
- allowlisted Kubernetes/monitoring labels;
- last scrape timestamp;
- scrape duration;
- sanitized scrape error code;
- evidence ID and expiry.

It does not store raw scrape URLs, discovered labels, raw errors, metric samples, credentials, or Secret values.

## Alert evidence

The observer stores only active Prometheus alert state:

```text
FIRING
PENDING
UNKNOWN
```

Only allowlisted labels such as alert name, severity, namespace, Service, job, Pod, and container are retained.

Annotations are excluded.

## Workload states

Each workload receives one runtime signal state:

```text
PROMETHEUS_TARGETS_UP
PROMETHEUS_TARGET_DOWN
ACTIVE_ALERT
NO_RUNTIME_SIGNAL_MATCH
UNKNOWN
```

These are not generic application-health states.

A target reporting `UP` proves only that Prometheus successfully scraped that target at the observed time.

## Attribution

Target or alert labels containing `namespace` + `service` are connected to the Kubernetes Service identity.

The Service-to-workload relationship reuses the existing topology inference:

```text
SERVICE_SELECTOR_MATCH_INFERENCE
```

Runtime attribution therefore remains explicit inference rather than direct Pod ownership proof.

## Source failure

Targets and alerts are queried separately.

```text
both reads succeed -> COMPLETE
one read fails     -> PARTIAL
both reads fail    -> FAILED_TO_OBSERVE
```

A partial or failed source makes workload runtime state `UNKNOWN`; it never becomes a false no-target/no-alert claim.

## Permissions

New permission:

```text
Role namespace: monitoring
resource: services/proxy
verb: get
```

The observer still cannot:

- list Kubernetes Secrets;
- mutate Kubernetes resources;
- proxy Services in other namespaces through this Role.

## Querying

The generated inventory remains queryable without additional infrastructure reads:

```bash
sudo -u infra-assurance iia-inventory list \
  --runtime-state PROMETHEUS_TARGET_DOWN

sudo -u infra-assurance iia-inventory list \
  --runtime-state ACTIVE_ALERT

sudo -u infra-assurance iia-inventory list \
  --runtime-state PROMETHEUS_TARGETS_UP
```

## Deferred Milestone 4 work

- Alertmanager delivery/silence/inhibition state;
- rule and metric freshness intelligence;
- incident grouping;
- Loki correlation;
- OpenTelemetry traces;
- Kubernetes events;
- Jenkins/Git deployment-event correlation;
- confidence-scored root-cause hypotheses.
