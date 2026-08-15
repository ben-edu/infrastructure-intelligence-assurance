# Milestone 4 Prometheus Runtime Intelligence Live Test Gate — 2026-08-15

## Status

Accepted.

The third management-host run passed the final corrected live gate. The first two runs remain documented because they validated failure semantics and progressively refined the least-privilege Service-proxy boundary.

## Scope

Validate the first Milestone 4 runtime observability slice against the existing Prometheus instance without modifying Prometheus, Kubernetes workloads, or alerting configuration.

## Final accepted run

Repository regression suite:

```text
102 passed in 0.74s
```

The normal observer service completed with `status=0/SUCCESS`; Git declared-state observation remained `COMPLETE` at revision `5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4`.

### Exact Service-proxy authorization

The observer authorization boundary was verified as:

```text
kube-prom-stack-prometheus:9090 proxy / monitoring = yes
not-authorized:9090 proxy / monitoring             = no
kube-prom-stack-prometheus:9090 proxy / default    = no
unqualified kube-prom-stack-prometheus / monitoring = no
list Secrets                                        = no
```

The Role is therefore constrained to the actual port-qualified Prometheus Service-proxy identity used by the runtime.

### Prometheus API observation

Both read-only API probes succeeded:

```text
targets API: success
active targets: 21
alerts API: success
active alerts: 11
```

Normalized runtime source:

```text
status: COMPLETE
mutation_allowed: false
```

### Target evidence

```text
targets_total: 21
targets_up: 21
targets_down: 0
targets_unknown: 0
targets_attributed_to_workloads: 11
targets_unattributed: 10
```

Seven workload entities received `PROMETHEUS_TARGETS_UP`; 61 received `NO_RUNTIME_SIGNAL_MATCH`.

`PROMETHEUS_TARGETS_UP` remains signal-scoped scrape evidence and is not presented as generic application health.

### Active alert evidence

```text
active_alerts_total: 11
active_alerts_firing: 11
active_alerts_pending: 0
active_alerts_unknown: 0
alerts_attributed_to_workloads: 0
alerts_unattributed: 11
```

The implementation did not force attribution for these alerts. Current alert labels identify Services such as `kube-prom-stack-kubelet` for which no current Service-to-workload controller inference exists in the corresponding scope. The alerts remain valid operational evidence while workload attribution remains unresolved.

This is preferred to inventing controller ownership.

### Explicit unresolved mappings

The runtime emitted evidence-backed unknowns such as:

```text
PROMETHEUS_TARGET_WORKLOAD_MAPPING_UNRESOLVED
PROMETHEUS_ALERT_WORKLOAD_MAPPING_UNRESOLVED
```

Examples include the Kubernetes API Service and kubelet monitoring Services, where no current controller-level selector inference exists.

These unknowns do not downgrade the Prometheus source itself; API observation was complete.

### Cardinality and sensitive-data gate

```text
runtime workloads: 68
inventory entities: 68
cardinality match: true
forbidden projected keys: none
raw URL markers: false
```

No raw scrape URLs, discovered labels, alert annotations, metric samples, credentials, Secret values, or other forbidden projected fields were found in the persisted runtime artifact.

## Earlier live attempts

### Attempt 1

Tests passed, but bootstrap used an incorrect `kubectl auth can-i get services/proxy` check. That syntax did not safely test the proxy subresource. The gate was corrected to use `--subresource=proxy`.

### Attempt 2

Tests passed and the corrected subresource checks succeeded for the unqualified Service name, but the real proxy request was denied because Kubernetes authorized the actual port-qualified resource name:

```text
kube-prom-stack-prometheus:9090
```

Runtime failure semantics were correct during that failure:

```text
source.status = FAILED_TO_OBSERVE
runtime workload UNKNOWN = 68
runtime/inventory cardinality = 68/68
PROMETHEUS_PROXY_FORBIDDEN for targets and alerts
forbidden projected keys = none
raw URL markers = false
```

No false zero-target, zero-alert, or healthy-workload conclusion was produced.

The Role was then narrowed to the exact port-qualified proxy identity rather than broadened.

## Acceptance conclusion

Accepted because:

1. repository tests pass;
2. Prometheus targets and alert APIs are observable through the reviewed read-only path;
3. proxy authorization is constrained to one port-qualified Service identity in one namespace;
4. Secret access and Kubernetes mutation remain denied;
5. source failures remain explicit and produce `UNKNOWN` rather than false absence;
6. current target and alert evidence is normalized without raw/sensitive payload persistence;
7. workload attribution occurs only when the existing evidence-backed Service-to-controller path supports it;
8. unresolved mappings remain explicit;
9. runtime/inventory cardinality is consistent;
10. `mutation_allowed=false` remains intact.

## Trust boundary

Prometheus remains authoritative for scrape-target and alert-evaluation state. The platform stores a narrow current projection and does not replace Prometheus or Alertmanager.

A Prometheus target reporting `UP` proves scrape-target reachability at the observed time, not application correctness or user-visible health.

Active Prometheus alerts remain operational evidence even when workload attribution is unresolved. The platform must not manufacture ownership merely to make alerts fit the workload inventory model.
