# ADR 0013 — Incident Candidates Are Derived Evidence Groups, Not Root-Cause Conclusions

## Status

Accepted for Milestone 4 implementation pending live validation.

## Context

Milestone 4 now has several independently validated current evidence layers:

- Prometheus runtime target and alert evaluation state;
- Alertmanager handling state and conservative alert correlation;
- bounded Kubernetes Event evidence and alert/Event correlation;
- workload operational inventory and topology relations;
- history, diff, declared-vs-observed drift, and compact change context.

The next roadmap capability is to reduce operator cognitive load by grouping related current signals, showing bounded infrastructure context, and recommending the next verification step.

A naive implementation could create a single health score, merge unrelated scopes, treat inhibited alerts as resolved, or present temporal correlation as root cause. Those behaviors would violate the evidence contract.

## Decision

Create a derived artifact called `incident-candidates`.

An incident candidate is a compact evidence grouping for investigation. It is not a confirmed incident and is never a root-cause conclusion.

The artifact is generated only from current artifacts produced by the platform. This slice adds no infrastructure query, no RBAC, and no mutation.

## Grouping rule

Alert-attention records are grouped only when both fields are identical:

```text
scope.type
scope.subject
```

Examples:

```text
Service/monitoring/kube-prom-stack-kubelet
Namespace/monitoring
Platform/k3s-main
```

remain separate candidates even when they refer to the same namespace or cluster.

This avoids manufacturing a broader incident graph before evidence supports one.

## Candidate state

Candidate state is handling-aware:

```text
ACTIVE
SUPPRESSED
UNKNOWN
```

Rules:

- any `ACTIVE` alert makes the candidate `ACTIVE`;
- `UNKNOWN` or `UNPROCESSED` evidence yields `UNKNOWN` when no active alert exists;
- inhibited/silenced/suppressed-only groups are `SUPPRESSED`.

`SUPPRESSED` does not mean resolved. The underlying alert remains evidence.

## Event context

Kubernetes Event relations are reused from the accepted Event-correlation artifact by `attention_id`.

No new Event matching logic is introduced here.

A related Event remains supporting temporal/object context and is never presented as cause.

## Infrastructure context

Impact/context is deliberately scoped:

### Workload scope

An exact workload identity can attach the matching workload inventory entity.

### Service scope

Related workloads may be attached only through an existing inventory Service-to-workload relation.

The current relation is selector-based controller inference. EndpointSlice/Pod routing is not proven.

### Namespace scope

Workloads in the namespace can be shown only as breadth/context. Namespace membership does not mean every workload is affected.

### Node scope

Current workload placement is unknown because Pods and owner references are not in the observation model. A live verification recommendation is emitted instead of guessing placement.

### Platform scope

Only cluster-level inventory counts are shown. Platform scope never expands into an assertion that all workloads are affected.

## Drift and recent change

Recent change and drift are attached to a candidate only when their subject identity exactly matches the candidate subject.

Namespace membership, naming similarity, or temporal proximity do not automatically promote drift/change into a candidate.

A matching change or drift record remains supporting evidence rather than root cause.

## Recommended drill-down

Recommendations are deterministic missing-evidence or fresh-verification checks.

Examples include:

- refresh incomplete Prometheus/Alertmanager evidence;
- refresh partial/failed Kubernetes Event evidence;
- verify the current alert condition;
- verify current EndpointSlice/Pod ownership for a Service with no supported workload mapping;
- verify Pod/workload placement for Node scope;
- verify the current state of an Event involved object;
- inspect exact recent change or drift on the same subject;
- verify cluster-level rule inputs for a platform alert;
- identify Loki as a candidate next evidence source when an active signal remains unexplained and no related structured Warning Event is available.

A recommendation does not execute the check.

## Runtime placement

The existing Kubernetes/observability collection service first writes its current artifacts.

A systemd `ExecStartPost` then runs the derived incident builder over:

```text
alert-attention.json
kubernetes-event-correlation.json
inventory.json
change-context.json
```

and writes:

```text
incident-candidates.json
incident-candidates.md
```

The derived builder contains no `kubectl`, HTTP, subprocess, Loki, OpenTelemetry, Jenkins, or other infrastructure client.

## Consequences

Positive:

- operators receive fewer, scope-aware investigation units;
- active and inhibited/suppressed evidence stays distinct;
- current Event, drift, change, and inventory context can be viewed together;
- the next useful evidence source can be selected from deterministic gaps rather than by integrating every telemetry system in advance;
- no new infrastructure permission is needed.

Tradeoffs:

- exact-scope grouping can leave related operational symptoms in separate candidates;
- namespace impact context may be broad and must not be interpreted as affected workload proof;
- Service impact remains limited by selector-based controller inference;
- Node impact remains incomplete without Pod scheduling/owner evidence;
- no causal ranking is attempted in this slice.

## Deferred

- Loki log ingestion/query;
- OpenTelemetry trace correlation;
- Jenkins/Git deployment-event ingestion;
- Pod/EndpointSlice ownership observation;
- cross-scope incident graph merging;
- root-cause hypotheses produced by AI;
- business-service impact models;
- automated remediation.
