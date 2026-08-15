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
- stable main checkpoint: `a9feef8957f74d0cb9ed4299fd86778de0bb2fe4`
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

Accepted runtime included 21 active targets, all UP, with 11 target paths attributed to workloads and 10 unattributed. Prometheus runtime state is signal-scoped and is not generic application-health proof.

### Milestone 4 — Alertmanager handling correlation

PR #13 is merged and live accepted.

Accepted live run included 11 Alertmanager alerts: 2 ACTIVE and 9 INHIBITED, with all 11 uniquely correlated to Prometheus. Scope remained 6 Service, 3 Namespace, 2 Platform, 0 Workload, 0 Node. No unsupported workload ownership was invented.

### Milestone 4 — Kubernetes Event correlation

PR #14 is squash-merged at:

```text
c97d5197bf278192055d87bde7f47705280038ad
```

Accepted live run:

```text
pytest: 125 passed in 0.89s
observer service: status=0/SUCCESS
Git declared source: COMPLETE
Prometheus source: COMPLETE
Alertmanager source: COMPLETE
Kubernetes Event source: COMPLETE
mutation_allowed: false
```

Event RBAC remained read-only:

```text
list Events cluster-wide: yes
create Event: no
list Pods cluster-wide: no
list Secrets cluster-wide: no
create Deployment: no
```

Current accepted Event evidence had one one-hour Warning record:

```text
ProbeWarning
Pod/moodle/moodle-b49d869bd-flsr6
count: 758740
```

The same cycle had 10 alert-attention records and 10 Event-correlation records. One Namespace/moodle attention record received the Warning Event as namespace-membership context. Nine had `NO_DIRECT_EVENT_MATCH`. Platform alerts were not broadly matched. Pod-name controller inference was not introduced.

Detailed report:

```text
docs/reports/2026-08-15-m4-kubernetes-event-correlation-live-test-gate.md
```

## Active work — PR #16 incident candidates and drill-down

- PR: `#16 Milestone 4 incident candidates and drill-down`
- branch: `feature/m4-incident-candidates`
- base: `a9feef8957f74d0cb9ed4299fd86778de0bb2fe4`
- status: Draft; do not merge until management-host live acceptance passes
- package version on branch: `0.12.0`

### Goal

Prove the roadmap capability:

```text
signal correlation -> incident grouping -> bounded infrastructure context -> recommended drill-down
```

before adding another telemetry engine.

### No-new-query boundary

This slice adds no infrastructure RBAC and performs no new infrastructure query.

A systemd `ExecStartPost` reads only already-generated current local artifacts:

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

The incident builder contains no `kubectl`, HTTP client, subprocess, Loki, OpenTelemetry, or Jenkins query.

### Grouping semantics

Candidates group only by identical:

```text
scope.type + scope.subject
```

Service/Namespace/Platform scopes never merge merely because they share a namespace or cluster.

Candidate state is:

```text
ACTIVE | SUPPRESSED | UNKNOWN
```

An inhibited/silenced-only candidate is `SUPPRESSED`, not resolved.

### Infrastructure context

- WORKLOAD: exact identity only.
- SERVICE: existing Service-to-workload selector inference only; EndpointSlice/Pod routing is not proven.
- NAMESPACE: workload membership is breadth context only, not affected-workload proof.
- NODE: workload placement remains unknown without Pod evidence; verify live instead of guessing.
- PLATFORM: cluster counts only; all workloads are not automatically classified as impacted.

Recent changes and drift attach only when their subject exactly matches the candidate subject.

### Deterministic drill-down

Recommended checks can include:

```text
VERIFY_ALERT_CONDITION_CURRENT
REFRESH_ALERT_EVIDENCE
REFRESH_KUBERNETES_EVENT_EVIDENCE
VERIFY_SERVICE_ENDPOINT_OWNERSHIP
VERIFY_NODE_WORKLOAD_PLACEMENT
VERIFY_RELATED_EVENT_OBJECT_STATE
REVIEW_EXACT_RECENT_CHANGE
VERIFY_EXACT_DECLARED_OBSERVED_DRIFT
VERIFY_PLATFORM_SIGNAL_INPUTS
CHECK_SCOPE_LOGS_IF_NEEDED
```

`LOKI_CANDIDATE` is a recommendation target only. This PR does not query Loki.

Relevant docs:

```text
docs/decisions/0013-incident-candidates-are-derived-evidence-groups.md
docs/milestone-4-incident-candidates.md
docs/reports/2026-08-15-m4-incident-candidates-live-test-gate.md
```

## Exact next step

Run PR #16 management-host acceptance:

1. fetch/reset branch;
2. run full pytest;
3. bootstrap/refresh the normal observer;
4. verify systemd `ExecStartPost` succeeds;
5. inspect `incident-candidates.json` and `.md`;
6. confirm candidate count is bounded by current alert-attention count;
7. inspect ACTIVE/SUPPRESSED/UNKNOWN counts and exact grouping;
8. inspect related workload/route/PVC context and caveats;
9. verify current Event relations remain supporting context, not cause;
10. inspect exact-subject recent change/drift attachment;
11. inspect deterministic recommended checks and `recommended_next_evidence_targets`;
12. verify no RBAC expansion and no new query path;
13. verify sensitive/free-form/raw URL fields are absent;
14. update live report and merge only if semantics are correct.

Use live results to choose the next specialized source. Do not preselect Loki/OpenTelemetry/Jenkins before the candidate recommendations show which missing evidence is actually useful.

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
