# Milestone 4 — Alert Scope Identity Validation

## Purpose

Correct label-derived alert resource scope before accepted routing ownership is allowed to influence incident context.

PR #18 demonstrated that an alert can carry:

```text
namespace=keycloak
service=kube-prom-stack-kubelet
```

without there being a Kubernetes Service named `kube-prom-stack-kubelet` in the `keycloak` namespace. Treating those two metric labels as an authoritative Service identity created false infrastructure subjects.

## Slice boundary

This slice is derived-only and read-only.

It adds no Kubernetes RBAC and performs no new Prometheus, Alertmanager, Kubernetes, Loki, or OpenTelemetry query.

Inputs are same-cycle local artifacts:

```text
alert-attention.json
kubernetes.json
kubernetes-event-runtime.json
```

The validator corrects resource scope and rebuilds Event correlation before incident grouping.

## Validation model

Alert labels remain intact as signal dimensions.

A resource scope is validated separately through:

```text
scope_validation.status
scope_validation.claimed_subject
scope_validation.validated_subject
scope_validation.basis
scope_validation.evidence_ids
```

Status meanings:

- `VALIDATED_INFRASTRUCTURE_SUBJECT` — exact resource identity exists in current observed Kubernetes evidence.
- `UNVERIFIED_SIGNAL_DIMENSION` — alert labels suggested a resource identity that was not validated; a weaker supported scope is used.
- `INFERRED_RELATION` — existing workload attribution remains an inference and is not upgraded by this slice.
- `PLATFORM_FALLBACK` — no stronger resource identity was claimed/validated.

## Conservative fallback

For an unvalidated Service signal:

```text
Service claim invalid/unverified
  -> validated Namespace scope, if available
  -> otherwise Platform scope
```

The validator never searches for a similarly named Service in another namespace and never rewrites the alert to such a Service.

## Source completeness

`alert-attention.json` version becomes `0.2` after validation and adds:

```text
source_status.kubernetes_scope
```

If the relevant Kubernetes collection is complete, a missing exact identity is a complete validation result.

If the relevant collection is partial/failed, the scope-validation source remains partial/failed and downstream correlation must not treat missing evidence as absence.

## Runtime ordering

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
```

`alert_scope_runtime` also rebuilds Kubernetes Event correlation from the corrected attention scopes before incident grouping.

## Expected current-cluster effect

The three previously observed false Service subjects:

```text
Service/keycloak/kube-prom-stack-kubelet
Service/monitoring/kube-prom-stack-kubelet
Service/moodle/kube-prom-stack-kubelet
```

must no longer remain Service-scoped unless current Kubernetes evidence unexpectedly proves those exact Services now exist.

The original signal label `service=kube-prom-stack-kubelet` must remain in each alert record.

The real `Service/kube-system/kube-prom-stack-kubelet` must not be substituted automatically.

## Out of scope

- routing ownership integration into incident impact;
- Loki ingestion/query;
- OpenTelemetry;
- alert-rule redesign;
- Prometheus relabel changes;
- mutation/remediation;
- broad new inventory collection.
