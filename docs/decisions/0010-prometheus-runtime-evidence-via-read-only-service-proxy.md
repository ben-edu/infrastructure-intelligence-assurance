# ADR 0010 — Prometheus Runtime Evidence via Read-Only Kubernetes Service Proxy

## Status

Accepted for Milestone 4 implementation pending live validation.

## Context

Milestone 3 established two different layers of infrastructure knowledge:

1. current Kubernetes / Git / history / topology evidence;
2. Prometheus Operator configuration coverage.

The second layer answers whether a workload has an evidence-backed `ServiceMonitor` or `PodMonitor` configuration path. It deliberately does not answer whether Prometheus is currently scraping the target, whether the target is up, or whether an alert is active.

Milestone 4 must begin consuming authoritative runtime observability signals without replacing Prometheus or Alertmanager.

## Decision

Add a narrow Prometheus runtime observer that reads the existing Prometheus HTTP API through the Kubernetes API Service proxy.

The first source is explicit:

```text
namespace: monitoring
service: kube-prom-stack-prometheus
port: 9090
proxy resource name: kube-prom-stack-prometheus:9090
```

The observer reads only:

```text
GET /api/v1/targets?state=active
GET /api/v1/alerts
```

Artifacts:

```text
/var/lib/infra-assurance/evidence/prometheus-runtime.json
/var/lib/infra-assurance/evidence/prometheus-runtime.md
```

No Prometheus configuration or Kubernetes object is modified.

## Kubernetes access boundary

The observer ServiceAccount receives one additional Role in `monitoring`:

```text
apiGroup: core
resource: services/proxy
resourceName: kube-prom-stack-prometheus:9090
verb: get
namespace: monitoring
```

This permission is not added to the cluster-wide observer ClusterRole.

Kubernetes Service proxy URLs support a port-qualified service-name segment such as `<service_name>:<port_name-or-number>`. The API authorization request for the runtime URL therefore carries the name `kube-prom-stack-prometheus:9090`; `resourceNames` must match that actual request identity rather than only the underlying Service object name.

Bootstrap is pinned to the reviewed source tuple `monitoring/kube-prom-stack-prometheus:9090` and verifies:

```text
get services/kube-prom-stack-prometheus:9090 --subresource=proxy -n monitoring = yes
get services/not-authorized:9090 --subresource=proxy -n monitoring = no
get services/kube-prom-stack-prometheus:9090 --subresource=proxy -n default = no
get services/kube-prom-stack-prometheus --subresource=proxy -n monitoring = no
list secrets --all-namespaces = no
```

No `create`, `update`, `patch`, or `delete` capability is introduced.

Two live gates refined this boundary before acceptance. The first exposed incorrect `kubectl auth can-i get services/proxy` syntax; the second proved that an unqualified `resourceNames: [kube-prom-stack-prometheus]` rule does not authorize the real port-qualified proxy request, which the API server reported as resource name `kube-prom-stack-prometheus:9090`.

Changing the configured Prometheus namespace, Service, or port requires a reviewed RBAC update so runtime configuration cannot silently become broader than the authorization contract.

## Persisted target evidence

The observer does not persist the raw Prometheus target payload.

For each active target it retains only:

- generated target ID;
- evidence ID;
- observation and expiry timestamps;
- normalized `UP | DOWN | UNKNOWN` health;
- allowlisted labels: `namespace`, `service`, `job`, `endpoint`, `pod`, `container`;
- last scrape timestamp;
- last scrape duration;
- sanitized scrape error code.

It does not persist:

- `scrapeUrl`;
- `globalUrl`;
- `discoveredLabels`;
- arbitrary labels;
- raw error text;
- credentials;
- Secret values;
- metric series or samples.

The raw scrape URL may participate only in an in-memory hash used to distinguish target IDs; it is never serialized.

## Persisted alert evidence

The observer reads active alerts from Prometheus and retains only:

