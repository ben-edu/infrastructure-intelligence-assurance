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
- stable main before PR #16 merge: `a9feef8957f74d0cb9ed4299fd86778de0bb2fe4`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- runtime user: `infra-assurance`
- systemd oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

The oneshot being `inactive (dead)` after `status=0/SUCCESS` is expected.

## Accepted implementation

### Milestones 0–3

Evidence contract, Kubernetes read-only observation/topology/preflight, bounded history/diff/Git drift, workload operational inventory, and Prometheus Operator configuration coverage are complete and live validated.

Git declared source remains:

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

### Milestone 4 — Prometheus runtime

PR #10 is merged and live accepted.

Accepted source boundary:

```text
monitoring/kube-prom-stack-prometheus:9090
services/proxy get only
```

Accepted baseline included 21 active targets, all UP. Prometheus runtime evidence is signal-scoped and is not generic application-health proof.

### Milestone 4 — Alertmanager handling correlation

PR #13 is merged and live accepted.

Accepted baseline included 11 Alertmanager alerts: 2 ACTIVE and 9 INHIBITED, all uniquely correlated to Prometheus. Scope remained Service/Namespace/Platform without invented workload ownership.

### Milestone 4 — Kubernetes Event correlation

PR #14 is merged and live accepted at:

```text
c97d5197bf278192055d87bde7f47705280038ad
```

Accepted Event boundary:

```text
core/v1 Events: get/list/watch
create Event: no
list Pods: no
list Secrets: no
Kubernetes mutation: no
window: 3600 seconds
max recent records: 500
```

Accepted live run had one Warning Event, `ProbeWarning` on a Moodle Pod. It was attached only as Namespace/moodle supporting context. Pod-name controller inference was not introduced and platform alerts were not broadly matched.

### Milestone 4 — Incident candidates and drill-down

PR #16 implementation is live accepted and ready to merge.

```text
branch: feature/m4-incident-candidates
tested head: 855d8acde041d6896d3172ba3a949134dd6d201e
package version: 0.12.0
pytest: 134 passed in 0.94s
observer service: status=0/SUCCESS
incident ExecStartPost: status=0/SUCCESS
mutation_allowed: false
```

No new infrastructure query or RBAC was introduced:

```text
list Pods: no
list EndpointSlices: no
list Secrets: no
create Deployment: no
query-capable client markers in incident implementation: none
```

The incident projection reads only current local artifacts:

```text
alert-attention.json
kubernetes-event-correlation.json
inventory.json
change-context.json
```

and emits:

```text
/var/lib/infra-assurance/evidence/incident-candidates.json
/var/lib/infra-assurance/evidence/incident-candidates.md
```

Live result:

```text
alert attention records: 10
incident candidates: 7
ACTIVE: 4
SUPPRESSED: 3
UNKNOWN: 0
scope:
  NAMESPACE: 3
  PLATFORM: 1
  SERVICE: 3
candidates with related Warning Events: 1
candidates with related workload context: 3
candidates with exact recent change: 0
candidates with exact drift: 0
```

Grouping is only by identical `scope.type + scope.subject`. `SUPPRESSED` means inhibited/silenced operational evidence, not resolved.

Infrastructure context remained bounded:

- Namespace membership is breadth context only, not affected-workload proof.
- Platform scope did not expand to all workloads.
- Service candidates did not receive guessed workload ownership.
- Recent change/drift attach only on exact subject identity.
- Event context remains supporting evidence, not root cause.

Current deterministic next-evidence recommendations:

```text
PROMETHEUS_ALERTMANAGER: 4
KUBERNETES_ENDPOINTSLICE_POD: 3
LOKI_CANDIDATE: 3
KUBERNETES_OBJECT: 1
PROMETHEUS_KUBERNETES: 1
```

Sensitive/causal guards passed:

```text
forbidden projected keys: none
raw URL markers: false
causal assertion markers: none
```

Detailed report:

```text
docs/reports/2026-08-15-m4-incident-candidates-live-test-gate.md
```

## Exact next step after PR #16 merge

Prefer a small read-only Kubernetes EndpointSlice/Pod ownership slice before adding Loki or OpenTelemetry.

Why this is the next useful slice:

- three current Service-scoped incident candidates explicitly require `KUBERNETES_ENDPOINTSLICE_POD` verification;
- current Service-to-workload relationships are selector-based inference and do not prove live routing;
- the existing `Service/monitoring/loki-headless` multiple-controller ambiguity also requires EndpointSlice/Pod ownership evidence;
- resolving this structural uncertainty improves topology, runtime attribution, and incident context before adding another telemetry engine.

Smallest intended scope:

1. add read-only observation for EndpointSlices and the minimum bounded Pod metadata needed for ownership/routing;
2. use EndpointSlice target references plus Pod owner references to derive evidence-backed Service -> Pod -> controller relations;
3. do not infer controller ownership from Pod names;
4. do not ingest Pod logs, environment variables, Secret values, mounted Secret content, service-account tokens, or sensitive connection data;
5. retain existing selector inference as a weaker relation where exact live routing evidence is unavailable;
6. surface ambiguity/unknown explicitly rather than forcing a controller match;
7. keep `mutation_allowed=false` and separate future control identity from observation identity;
8. use live acceptance before allowing the stronger relation to influence incident candidates.

Do not add Loki/OpenTelemetry in the same slice.

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

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, live gate outcomes, material blockers/risks, exact next step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
