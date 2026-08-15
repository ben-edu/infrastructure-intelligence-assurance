# Project Handoff

This file is the compact continuation checkpoint for the Infrastructure Intelligence & Assurance Platform.

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules. This file records the current implementation checkpoint and exact continuation point.

## Resume protocol

1. Read the Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR contains a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Use repository/live evidence instead of reconstructing implementation state from chat memory.

## Stable repository/runtime

- repo: `ben-edu/infrastructure-intelligence-assurance`
- stable branch: `main`
- stable continuity checkpoint: `61a80fcedd2cc0a658638405f8e2fe63cd4c18bd`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- runtime user: `infra-assurance`
- systemd oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

The oneshot being `inactive (dead)` after `status=0/SUCCESS` is expected.

## Stable implementation

### Milestone 0

Evidence contract complete.

Key semantics remain:

- `PRESENT | ABSENT | UNKNOWN`
- `COMPLETE | PARTIAL | FAILED_TO_OBSERVE`
- `CURRENT | STALE`
- failed observation never means absence
- declared and observed planes stay separate
- inference is not fact
- secrets/sensitive values are excluded

### Milestone 1

Kubernetes vertical slice complete and live validated.

Read-only observation covers Namespace, Node, Deployment, StatefulSet, DaemonSet, Service, Ingress, and PVC, plus topology, context, and read-only planning preflight.

### Milestone 2

History, diff, Git declared-state observation, drift, and compact change context complete and live validated.

Git source:

- `ben-edu/api-cluster-infra`
- branch `main`
- dedicated read-only deploy key
- repeatedly observed revision `5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4`
- accepted live declared records: 27

Known real drift retained intentionally:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

No automatic correction was made.

### Milestone 3

Workload operational inventory and Prometheus Operator configuration coverage complete for current slices and live validated.

Latest accepted inventory:

- workloads: 68
- Git-declared workloads: 9
- outside configured Git scope: 59
- Service links: 77
- Ingress route candidates: 26
- PVC links: 18

Accepted Prometheus Operator coverage:

- Prometheus: 1
- ServiceMonitor: 11
- PodMonitor: 0
- selected ServiceMonitor: 9
- `OPERATOR_MONITOR_MATCH`: 7 workloads
- `NO_OPERATOR_MONITOR_MATCH`: 61 workloads
- unknown: 0

Configuration coverage is not scrape-health evidence.

## Active work — Milestone 4

### PR

- PR: `#10 Milestone 4 Prometheus runtime intelligence`
- branch: `feature/m4-prometheus-runtime-intelligence`
- status: Draft; do not merge until final live acceptance succeeds

Goal: consume authoritative Prometheus runtime target health and active alert state, safely normalize it, and attach signal-scoped evidence to workload inventory entities.

Persisted runtime projection excludes raw scrape URLs, discovered labels, arbitrary annotations, metric series/samples, credentials, Secret values, and sensitive connection data.

### Live attempt 1

Tests:

```text
102 passed in 0.72s
```

Observer runtime itself succeeded. Bootstrap stopped because the RBAC verification command used `kubectl auth can-i get services/proxy`, which tests `TYPE/NAME` rather than reliably testing the proxy subresource.

Correction: use named resource plus `--subresource=proxy`.

### Live attempt 2

Tests:

```text
102 passed in 0.65s
```

Bootstrap succeeded and reported:

```text
Prometheus Service / monitoring : yes
Other Service / monitoring      : no
Prometheus Service / default    : no
Secrets                         : no
Create Deployment               : no
```

The real API request nevertheless failed:

```text
services "kube-prom-stack-prometheus:9090" is forbidden
```

Runtime failure semantics were correct:

- source: `FAILED_TO_OBSERVE`
- targets: 0 because observation failed, not because absence was claimed
- alerts: 0 because observation failed, not because absence was claimed
- 68/68 workloads: `UNKNOWN`
- runtime/inventory cardinality matched
- errors: `PROMETHEUS_PROXY_FORBIDDEN` for targets and alerts
- forbidden projected keys: none
- raw URL markers: false

### Root cause and correction already implemented

The real Service proxy URL contains the port-qualified resource name:

```text
kube-prom-stack-prometheus:9090
```

The RBAC rule had been restricted to only:

```text
kube-prom-stack-prometheus
```

which does not authorize the actual port-qualified proxy request.

The active branch now uses the exact least-privilege rule:

```text
namespace: monitoring
resource: services/proxy
resourceName: kube-prom-stack-prometheus:9090
verb: get
```

Bootstrap is pinned to the exact source tuple:

```text
monitoring / kube-prom-stack-prometheus / 9090
```

and must verify:

```text
allowed: kube-prom-stack-prometheus:9090 proxy in monitoring
denied:  unrelated-service:9090 proxy in monitoring
denied:  kube-prom-stack-prometheus:9090 proxy in default
denied:  unqualified kube-prom-stack-prometheus proxy in monitoring
denied:  list Secrets
denied:  Kubernetes mutation
```

Regression tests and the live-test report were updated for this exact boundary.

### Exact next step

Fetch/reset the rewritten PR #10 branch on `mgmt-automation`, then run the final corrected acceptance:

1. pytest;
2. bootstrap;
3. exact port-qualified proxy RBAC checks;
4. Prometheus `/api/v1/targets?state=active` probe;
5. Prometheus `/api/v1/alerts` probe;
6. inspect `prometheus-runtime.json/md`;
7. verify runtime/inventory cardinality;
8. verify sensitive/raw field exclusion;
9. treat real target-down/active-alert signals as valid evidence, not gate failures;
10. update live report;
11. only then mark PR #10 ready and merge.

M4 is not accepted yet.

## Trust invariants

- observation credentials remain separate from future control credentials
- current infrastructure interaction is read-only
- collector failure is explicit
- stale is not current
- unknown is not absent
- inference is not fact
- declared and observed state remain separate
- specialized systems remain authoritative
- no passwords, tokens, private keys, raw Kubernetes Secret values, sensitive Terraform state, or complete sensitive connection strings in evidence/AI context
- current generated operational artifacts keep `mutation_allowed=false`

## Key artifacts

```text
/var/lib/infra-assurance/evidence/kubernetes.json
/var/lib/infra-assurance/evidence/context.json
/var/lib/infra-assurance/evidence/topology.json
/var/lib/infra-assurance/evidence/diff.json
/var/lib/infra-assurance/evidence/drift.json
/var/lib/infra-assurance/evidence/change-context.json
/var/lib/infra-assurance/evidence/observability-coverage.json
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/prometheus-runtime.json   # M4, not yet accepted
```

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, live gate outcomes, material blockers/risks, exact next step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
