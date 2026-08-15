# Milestone 4 Alert Scope Validation Live Test Gate — 2026-08-15

## Status

Accepted on `mgmt-automation`.

## Purpose

Validate that alert label dimensions are no longer treated as authoritative Kubernetes resource identity unless the same-cycle Kubernetes snapshot supports that exact subject.

## Repository gate

The first test attempt exposed a real implementation defect in fallback warning provenance:

```text
KeyError: 'evidence_id'
3 failed, 153 passed in 1.56s
```

Alert-attention records carry `evidence_ids`, not a singular `evidence_id`. The validator was corrected to preserve the existing evidence list and a regression assertion was added.

The corrected full suite then passed:

```text
156 passed in 0.89s
```

Static guards also passed:

```text
RBAC changes: none
query-capable client markers: none
```

## Runtime acceptance

`bootstrap-observer.sh` completed successfully. The systemd oneshot executed in the intended order:

```text
kubernetes_runtime   status=0/SUCCESS
routing_ownership   status=0/SUCCESS
alert_scope_runtime status=0/SUCCESS
incident_runtime    status=0/SUCCESS
```

The oneshot returned to `inactive (dead)` after successful completion, as expected.

Git declared-state observation remained `COMPLETE` with 27 normalized records at revision:

```text
5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
```

A first manual artifact helper attempted to import the optional test-only `jsonschema` package under root Python and stopped with `ModuleNotFoundError`. That was an acceptance-helper environment defect, not a platform runtime failure. No runtime dependency was installed to work around it.

A subsequent stdlib-only artifact inspection passed completely:

```text
PR #20 LIVE ACCEPTANCE: PASS
```

## Accepted artifact facts

Trust/source state:

```text
alert_attention_version: 0.2
mutation_allowed: false
Prometheus: COMPLETE
Alertmanager: COMPLETE
Kubernetes scope validation: COMPLETE
```

Cardinality was preserved:

```text
Alertmanager alerts: 11
Alert attention:     11
Event correlations: 11
```

Final scope distribution:

```text
NAMESPACE: 9
PLATFORM:  2
SERVICE:   0
WORKLOAD:  0
NODE:      0
```

Validation distribution:

```text
VALIDATED_INFRASTRUCTURE_SUBJECT: 3
UNVERIFIED_SIGNAL_DIMENSION:      6
PLATFORM_FALLBACK:                2
```

All remaining Service-scope validation checks passed:

```text
Service scopes without observed Service: none
```

The known synthetic kubelet subjects are gone:

```text
Service/keycloak/kube-prom-stack-kubelet
Service/monitoring/kube-prom-stack-kubelet
Service/moodle/kube-prom-stack-kubelet
```

Accepted guards:

```text
pseudo attention scopes: none
pseudo incident scopes:  none
automatic kube-system rewrite: none
label mismatches: none
current kubelet-labelled alerts: 6
```

The original `service=kube-prom-stack-kubelet` signal dimension remains preserved. No alert was rewritten to `Service/kube-system/kube-prom-stack-kubelet` merely because that real Service exists elsewhere.

## Downstream result

Corrected incident grouping produced four candidates:

```text
Namespace/keycloak    alerts=2
Namespace/monitoring  alerts=5
Namespace/moodle      alerts=2
Platform/k3s-main     alerts=2
```

The six unverified kubelet Service claims are explicitly represented by `ALERT_SCOPE_SERVICE_SIGNAL_NOT_OBSERVED` and retain the weaker observed Namespace scope. This is a completed validation result, not a source failure.

Sensitive/free-form guards passed:

```text
forbidden projected keys: none
raw URL markers: false
```

## Acceptance decision

PR #20 is accepted for merge.

The slice proves the intended trust boundary:

- alert labels remain signal dimensions;
- exact resource identity is accepted only when same-cycle Kubernetes evidence supports it;
- missing identity under complete observation does not trigger heuristic rewriting;
- failed observation remains distinct from absence;
- Event correlation and incident grouping consume the corrected scopes;
- no telemetry query, RBAC expansion, mutation, secret access, or root-cause inference was added.

## Next step

After merge, create a separate Milestone 4 integration slice that consumes the already accepted routing-ownership artifact and prefers complete routing evidence over selector inference where supported. Keep ambiguous/non-Pod/unknown routing explicit and do not add Loki/OpenTelemetry in that integration slice.
