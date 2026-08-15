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

### Milestones 0–3

Accepted/live validated:

- evidence/trust contract;
- Kubernetes read-only inventory/context;
- topology and read-only planning preflight;
- bounded history/diff;
- Git declared-state observer and drift;
- workload operational inventory;
- Prometheus Operator configuration coverage.

Git declared source:

```text
ben-edu/api-cluster-infra
branch: main
last repeatedly observed revision: 5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
accepted declared records: 27
```

Known real drift remains intentionally unresolved:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

### Milestone 4 accepted slices

Prometheus runtime — PR #10:

- exact read-only proxy: `monitoring/kube-prom-stack-prometheus:9090`;
- accepted baseline: 21 targets, all UP;
- signal state is not generic application-health proof.

Alertmanager handling correlation — PR #13:

- exact read-only proxy: `monitoring/kube-prom-stack-alertmanager:9093`;
- accepted baseline: 11 alerts, 2 ACTIVE, 9 INHIBITED;
- all 11 correlated to Prometheus without inventing workload ownership.

Kubernetes Event correlation — PR #14:

- Events `get/list/watch` only;
- accepted one-hour projection excludes Event message/free-form sensitive material;
- Pod-name controller inference is not implemented.

Incident candidates/drill-down — PR #16, merged at `12ad053332bdbff39b2e580cd33cd6715e675748`:

```text
pytest: 134 passed in 0.94s
observer: SUCCESS
incident ExecStartPost: SUCCESS
alert attention: 10
incident candidates: 7
ACTIVE: 4
SUPPRESSED: 3
UNKNOWN: 0
scope: 3 Namespace / 1 Platform / 3 Service
mutation_allowed: false
```

Accepted next-evidence recommendations:

```text
PROMETHEUS_ALERTMANAGER: 4
KUBERNETES_ENDPOINTSLICE_POD: 3
LOKI_CANDIDATE: 3
KUBERNETES_OBJECT: 1
PROMETHEUS_KUBERNETES: 1
```

The three Service candidates had no supported workload routing ownership and therefore required EndpointSlice/Pod verification.

## Active work — PR #18 routing ownership evidence

- PR: `#18 Milestone 4 bounded EndpointSlice and Pod routing ownership`
- branch: `feature/m4-endpointslice-pod-ownership`
- base main: `e24b86e7431cecaea01a6984b57f6b2185390f73`
- package version: `0.13.0`
- status: Draft; do not merge until management-host live acceptance passes

### Goal

Strengthen current Service backend/controller evidence before allowing routing ownership to influence topology, inventory, or incident candidates.

### Least-privilege observation design

New RBAC:

```text
EndpointSlices: list
Pods:           get only
ReplicaSets:    get only
```

Explicitly not granted:

```text
Pods:        list/watch
ReplicaSets: list/watch
Secrets:     access
mutation:    create/update/patch/delete
```

Pod exact GETs occur only for Pod targetRefs observed in EndpointSlices. ReplicaSet exact GETs occur only for ReplicaSet controller ownerReferences observed from those selected Pods.

Default bounds per cycle:

```text
max Pod GETs:        500
max ReplicaSet GETs: 250
```

Bound exhaustion is `PARTIAL`, never absence.

### Safe persisted projection

EndpointSlice evidence retains only:

- namespace/name;
- `kubernetes.io/service-name` association;
- endpoint targetRef identity;
- ready/serving/terminating conditions.

Pod/ReplicaSet exact reads emit controller ownerReference apiVersion/kind/name only.

The artifact excludes EndpointSlice addresses, Pod IPs, Pod specs/status, arbitrary labels/annotations, container/env data, logs, volumes, Secret references, service-account tokens, and owner UIDs.

### Ownership chain

Supported evidence paths:

```text
Service -> EndpointSlice -> Pod -> StatefulSet
Service -> EndpointSlice -> Pod -> DaemonSet
Service -> EndpointSlice -> Pod -> ReplicaSet -> Deployment
```

Pod names are never parsed to derive ownership. Non-Pod targetRefs remain explicit `NON_POD_TARGET` evidence.

Artifacts:

```text
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.json
/var/lib/infra-assurance/evidence/kubernetes-routing-ownership.md
```

The routing artifact is generated before incident candidates, but PR #18 deliberately does not pass it into incident-candidate generation. Existing selector-based relationships remain authoritative for accepted downstream behavior until a separate integration gate.

Relevant docs:

```text
docs/decisions/0014-bounded-endpointslice-pod-routing-ownership.md
docs/milestone-4-routing-ownership.md
docs/reports/2026-08-15-m4-routing-ownership-live-test-gate.md
```

## Exact next step

Run PR #18 management-host acceptance.

Verify:

1. full pytest suite;
2. observer/systemd success;
3. EndpointSlice list = yes;
4. Pod get = yes but Pod list/watch = no;
5. ReplicaSet get = yes but ReplicaSet list/watch = no;
6. Secrets and mutation remain denied;
7. routing ownership artifact source status/bounds;
8. exact Pod/ReplicaSet GET counts;
9. resolution/state distribution;
10. `Service/monitoring/loki-headless` specifically;
11. current `kube-prom-stack-kubelet` Services specifically;
12. sensitive/full-object fields absent;
13. incident candidates still do not consume the new artifact.

If accepted, the next slice may integrate current complete routing ownership into topology/inventory/incident context, preferring it over selector inference only where evidence supports that upgrade.

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
