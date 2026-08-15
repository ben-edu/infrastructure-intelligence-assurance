# Milestone 4 Alert Scope Validation Live Test Gate — 2026-08-15

## Status

Pending management-host live acceptance.

## Purpose

Validate that alert label dimensions are no longer treated as authoritative Kubernetes resource identity unless the same-cycle Kubernetes snapshot supports that exact subject.

## Required acceptance evidence

1. Full repository tests pass.
2. Existing observer collection, Prometheus, Alertmanager, Event, routing ownership, inventory, incident grouping, Git/history/drift remain healthy.
3. No Kubernetes RBAC changes are introduced by this slice.
4. The scope-validation runtime contains no infrastructure query client (`kubectl`, subprocess, HTTP client).
5. systemd ordering is:

```text
routing ownership
alert scope validation / Event-correlation rebuild
incident grouping
```

6. Final `alert-attention.json` is version `0.2`.
7. `source_status.kubernetes_scope` is explicit.
8. Attention cardinality is unchanged by scope validation.
9. Original allowlisted alert labels remain unchanged.
10. Every final attention record contains `scope_validation`.
11. Exact observed Service/Node/Namespace subjects may remain resource scoped with `VALIDATED_INFRASTRUCTURE_SUBJECT`.
12. Existing workload scope remains `INFERRED_RELATION`; this slice does not upgrade it to observed routing ownership.
13. An unobserved exact Service identity with a valid observed namespace falls back to Namespace scope with `UNVERIFIED_SIGNAL_DIMENSION`.
14. An unobserved Namespace identity falls back to Platform scope.
15. Failed/incomplete relevant Kubernetes collection keeps `kubernetes_scope` partial/failed, not false absence.
16. The three previously observed kubelet pseudo-Service subjects are specifically inspected:

```text
Service/keycloak/kube-prom-stack-kubelet
Service/monitoring/kube-prom-stack-kubelet
Service/moodle/kube-prom-stack-kubelet
```

17. Those subjects must not remain Service scoped unless current Kubernetes evidence now proves the exact Services exist.
18. They must not be rewritten automatically to `Service/kube-system/kube-prom-stack-kubelet`.
19. Original `service=kube-prom-stack-kubelet` signal labels must remain preserved.
20. Event correlation is rebuilt from corrected scopes before incident grouping.
21. Incident candidate cardinality/grouping changes are allowed only as a deterministic consequence of corrected scope identity; no alerts may be silently dropped.
22. Sensitive/free-form field guards remain clean and `mutation_allowed=false`.

## Expected interpretation

A reduced number of Service-scoped incident candidates is expected if previous Service identities were synthetic combinations of metric dimensions.

A Namespace fallback does not claim that the whole namespace is affected. It means only that the namespace label is an observed infrastructure identity while the stronger Service identity was not validated.

`UNVERIFIED_SIGNAL_DIMENSION` is not a source failure when the relevant Kubernetes collection is complete. It is a completed validation result showing that a signal dimension did not map to the claimed resource identity.

If Kubernetes scope validation is partial/failed, downstream no-match evidence must remain uncertain.

## Trust boundary

This slice corrects identity semantics only. It does not add telemetry, infer root cause, infer business impact, change Prometheus/Alertmanager rules, or introduce remediation.
