# Milestone 4 Alertmanager Correlation Live Test Gate — 2026-08-15

## Status

Accepted on `mgmt-automation`.

## Pre-implementation discovery

Observed in namespace `monitoring`:

```text
Service/alertmanager-operated
  9093 http-web
  9094 tcp-mesh
  9094 udp-mesh

Service/kube-prom-stack-alertmanager
  9093 http-web
  8080 reloader-web
```

Prometheus `/api/v1/alertmanagers` returned one active Alertmanager endpoint at port 9093. The implementation uses the stable `Service/kube-prom-stack-alertmanager:9093`, not an observed Pod IP or `alertmanager-operated`.

## Repository and runtime gate

Repository regression suite:

```text
112 passed in 0.84s
```

The observer service completed with `status=0/SUCCESS`. Git declared-state observation remained `COMPLETE` with 27 normalized records at revision:

```text
5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
```

The systemd oneshot returned to `inactive (dead)` after success, which is expected.

## Exact proxy authorization

Accepted authorization results:

```text
Prometheus exact proxy             : yes
Alertmanager exact proxy           : yes
alertmanager-operated proxy        : no
Unqualified Alertmanager proxy     : no
Alertmanager proxy / default       : no
Secrets                            : no
Create Deployment                  : no
```

Therefore the additional Alertmanager boundary is exactly:

```text
namespace: monitoring
resource: services/proxy
resourceName: kube-prom-stack-alertmanager:9093
verb: get
```

No `alertmanager-operated` proxy, cross-namespace proxy, Secret access, or Kubernetes mutation is authorized by this slice.

## Live Alertmanager API evidence

The observer identity successfully read:

```text
GET /api/v2/alerts?active=true&silenced=true&inhibited=true&unprocessed=true
GET /api/v2/silences?active=true&expired=false&pending=true
```

Live API summary:

```text
alerts: 11
Alertmanager raw states:
  suppressed: 9
  active: 2
normalized handling:
  inhibited: 9
  active: 2
silences: 0
```

Alertmanager source status:

```text
COMPLETE
```

Prometheus source remained independently:

```text
COMPLETE
```

## Prometheus / Alertmanager correlation

All 11 current Alertmanager alerts had one unique match in the current normalized Prometheus alert projection:

```text
MATCHED: 11
UNRESOLVED: 0
AMBIGUOUS: 0
```

This is correlation between two authoritative alert evidence sources. It is not workload ownership.

## Alert attention projection

Current attention records:

```text
attention_total: 11
active: 2
inhibited: 9
silenced: 0

scope_service: 6
scope_namespace: 3
scope_platform: 2
scope_workload: 0
scope_node: 0
```

The two active platform-scoped alerts were:

```text
KubeCPUOvercommit severity=warning
Watchdog severity=none
```

The inhibited records included `CPUThrottlingHigh` at Service scope and `InfoInhibitor` at Namespace scope.

No workload scope was invented. Service/namespace/platform evidence remains first-class operational attention when no supported workload ownership path exists.

## Sensitive / free-form exclusion

Accepted artifact inspection found:

```text
forbidden projected keys: none
raw URL markers: false
```

The persisted projections exclude:

- receiver names and configuration;
- free-form annotations;
- generator URLs;
- arbitrary labels such as `instance`;
- silence comments, matchers, and creator identity;
- notification payloads;
- credentials, tokens, and Secret values.

## Acceptance conclusion

The slice is accepted.

Alertmanager is authoritative for current handling/silencing/inhibition state. Prometheus remains authoritative for alert evaluation. The platform now joins those two evidence planes conservatively and emits compact operational attention without turning Service/Namespace/Platform alerts into unsupported workload claims.

`mutation_allowed=false` remains in both Alertmanager runtime and alert-attention artifacts.

## Next Milestone 4 slice

Add current Kubernetes Event evidence as a bounded, read-only operational signal and correlate it with existing workload/node/service alert attention where the object identity supports it.

The next slice should focus on recent warning/relevant events, explicit freshness, safe reason/type/object identity fields, and incident-context enrichment. It must not persist arbitrary event messages without a reviewed sanitization policy and must not infer root cause solely from event correlation.
