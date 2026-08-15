# Milestone 4 Prometheus Runtime Intelligence Live Test Gate — 2026-08-15

## Status

Pending final corrected management-host live acceptance.

Two live attempts have now validated the failure semantics and progressively tightened the Service-proxy authorization boundary. M4 is not accepted yet.

## Scope

Validate the first Milestone 4 runtime observability slice against the existing Prometheus instance without modifying Prometheus, Kubernetes workloads, or alerting configuration.

## First live attempt

Repository regression suite passed:

```text
102 passed in 0.72s
```

The observer systemd service completed with `status=0/SUCCESS`; Git declared-state observation remained `COMPLETE` at revision `5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4`.

Bootstrap stopped because the original authorization check used `kubectl auth can-i get services/proxy`, which tests `TYPE/NAME` rather than safely proving the proxy subresource. The gate was corrected to use `--subresource=proxy`.

## Second live attempt

Repository regression suite passed again:

```text
102 passed in 0.65s
```

Bootstrap authorization checks reported:

```text
Prometheus Service / monitoring : yes
Other Service / monitoring      : no
Prometheus Service / default    : no
Secrets                         : no
Create Deployment               : no
```

However, the real Prometheus API proxy request failed with:

```text
services "kube-prom-stack-prometheus:9090" is forbidden
```

The runtime handled that failure correctly:

```text
source.status = FAILED_TO_OBSERVE
runtime workload UNKNOWN = 68
runtime/inventory cardinality = 68/68
source errors = PROMETHEUS_PROXY_FORBIDDEN for targets and alerts
forbidden projected keys = none
raw URL markers present = false
```

No false zero-target, zero-alert, or healthy-workload conclusion was produced.

### Root cause

The API server proxy URL uses a port-qualified Service name:

```text
kube-prom-stack-prometheus:9090
```

Kubernetes Service proxy URLs explicitly support `<service_name>:<port_name-or-number>`. RBAC `resourceNames` matches the resource name carried by the authorization request, so restricting the rule to only `kube-prom-stack-prometheus` does not authorize the actual port-qualified proxy request.

### Final correction

The reviewed Role is now pinned to the exact proxy resource name used by the runtime:

```text
namespace: monitoring
resource: services/proxy
resourceName: kube-prom-stack-prometheus:9090
verb: get
```

Bootstrap is also pinned to the exact source tuple:

```text
monitoring / kube-prom-stack-prometheus / 9090
```

and verifies:

```text
get services/kube-prom-stack-prometheus:9090 --subresource=proxy -n monitoring = yes
get services/not-authorized:9090 --subresource=proxy -n monitoring = no
get services/kube-prom-stack-prometheus:9090 --subresource=proxy -n default = no
get services/kube-prom-stack-prometheus --subresource=proxy -n monitoring = no
list secrets --all-namespaces = no
```

## Required final acceptance evidence

1. Repository tests pass after the port-qualified authorization correction.
2. Existing Git, Kubernetes, history, drift, topology, configuration coverage, and inventory outputs remain healthy.
3. The exact Prometheus port-qualified Service proxy request succeeds.
4. Unrelated Service proxy access in `monitoring` remains denied.
5. Cross-namespace proxy access remains denied.
6. The unqualified Prometheus Service proxy name remains denied, proving the rule is constrained to the actual port-qualified request.
7. Secret access and Kubernetes mutation remain denied.
8. Prometheus targets and alerts APIs return successful observations.
9. Runtime workload cardinality matches inventory cardinality from the same run.
10. Raw scrape URLs, discovered labels, alert annotations, metric samples, credentials, Secret values, and arbitrary labels remain absent from persisted runtime evidence.
11. Any real down targets or active alerts remain visible as evidence and are not treated as test failures.
12. `mutation_allowed` remains `false`.

## Trust boundary

Prometheus remains authoritative for scrape-target and alert-evaluation state. The platform stores a narrow current evidence projection and does not replace Prometheus or Alertmanager.

The two failed live attempts are accepted evidence about the integration boundary, not hidden implementation noise: the first exposed incorrect authorization-test syntax; the second exposed the port-qualified resource name used by the real Service proxy request.
