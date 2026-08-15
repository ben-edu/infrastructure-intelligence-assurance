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
- stable main checkpoint: `7f271d8f4fcd1e4408bc4b0e864b3fffe4c4c11e`
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

```text
source: monitoring/kube-prom-stack-prometheus:9090
source status: COMPLETE
active targets: 21
  up: 21
  attributed to workloads: 11
  unattributed: 10
active Prometheus alerts: 11
  firing: 11
workload runtime states:
  PROMETHEUS_TARGETS_UP: 7
  NO_RUNTIME_SIGNAL_MATCH: 61
```

Prometheus runtime signal is not generic application-health proof.

### Milestone 4 — Alertmanager handling correlation

PR #13 is squash-merged at:

```text
7f271d8f4fcd1e4408bc4b0e864b3fffe4c4c11e
```

Live acceptance:

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

The two current active platform-scoped records include `KubeCPUOvercommit` and `Watchdog`. Inhibited records include `CPUThrottlingHigh` and `InfoInhibitor`. Correlation between Prometheus and Alertmanager does not imply workload ownership.

Detailed reports:

```text
docs/reports/2026-08-15-m4-prometheus-runtime-live-test-gate.md
docs/reports/2026-08-15-m4-alertmanager-correlation-live-test-gate.md
```

## Active work — PR #14 Kubernetes Event correlation

- PR: `#14 Milestone 4 Kubernetes Event correlation`
- branch: `feature/m4-kubernetes-event-correlation`
- status: Draft; do not merge until management-host live acceptance passes
- package version on branch: `0.11.0`

### Goal

Add bounded recent Kubernetes Event evidence and relate recent Warning Events to current alert attention without storing free-form Event messages or claiming root cause.

### New read-only permission

```text
core/v1 events: get, list, watch
```

Must remain denied:

```text
create events
list Secrets
Kubernetes mutation
```

No Pod permission is added.

### Event source contract

Runtime query:

```text
kubectl get events --all-namespaces -o json
```

Default bounds:

```text
recent window: 3600 seconds
maximum persisted recent events: 500
```

Persisted Event fields:

- `WARNING | NORMAL | UNKNOWN` type;
- safe reason token or `REDACTED_REASON`;
- involved-object API version/kind/namespace/name;
- first/last occurrence;
- occurrence count;
- evidence/observation freshness IDs.

Explicitly excluded:

- Event `message` / `note`;
- source host / reporting instance;
- arbitrary labels/annotations;
- raw object UIDs;
- credentials, Secret values, connection strings.

### Event/alert correlation

Only recent Warning Events participate.

Supported bases:

```text
DIRECT_OBJECT_IDENTITY
NAMESPACE_SCOPE_MEMBERSHIP
RECENT_KUBERNETES_WARNING_EVENT
```

Rules:

- exact Service/Node/Workload subject can correlate directly;
- Namespace attention can receive Warning Event context for objects in that namespace;
- Platform alerts are not automatically matched to all Events;
- Pod Events are not promoted to workload ownership by Pod-name heuristics;
- Event correlation is supporting context, not root cause.

Source failure becomes `FAILED_TO_OBSERVE`. A bounded-window truncation becomes `PARTIAL`. Only a `COMPLETE` Event source can support `NO_DIRECT_EVENT_MATCH`; otherwise no-match is `UNKNOWN`.

New artifacts:

```text
/var/lib/infra-assurance/evidence/kubernetes-event-runtime.json
/var/lib/infra-assurance/evidence/kubernetes-event-runtime.md
/var/lib/infra-assurance/evidence/kubernetes-event-correlation.json
/var/lib/infra-assurance/evidence/kubernetes-event-correlation.md
```

Relevant docs:

```text
docs/decisions/0012-kubernetes-events-are-bounded-supporting-evidence.md
docs/milestone-4-kubernetes-event-correlation.md
docs/reports/2026-08-15-m4-kubernetes-event-correlation-live-test-gate.md
```

## Exact next step

Run PR #14 management-host acceptance:

1. fetch/reset the branch;
2. run the full pytest suite;
3. bootstrap the observer;
4. verify `list events=yes`, `create events=no`, `list secrets=no`, mutation=no;
5. inspect current Event source status, window size, Warning/Normal counts, and truncation;
6. inspect current Event/alert-attention matches and their explicit basis;
7. verify raw `message`, source host/reporting instance, UID, arbitrary metadata, credentials, URLs, and Secret-bearing fields are absent;
8. treat real Warning Events as evidence, not test failures;
9. update the live report and merge only if trust semantics are correct.

Do not expand to Loki/OpenTelemetry in this same slice.

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