- generated alert ID;
- evidence ID;
- `FIRING | PENDING | UNKNOWN` state;
- active timestamp;
- allowlisted labels: `alertname`, `severity`, `namespace`, `service`, `job`, `pod`, `container`.

Prometheus alert annotations and arbitrary labels are excluded because they are free-form and can carry sensitive or unnecessarily verbose data.

This slice reads Prometheus alert evaluation state. Alertmanager delivery, grouping, silencing, inhibition, receiver, and notification state remain separate future evidence.

## Workload attribution

When a Prometheus target or alert contains both `namespace` and `service` labels, the observer can associate it with a Kubernetes Service identity.

The Service is then related to workload controllers using the existing topology relation:

```text
SERVICE_SELECTOR_MATCH_INFERENCE
```

Attribution basis remains explicit:

```text
Prometheus target:
PROMETHEUS_RUNTIME_TARGET_SERVICE_LABEL
+ SERVICE_SELECTOR_MATCH_INFERENCE

Prometheus alert:
PROMETHEUS_ACTIVE_ALERT_SERVICE_LABEL
+ SERVICE_SELECTOR_MATCH_INFERENCE
```

The platform does not claim that this proves live Pod ownership or endpoint routing.

## Workload runtime states

A workload receives one of:

```text
PROMETHEUS_TARGETS_UP
PROMETHEUS_TARGET_DOWN
ACTIVE_ALERT
NO_RUNTIME_SIGNAL_MATCH
UNKNOWN
```

`PROMETHEUS_TARGETS_UP` means matched Prometheus targets reported `up`; it is not generic application-health proof.

`PROMETHEUS_TARGET_DOWN` means at least one attributed scrape target reported `down`; it is not automatically a root-cause conclusion.

`ACTIVE_ALERT` means an attributed Prometheus alert is firing or pending.

`NO_RUNTIME_SIGNAL_MATCH` means this slice found no target or active alert it could attribute to the workload; it does not prove the workload is unmonitored, healthy, or alert-free outside the modeled path.

`UNKNOWN` means runtime evidence was not safely observable or attributable enough for the modeled state.

## Failure semantics

Targets and alerts are observed independently.

If both API reads fail:

```text
source.status = FAILED_TO_OBSERVE
```

If one read fails:

```text
source.status = PARTIAL
```

Workload runtime state becomes `UNKNOWN` when the source is incomplete. A failed Prometheus read is never converted into a false claim of zero targets or zero alerts.

An individual target with an unrecognized health value creates target-level `UNKNOWN` evidence; it does not automatically downgrade an otherwise successful Prometheus API source observation.

The second live gate explicitly validated this behavior: both proxy calls were forbidden, the source became `FAILED_TO_OBSERVE`, and all 68 workload states became `UNKNOWN` while runtime/inventory cardinality remained consistent.

## Consequences

Positive:

- authoritative Prometheus runtime evidence is consumed rather than inferred health;
- configuration coverage and runtime state remain distinct;
- runtime signals attach to the existing workload inventory;
- raw Prometheus payloads and sensitive/free-form fields are not persisted;
- failed observation remains explicit;
- proxy RBAC is constrained to one port-qualified Service proxy identity in one namespace;
- the existing five-minute loop can refresh runtime context unattended.

Tradeoffs:

- Kubernetes Service proxy GET permission is stronger than ordinary object list/get even though it is namespaced, exact-name constrained, and non-mutating;
- the Prometheus source namespace, Service, and port are intentionally pinned to the reviewed RBAC rule;
- Service-based workload attribution still relies on controller selector inference;
- targets without usable `namespace` + `service` labels remain unattributed;
- active Prometheus alerts are not equivalent to Alertmanager notification state;
- a target reporting `up` is not application-health proof.

## Deferred

- Alertmanager active/silenced/inhibited/receiver evidence;
- Prometheus rule and metric freshness analysis;
- Loki incident-log correlation;
- OpenTelemetry traces;
- Kubernetes event correlation;
- Jenkins/Git deployment-event correlation;
- cross-signal incident grouping and root-cause hypotheses.
