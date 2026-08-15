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

### Milestone 4 — Prometheus runtime intelligence

Accepted and ready for merge through PR #10.

Exact read-only proxy boundary:

```text
namespace: monitoring
resource: services/proxy
resourceName: kube-prom-stack-prometheus:9090
verb: get
```

Accepted live run:

```text
pytest: 102 passed in 0.74s
Prometheus source: COMPLETE
active targets: 21
  up: 21
  down: 0
  unknown: 0
  attributed to workloads: 11
  unattributed: 10
active alerts: 11
  firing: 11
  pending: 0
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

Denied in the accepted gate:

- unrelated Service proxy in `monitoring`;
- same proxy identity in `default`;
- unqualified Prometheus Service proxy;
- Secret listing;
- Kubernetes mutation.

The 11 firing alerts were deliberately not force-mapped to workloads. Current labels identify Services such as `kube-prom-stack-kubelet` where no current evidence-backed Service-to-controller inference exists in the relevant scope. The runtime records `PROMETHEUS_ALERT_WORKLOAD_MAPPING_UNRESOLVED` instead of inventing ownership.

Likewise, 10 targets remain unattributed where no current controller-level mapping is supported.

Prometheus remains authoritative for target health and alert evaluation. `PROMETHEUS_TARGETS_UP` is scrape-target evidence, not generic application-health proof.

Detailed acceptance report:

```text
docs/reports/2026-08-15-m4-prometheus-runtime-live-test-gate.md
```

## Exact next step after PR #10 merge

Continue Milestone 4 with a small Alertmanager correlation slice around the 11 real active alerts.

Preferred scope:

- observe existing Alertmanager read-only;
- capture only safe alert-handling state such as active/silenced/inhibited status where the API supports it;
- exclude receiver configuration, credentials, free-form annotations, notification payloads, and other sensitive data;
- correlate Alertmanager records with normalized Prometheus alert identities/allowlisted labels;
- retain namespace/node/platform-scoped alerts as first-class operational evidence when workload attribution is unsupported;
- do not invent workload ownership for kubelet/node/platform alerts;
- produce a compact alert-attention projection suitable for later cross-signal incident grouping.

Do not expand to Loki/OpenTelemetry yet. First prove that Prometheus alert evaluation and Alertmanager handling context can be joined reliably.

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
/var/lib/infra-assurance/evidence/prometheus-runtime.json
```

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, live gate outcomes, material blockers/risks, exact next step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
