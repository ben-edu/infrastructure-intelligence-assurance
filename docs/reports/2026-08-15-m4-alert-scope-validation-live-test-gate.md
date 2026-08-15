# Milestone 4 Alert Scope Validation Live Test Gate — 2026-08-15

## Status

Repository gate accepted after correction. Management-host runtime executed successfully; final artifact acceptance is pending one stdlib-only verification pass because the manual acceptance helper used `sudo python3` with an unavailable optional `jsonschema` package.

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

This establishes repository-level correctness for the corrected implementation.

## Second management-host attempt — runtime succeeded, helper dependency failed

`bootstrap-observer.sh` completed and the systemd oneshot finished successfully.

Observed execution order and status:

```text
kubernetes_runtime   status=0/SUCCESS
routing_ownership   status=0/SUCCESS
alert_scope_runtime status=0/SUCCESS
incident_runtime    status=0/SUCCESS
```

The oneshot returned to `inactive (dead)` after successful completion, which is expected.

The manual Python acceptance helper then stopped before printing its JSON assertions with:

```text
ModuleNotFoundError: No module named 'jsonschema'
```

This is an acceptance-helper environment defect, not a platform runtime failure. Repository tests already exercise the schema with `jsonschema`; the root/system Python used by the manual helper does not have that optional test dependency installed. No package installation is required for the runtime and none should be added solely to satisfy this helper.

Useful live evidence emitted by the successfully completed runtime before the helper failure:

```text
Alert attention records: 11
Active: 5
Inhibited: 6
Correlated to Prometheus: 11
Workload scoped: 0
Node scoped: 0
Service scoped: 0
Namespace scoped: 9
Platform scoped: 2
```

The final attention context explicitly reported six `ALERT_SCOPE_SERVICE_SIGNAL_NOT_OBSERVED` corrections for kubelet-labelled signals in monitoring, moodle, and keycloak. They fell back to their observed Namespace scopes; no pseudo-Service scope remained in the rendered context and no automatic rewrite to the real kube-system Service was performed.

Incident grouping after corrected scope identity produced:

```text
Alert attention records: 11
Incident candidates: 4
Active candidates: 4
Suppressed candidates: 0
Unknown candidates: 0
```

Current candidates were:

```text
Namespace/keycloak
Namespace/monitoring
Namespace/moodle
Platform/k3s-main
```

This is consistent with the intended correction: synthetic kubelet Service identities are no longer used downstream.

## Remaining live acceptance evidence

Run one stdlib-only artifact inspection; do not reinstall dependencies or rerun pytest/bootstrap unnecessarily.

The remaining check must confirm:

1. final `alert-attention.json` version is `0.2`;
2. `source_status.kubernetes_scope` is explicit and current;
3. Attention cardinality equals current Alertmanager alert cardinality;
4. Event correlation cardinality equals final attention cardinality;
5. every final attention record contains `scope_validation`;
6. no final `SERVICE` scope lacks an observed Kubernetes Service;
7. the kubelet pseudo-Service subjects do not remain;
8. no automatic rewrite to `Service/kube-system/kube-prom-stack-kubelet` occurred;
9. original `service=kube-prom-stack-kubelet` signal labels remain preserved;
10. Event correlation and incident grouping use corrected scopes;
11. sensitive/free-form field guards remain clean and `mutation_allowed=false`.

Schema validation does not need to be repeated in this root-Python live helper because the accepted repository test suite already validates the v0.2 schema.

## Expected interpretation

A reduced number of Service-scoped incident candidates is expected if previous Service identities were synthetic combinations of metric dimensions.

A Namespace fallback does not claim that the whole namespace is affected. It means only that the namespace label is an observed infrastructure identity while the stronger Service identity was not validated.

`UNVERIFIED_SIGNAL_DIMENSION` is not a source failure when the relevant Kubernetes collection is complete. It is a completed validation result showing that a signal dimension did not map to the claimed resource identity.

If Kubernetes scope validation is partial/failed, downstream no-match evidence must remain uncertain.

## Trust boundary

This slice corrects identity semantics only. It does not add telemetry, infer root cause, infer business impact, change Prometheus/Alertmanager rules, or introduce remediation.
