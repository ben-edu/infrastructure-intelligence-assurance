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
- stable main before PR #13 merge: `e0e3fb378501fda0630800755b085fb0f749af23`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- runtime user: `infra-assurance`
- systemd oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

The oneshot being `inactive (dead)` after `status=0/SUCCESS` is expected.

## Stable implementation

### Milestone 0

Evidence contract complete. Failed observation is never absence; declared/observed planes remain separate; inference is not fact; sensitive values are excluded.

### Milestone 1

Kubernetes read-only evidence, operational context, topology, and read-only planning preflight complete and live validated.

### Milestone 2

History, diff, dedicated Git declared-state observation, drift, and compact change context complete and live validated.

Git source:

```text
ben-edu/api-cluster-infra
branch: main
last repeatedly observed revision: 5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
accepted declared records: 27
```

Known real drift retained intentionally:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

### Milestone 3

Workload operational inventory and Prometheus Operator configuration coverage complete for current slices and live validated.

Accepted inventory snapshot included 68 workloads. Prometheus Operator coverage had 7 `OPERATOR_MONITOR_MATCH` workloads and 61 `NO_OPERATOR_MONITOR_MATCH`; configuration coverage is not scrape-health evidence.

### Milestone 4 — Prometheus runtime intelligence

PR #10 is squash-merged and live accepted.

Exact proxy boundary:

```text
monitoring / kube-prom-stack-prometheus:9090 / services/proxy / get
```

Accepted live run:

```text
pytest: 102 passed
Prometheus source: COMPLETE
active targets: 21
  up: 21
  down: 0
  attributed to workloads: 11
  unattributed: 10
active alerts: 11
  firing: 11
  attributed to workloads: 0
  unattributed: 11
workload runtime states:
  PROMETHEUS_TARGETS_UP: 7
  NO_RUNTIME_SIGNAL_MATCH: 61
runtime/inventory cardinality: 68/68
forbidden projected keys: none
raw URL markers: false
mutation_allowed: false
```

Unsupported Service-to-controller alert attribution remains explicit rather than being force-mapped to workloads.

Detailed report:

```text
docs/reports/2026-08-15-m4-prometheus-runtime-live-test-gate.md
```

### Milestone 4 — Alertmanager handling correlation

PR #13 implementation is live accepted and ready to merge.

Live-discovered and reviewed source:

```text
monitoring / kube-prom-stack-alertmanager:9093
```

Exact additional proxy boundary:

```text
namespace: monitoring
resource: services/proxy
resourceName: kube-prom-stack-alertmanager:9093
verb: get
```

Accepted live RBAC:

```text
Prometheus exact proxy             : yes
Alertmanager exact proxy           : yes
alertmanager-operated proxy        : no
Unqualified Alertmanager proxy     : no
Alertmanager proxy / default       : no
Secrets                            : no
Create Deployment                  : no
```

Accepted repository/runtime gate:

```text
pytest: 112 passed in 0.84s
observer service: status=0/SUCCESS
Git declared source: COMPLETE
Prometheus source: COMPLETE
Alertmanager source: COMPLETE
mutation_allowed: false
```

Current Alertmanager evidence:

```text
alerts_total: 11
active: 2
inhibited: 9
silenced: 0
unprocessed: 0
silences_total: 0
```

Prometheus/Alertmanager correlation:

```text
MATCHED: 11
UNRESOLVED: 0
AMBIGUOUS: 0
```

This is alert-source correlation, not workload ownership.

Current alert-attention scope:

```text
attention_total: 11
scope_service: 6
scope_namespace: 3
scope_platform: 2
scope_workload: 0
scope_node: 0
```

Active platform-scoped records currently include:

```text
KubeCPUOvercommit severity=warning
Watchdog severity=none
```

Inhibited records include `CPUThrottlingHigh` and `InfoInhibitor` at Service/Namespace scope. No unsupported workload owner was invented.

Sensitive/free-form guard passed:

```text
forbidden projected keys: none
raw URL markers: false
```

Persisted Alertmanager evidence excludes receiver names/configuration, free-form annotations, generator URLs, arbitrary `instance` labels, silence comments/matchers/creator identity, notification payloads, credentials, and Secret values.

Relevant docs:

```text
docs/decisions/0011-alertmanager-handling-state-and-conservative-correlation.md
docs/milestone-4-alertmanager-correlation.md
docs/reports/2026-08-15-m4-alertmanager-correlation-live-test-gate.md
```

## Exact next step

After PR #13 merge, continue Milestone 4 with a Kubernetes Event correlation slice.

Smallest useful scope:

1. add read-only observation for current Kubernetes Events;
2. persist only bounded recent event evidence with safe structured fields such as type, reason, involved-object identity, timestamps/count, and evidence IDs;
3. do not persist arbitrary raw event messages until an explicit sanitization policy is reviewed;
4. correlate events directly when involvedObject identity matches observed Node/Workload/Service/PVC objects;
5. relate Pod events to workload controllers only if a safe ownership evidence path is added; do not infer controller ownership from Pod names;
6. enrich current alert attention with related recent Kubernetes event evidence without promoting correlation to root cause;
7. preserve explicit stale/failed/unknown semantics and `mutation_allowed=false`;
8. keep Kubernetes Event RBAC read-only and do not expand to Loki/OpenTelemetry in the same slice.

Goal: move from alert correlation toward evidence-backed incident grouping and recommended drill-down without introducing a replacement monitoring engine.

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
