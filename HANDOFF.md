# Project Handoff

This is the compact continuation checkpoint for the Infrastructure Intelligence & Assurance Platform. Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read the Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable repository/runtime

- repo: `ben-edu/infrastructure-intelligence-assurance`
- stable branch: `main`
- stable main checkpoint before active PR: `e24b86e7431cecaea01a6984b57f6b2185390f73`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- runtime user: `infra-assurance`
- systemd oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

The oneshot being `inactive (dead)` after `status=0/SUCCESS` is expected.

## Accepted implementation checkpoint

Milestones 0–3 are live validated for the evidence contract, Kubernetes read-only inventory/context, topology/preflight, bounded history/diff, Git declared-state/drift, workload inventory, and Prometheus Operator configuration coverage.

Milestone 4 accepted slices:

- PR #10 — Prometheus runtime, exact read-only proxy `monitoring/kube-prom-stack-prometheus:9090`.
- PR #13 — Alertmanager handling correlation, exact read-only proxy `monitoring/kube-prom-stack-alertmanager:9093`.
- PR #14 — Kubernetes Event correlation with no Pod-name ownership inference.
- PR #16 — incident candidates/drill-down, merged at `12ad053332bdbff39b2e580cd33cd6715e675748`.

PR #16 accepted live result:

```text
pytest: 134 passed
alert attention: 10
incident candidates: 7
ACTIVE: 4
SUPPRESSED: 3
UNKNOWN: 0
scope: 3 Namespace / 1 Platform / 3 Service
mutation_allowed: false
```

The three current Service candidates require stronger Kubernetes routing evidence before workload ownership should be inferred.

Known real drift remains intentionally unresolved:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Active work — PR #18 routing ownership evidence

- PR: `#18 Milestone 4 bounded EndpointSlice and Pod routing ownership`
- branch: `feature/m4-endpointslice-pod-ownership`
- package version: `0.13.0`
- status: Draft; do not merge until corrected management-host live acceptance passes

### Goal

Produce stronger Service routing/controller evidence without broad Pod enumeration, then validate it before any downstream topology/inventory/incident integration.

### Least-privilege design

```text
EndpointSlices: list
Pods:           get only
ReplicaSets:    get only

Pods:           list/watch denied
ReplicaSets:    list/watch denied
Secrets:        denied
mutation:       denied
```

Pod GETs are exact-name and only follow EndpointSlice Pod targetRefs. ReplicaSet GETs are exact-name and only follow selected Pod controller ownerReferences.

Default per-cycle bounds:

```text
max Pod GETs:        500
max ReplicaSet GETs: 250
```

Bound exhaustion or failed observation is explicit `PARTIAL/UNKNOWN`, never absence.

Persisted projection excludes EndpointSlice addresses/IPs, Pod IP/spec/status, arbitrary labels/annotations, container/env data, logs, volumes, Secret references, service-account tokens, UIDs, and other full-object content.

Supported ownership chains:

```text
Service -> EndpointSlice -> Pod -> StatefulSet
Service -> EndpointSlice -> Pod -> DaemonSet
Service -> EndpointSlice -> Pod -> ReplicaSet -> Deployment
```

Pod names are never parsed for ownership. Cluster-scoped targetRefs such as Node retain `namespace=null`. Non-Pod targetRefs remain explicit `NON_POD_TARGET` evidence.

Artifacts:

```text
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.json
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.md
```

PR #18 deliberately does not feed this artifact into incident candidates yet.

### First management-host gate attempt

The first PR #18 run stopped at pytest before bootstrap:

```text
1 failed, 145 passed in 0.98s
```

Failed test:

```text
tests/test_routing_ownership_wiring.py::test_rbac_allows_endpointslice_list_but_only_exact_get_capability_for_pods_and_replicasets
```

Cause: regression-test parsing bug, not an RBAC implementation defect. The test split the ClusterRole text at the document boundary and accidentally included later rules, so `list/watch` verbs from unrelated resources were attributed to the Pod rule.

Correction already committed on the active branch:

- parse individual ClusterRole rule blocks;
- assert Pod rule independently as `verbs: ["get"]`;
- assert ReplicaSet rule independently as `verbs: ["get"]`;
- assert EndpointSlice rule independently as `verbs: ["list"]`.

Because pytest failed, `bootstrap-observer.sh` did not execute in the first attempt. No live RBAC/runtime acceptance claim is made yet.

Detailed gate report:

```text
docs/reports/2026-08-15-m4-routing-ownership-live-test-gate.md
```

## Exact next step

Fetch the active branch normally (do not force-rewrite it; the management host has already tested this branch), rerun the full pytest suite, and only if green continue with bootstrap and the existing PR #18 routing-ownership acceptance block.

Key live acceptance checks remain:

1. EndpointSlice list yes, direct get no;
2. Pod get yes, list/watch no;
3. ReplicaSet get yes, list/watch no;
4. Secrets/mutation no;
5. source status and GET bounds explicit;
6. `Service/monitoring/loki-headless` live routing inspected;
7. current `kube-prom-stack-kubelet` Service routing inspected;
8. cluster-scoped Node target namespace remains null;
9. sensitive/full-object fields absent;
10. incident candidates still do not consume routing ownership.

If accepted, the next slice may integrate complete routing ownership into topology/inventory/incident context, preferring the stronger relation only where live evidence supports it.

Do not add Loki/OpenTelemetry in PR #18.

## Trust invariants

- observation credentials remain separate from future control credentials;
- infrastructure interaction remains read-only;
- collector failure is explicit;
- stale is not current;
- unknown is not absent;
- inference is not fact;
- declared and observed state remain separate;
- specialized systems remain authoritative;
- no passwords, tokens, private keys, raw Kubernetes Secret values, sensitive Terraform state, or complete sensitive connection strings enter evidence/AI context;
- current generated operational artifacts keep `mutation_allowed=false`.
