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
- stable main before PR #14 merge: `7f271d8f4fcd1e4408bc4b0e864b3fffe4c4c11e`
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

PR #13 is squash-merged at:

```text
7f271d8f4fcd1e4408bc4b0e864b3fffe4c4c11e
```

Accepted run:

```text
pytest: 112 passed in 0.84s
Prometheus source: COMPLETE
Alertmanager source: COMPLETE
Alertmanager alerts: 11
  ACTIVE: 2
  INHIBITED: 9
silences: 0
Prometheus correlation:
  MATCHED: 11
  UNRESOLVED: 0
  AMBIGUOUS: 0
alert-attention scope:
  SERVICE: 6
  NAMESPACE: 3
  PLATFORM: 2
  WORKLOAD: 0
  NODE: 0
forbidden projected keys: none
raw URL markers: false
mutation_allowed: false
```

Prometheus/Alertmanager correlation does not imply workload ownership.

### Milestone 4 — Kubernetes Event correlation

PR #14 implementation is live accepted and ready to merge.

Branch:

```text
feature/m4-kubernetes-event-correlation
```

Tested head:

```text
0e656734eb53b8b3f5789313ed29b3d8a74c9121
```

Accepted repository/runtime gate:

```text
pytest: 125 passed in 0.89s
observer service: status=0/SUCCESS
Git declared source: COMPLETE
Prometheus source: COMPLETE
Alertmanager source: COMPLETE
Kubernetes Event source: COMPLETE
mutation_allowed: false
```

Accepted Event RBAC:

```text
list Events cluster-wide: yes
create Event: no
list Pods cluster-wide: no
list Secrets cluster-wide: no
create Deployment: no
```

Event source bounds:

```text
window_seconds: 3600
max_events: 500
window_truncated: false
```

Current live Event evidence in the acceptance run:

```text
events_seen_from_api: 1
events_recent: 1
events_warning: 1
events_normal: 0
reason: ProbeWarning
subject: Pod/moodle/moodle-b49d869bd-flsr6
count: 758740
```

The occurrence count is retained as Kubernetes-reported structured evidence. It is not interpreted as severity or root cause.

The alert-attention projection contained 10 records in this run. This differs from the earlier 11-alert snapshot because alert state is time-varying. Event correlation used the same-cycle current attention projection and preserved cardinality:

```text
alert attention records: 10
event correlation records: 10
attention_with_related_warning_events: 1
attention_without_direct_warning_match: 9
attention_event_correlation_unknown: 0
```

The one relation is:

```text
attention: Namespace/moodle
handling: INHIBITED
related Event: ProbeWarning on Pod/moodle/moodle-b49d869bd-flsr6
basis:
  NAMESPACE_SCOPE_MEMBERSHIP
  RECENT_KUBERNETES_WARNING_EVENT
```

This is supporting namespace context only. Pod-name controller inference is not implemented.

Both current platform-scoped alert-attention records had `NO_DIRECT_EVENT_MATCH`; platform alerts are not broadly matched to cluster Events.

Sensitive/free-form guard passed:

```text
forbidden projected keys: none
raw URL markers: false
```

Persisted Event evidence excludes message/note text, source/reporting host, arbitrary annotations/labels, raw UID, credentials, and Secret values. Unsafe/free-form Event reasons are redacted.

Detailed report:

```text
docs/reports/2026-08-15-m4-kubernetes-event-correlation-live-test-gate.md
```

## Exact next step after PR #14 merge

Continue Milestone 4 with a derived incident-grouping and drill-down slice before adding another telemetry engine.

Smallest useful scope:

1. consume only already-generated current artifacts: alert attention, Kubernetes Event correlation, Prometheus runtime, inventory/topology, drift, diff/change context;
2. create compact evidence-backed `incident-candidates` grouped by supported shared scope/subject and current signal relations;
3. distinguish `ACTIVE`, `INHIBITED`, drift, recent change, related Event context, and unknown evidence instead of flattening them into one health score;
4. produce an impact summary using existing inventory relationships without claiming business impact that is not modeled;
5. emit recommended drill-down/live verification checks from deterministic missing-evidence rules;
6. never label a correlation as root cause; hypotheses must remain explicit inference with evidence IDs and confidence/basis;
7. do not query Loki/OpenTelemetry/Jenkins in this slice; identify which candidate would actually benefit from the next specialized source first;
8. keep the slice derived/read-only with `mutation_allowed=false` and no new infrastructure RBAC.

Goal: prove the roadmap capability `signal correlation -> incident grouping -> impact summary -> recommended drill-down` using the evidence already collected, reducing operator cognitive load before broadening telemetry ingestion.

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
