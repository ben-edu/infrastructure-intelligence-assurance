# Milestone 4 — Incident Candidates and Deterministic Drill-down

## Goal

Turn already-generated current evidence into compact investigation candidates without adding a new telemetry source or weakening trust semantics.

## Inputs

This slice reads only current local evidence artifacts:

```text
alert-attention.json
kubernetes-event-correlation.json
inventory.json
change-context.json
```

It performs no Kubernetes, Prometheus, Alertmanager, Loki, OpenTelemetry, Jenkins, GitHub, or other infrastructure query.

## Outputs

```text
/var/lib/infra-assurance/evidence/incident-candidates.json
/var/lib/infra-assurance/evidence/incident-candidates.md
```

`mutation_allowed=false` remains binding.

## Candidate grouping

One candidate is created per identical:

```text
alert attention scope type + subject
```

Multiple alerts for one Service may group together. Service, Namespace, Workload, Node, and Platform scopes do not collapse into one candidate merely because they are nearby or share a namespace.

## Candidate contents

Each candidate contains:

- current alert handling projection;
- `ACTIVE | SUPPRESSED | UNKNOWN` candidate state;
- already-derived related Warning Event context;
- exact-subject recent change context;
- exact-subject declared-vs-observed drift context;
- bounded related infrastructure context;
- deterministic recommended live verification/drill-down checks;
- evidence IDs and explicit caveats.

## Impact/context rules

`impact_context` is not business-impact classification.

- Workload: exact inventory identity.
- Service: existing Service-to-controller selector inference only.
- Namespace: namespace membership breadth context only.
- Node: placement remains unknown without Pod evidence.
- Platform: cluster counts only; workloads are not automatically marked affected.

Ingress/PVC context is attached only through already-related inventory workloads.

## Drill-down rules

Recommended checks are generated from missing or insufficient evidence.

The output may identify a specialized source such as Loki as the next useful evidence target, but this slice does not query that source.

Examples:

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

## Runtime integration

The normal observer service keeps its existing collection path.

After the current artifacts are atomically written, `ExecStartPost` runs the derived incident builder. This avoids changing prior collector semantics and makes the no-new-query boundary directly testable.

## Non-goals

This slice does not:

- claim root cause;
- produce a global health score;
- query Loki;
- query OpenTelemetry;
- query Jenkins/Git deployment history;
- add Pod or EndpointSlice RBAC;
- infer Pod controller ownership from names;
- infer business-service impact;
- mutate infrastructure.
