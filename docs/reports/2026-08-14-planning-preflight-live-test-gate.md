# Kubernetes Planning Preflight Live Test Gate — 2026-08-14

## Status

Accepted after management-host test, live-cluster refresh, and task-scoped AI consumption.

## Scope

Final Milestone 1 acceptance test for task-scoped AI planning consumption.

The test used the installed read-only observer evidence and the repository's non-production hypothetical deployment request. It did not mutate Kubernetes resources.

## Repository test result

The corrected repository test contract passed directly from the management-host checkout:

```text
43 passed in 0.17s
```

The earlier request-example allowlist failure was confirmed to be a test-contract mismatch. Evidence/context examples retain their explicit allowlist while planning request examples are validated by their dedicated JSON Schema and `validate_request()` path.

## Runtime refresh result

The bootstrap refreshed the live Kubernetes evidence loop and installed the durable preflight CLI successfully.

Observed runtime state:

- Kubernetes evidence collection service completed with status `0/SUCCESS`;
- raw evidence, compact context, operator context, topology JSON, and topology Markdown were refreshed;
- `/usr/local/bin/iia-k8s-preflight` was installed;
- the non-sensitive hypothetical request was installed under `/etc/infra-assurance/examples/`.

No Kubernetes RBAC permission or mutation capability was added.

## Live planning preflight result

The preflight ran as the `infra-assurance` service user and produced:

- preflight version: `0.1`;
- cluster: `k3s-main`;
- mutation allowed: `false`;
- readiness: `PLAN_WITH_LIVE_VERIFICATION`;
- evidence-backed facts: 6;
- observed conflicts: 0;
- inferences: 0;
- unknown evidence states: 0;
- required live verification checks: 6;
- candidate plan steps: 5;
- post-change verification checks: 5.

Evidence-backed facts established that:

- Namespace `validation` is present;
- the requested Deployment name is not observed in the current complete Deployment collection;
- the requested Service name is not observed in the current complete Service collection;
- the requested Ingress name is not observed in the current complete Ingress collection;
- the requested PVC name is not observed in the current complete PVC collection;
- all three observed Nodes are Ready and schedulable in the current snapshot.

No current resource-name or exact route conflict was observed for the hypothetical request.

## Required live verification retained

The preflight correctly refused to convert unobserved domains into facts. It requires live verification of:

1. image registry reachability and pull authentication;
2. actual scheduler feasibility and current capacity pressure;
3. ResourceQuota and LimitRange policy in namespace `validation`;
4. applicable NetworkPolicy constraints;
5. external DNS ownership/routing for the requested hostname;
6. default StorageClass and dynamic provisioning capability for the requested PVC.

These checks remain required before any later approval to mutate infrastructure.

## AI consumption result

The task-scoped `preflight.md` artifact was sufficient for planning reasoning without passing the complete raw Kubernetes snapshot to the AI.

The AI consumption test preserved the trust boundary:

- observed namespace/resource-name/node state was treated as fact;
- zero conflicts was not interpreted as authorization to deploy;
- the six unobserved operational domains remained required live verification;
- the five candidate steps remained plan-only;
- `mutation_allowed=false` was preserved;
- no unknown, stale, failed, or inferred state was promoted to fact.

The hypothetical image uses `registry.example.invalid`; therefore no claim is made that the image is pullable. Image pullability remains explicitly unverified, as intended by the acceptance test.

## Trust statement

No credential, kubeconfig content, Kubernetes Secret payload, sensitive connection string, or secret-bearing environment value is recorded in this report.

A successful preflight is not approval to execute the candidate plan. Milestone 1 remains read-only.

## Acceptance conclusion

Milestone 1 acceptance is complete end-to-end:

```text
Observe
  -> Normalize
  -> Timestamp / provenance
  -> Freshness / trust
  -> Compact operational context
  -> Traceable topology
  -> Task-scoped planning preflight
  -> Explicit uncertainty and required live verification
  -> AI consumption without mutation authority
```

The next milestone may now introduce snapshot history, diff, and declared-versus-observed drift while preserving these evidence and trust semantics.
