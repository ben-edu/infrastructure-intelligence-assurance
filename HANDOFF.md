# Project Handoff

This is the compact continuation checkpoint for the Infrastructure Intelligence & Assurance Platform. Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read the Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable checkpoint

- repository: `ben-edu/infrastructure-intelligence-assurance`
- stable branch: `main`
- stable main before active PR: `e24b86e7431cecaea01a6984b57f6b2185390f73`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- cluster: `k3s-main`
- runtime user: `infra-assurance`
- oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

Milestones 0–3 are live validated for the evidence contract, Kubernetes observation/context/topology/preflight, history/diff, Git declared-state/drift, workload inventory, and Prometheus Operator coverage.

Milestone 4 accepted slices:

- PR #10 — Prometheus runtime;
- PR #13 — Alertmanager handling correlation;
- PR #14 — Kubernetes Event correlation;
- PR #16 — incident candidates/drill-down.

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

Known real drift remains intentionally unresolved:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Active work — PR #18

- PR: `#18 Milestone 4 bounded EndpointSlice and Pod routing ownership`
- branch: `feature/m4-endpointslice-pod-ownership`
- package version: `0.13.0`
- status: Draft
- live acceptance: not complete

Goal: strengthen Service routing/controller evidence before allowing stronger routing ownership to influence topology, inventory, or incident candidates.

### Least-privilege observation design

```text
EndpointSlices: list
Pods:           get only
ReplicaSets:    get only

Pods:           list/watch denied
ReplicaSets:    list/watch denied
Secrets:        denied
mutation:       denied
```

Pod GETs are exact-name and follow only Pod targetRefs observed in EndpointSlices. ReplicaSet GETs are exact-name and follow only controller ownerReferences observed on those selected Pods.

Default bounds:

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

### Management-host gate history

First attempt stopped before bootstrap:

```text
1 failed, 145 passed in 0.98s
```

Cause: regression-test parsing bug. The test accidentally included later ClusterRole rules and attributed unrelated `list/watch` verbs to the Pod rule. No infrastructure/RBAC change was applied in that attempt.

The test was corrected to inspect individual RBAC rule blocks.

Corrected repository test gate then passed on `mgmt-automation`:

```text
146 passed in 0.92s
```

Tested branch checkpoint before the report/Handoff bookkeeping commits:

```text
44a13b0 record first PR 18 live gate failure
```

Therefore repository-level tests are green. Bootstrap/live Kubernetes acceptance has not yet been run for PR #18.

Detailed report:

```text
docs/reports/2026-08-15-m4-routing-ownership-live-test-gate.md
```

## Exact next step

Do not rerun pytest unnecessarily. Fetch the active branch normally, then run `bootstrap-observer.sh` and the remaining live routing acceptance checks.

Required live checks:

1. EndpointSlice list = yes, direct get = no;
2. Pod get = yes, list/watch = no;
3. ReplicaSet get = yes, list/watch = no;
4. Secrets/mutation = no;
5. observer and both ExecStartPost steps succeed;
6. routing source status/bounds and exact GET counts are explicit;
7. `Service/monitoring/loki-headless` routing is inspected;
8. current Service-scoped incident candidates, especially kubelet-related ones, are inspected;
9. Node targetRefs preserve `namespace=null`;
10. sensitive/full-object fields remain absent;
11. incident candidates still do not consume routing ownership.

If accepted, update the live report/Handoff, mark PR #18 ready, squash merge it, and then create a separate integration slice that uses stronger routing evidence only where current evidence supports it.

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

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
