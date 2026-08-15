# Milestone 4 Alert Scope Validation Live Test Gate — 2026-08-15

## Status

Repository gate accepted after correction. Management-host bootstrap/runtime acceptance remains pending.

## Purpose

Validate that alert label dimensions are no longer treated as authoritative Kubernetes resource identity unless the same-cycle Kubernetes snapshot supports that exact subject.

## First management-host attempt

The first PR #20 run passed the static guards before pytest:

```text
RBAC changes: none
query-capable client markers: none
```

The repository test gate then stopped execution before bootstrap:

```text
3 failed, 153 passed in 1.56s
```

All three failures reached fallback scope paths and raised:

```text
KeyError: 'evidence_id'
```

Root cause: alert-attention records carry an `evidence_ids` array, not a singular `evidence_id` field. The new scope validator incorrectly referenced `alert["evidence_id"]` when constructing fallback warnings. This was an implementation defect that would also affect live fallback processing; it was not a test-fixture defect.

Correction on the active branch:

- fallback warnings now preserve the existing `alert.evidence_ids` list;
- no synthetic singular evidence field is introduced;
- a regression assertion verifies that original alert evidence survives an unverified Service-to-Namespace fallback.

Because pytest failed, `bootstrap-observer.sh` did not execute in this first attempt. No runtime/systemd acceptance claim is derived from it.

## Corrected repository gate

The corrected branch was fast-forwarded on `mgmt-automation` and the full repository suite passed:

```text
156 passed in 0.89s
```

Tested branch checkpoint before this bookkeeping commit:

```text
2d7e655 Record first PR 20 gate failure
```

This establishes repository-level correctness for the corrected implementation. It does not yet establish live scope-validation/systemd acceptance.

## Required live acceptance evidence

1. Existing observer collection, Prometheus, Alertmanager, Event, routing ownership, inventory, incident grouping, Git/history/drift remain healthy.
2. No Kubernetes RBAC changes are introduced by this slice.
3. The scope-validation runtime contains no infrastructure query client (`kubectl`, subprocess, HTTP client).
4. systemd ordering is:

```text
routing ownership
alert scope validation / Event-correlation rebuild
incident grouping
```

5. Final `alert-attention.json` is version `0.2`.
6. `source_status.kubernetes_scope` is explicit.
7. Attention cardinality is unchanged by scope validation.
8. Original allowlisted alert labels remain unchanged.
9. Every final attention record contains `scope_validation`.
10. Exact observed Service/Node/Namespace subjects may remain resource scoped with `VALIDATED_INFRASTRUCTURE_SUBJECT`.
11. Existing workload scope remains `INFERRED_RELATION`; this slice does not upgrade it to observed routing ownership.
12. An unobserved exact Service identity with a valid observed namespace falls back to Namespace scope with `UNVERIFIED_SIGNAL_DIMENSION`.
13. An unobserved Namespace identity falls back to Platform scope.
14. Failed/incomplete relevant Kubernetes collection keeps `kubernetes_scope` partial/failed, not false absence.
15. The three previously observed kubelet pseudo-Service subjects are specifically inspected:

```text
Service/keycloak/kube-prom-stack-kubelet
Service/monitoring/kube-prom-stack-kubelet
Service/moodle/kube-prom-stack-kubelet
```

16. Those subjects must not remain Service scoped unless current Kubernetes evidence now proves the exact Services exist.
17. They must not be rewritten automatically to `Service/kube-system/kube-prom-stack-kubelet`.
18. Original `service=kube-prom-stack-kubelet` signal labels must remain preserved.
19. Event correlation is rebuilt from corrected scopes before incident grouping.
20. Incident candidate cardinality/grouping changes are allowed only as a deterministic consequence of corrected scope identity; no alerts may be silently dropped.
21. Sensitive/free-form field guards remain clean and `mutation_allowed=false`.
22. Fallback warnings preserve existing alert `evidence_ids`; no singular synthetic `evidence_id` field is required.

## Expected interpretation

A reduced number of Service-scoped incident candidates is expected if previous Service identities were synthetic combinations of metric dimensions.

A Namespace fallback does not claim that the whole namespace is affected. It means only that the namespace label is an observed infrastructure identity while the stronger Service identity was not validated.

`UNVERIFIED_SIGNAL_DIMENSION` is not a source failure when the relevant Kubernetes collection is complete. It is a completed validation result showing that a signal dimension did not map to the claimed resource identity.

If Kubernetes scope validation is partial/failed, downstream no-match evidence must remain uncertain.

## Trust boundary

This slice corrects identity semantics only. It does not add telemetry, infer root cause, infer business impact, change Prometheus/Alertmanager rules, or introduce remediation.
