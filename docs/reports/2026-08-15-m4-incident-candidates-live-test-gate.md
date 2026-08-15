# Milestone 4 Incident Candidates Live Test Gate — 2026-08-15

## Status

Accepted on `mgmt-automation`.

## Tested implementation

```text
branch: feature/m4-incident-candidates
head: 855d8acde041d6896d3172ba3a949134dd6d201e
pytest: 134 passed in 0.94s
observer service: status=0/SUCCESS
incident ExecStartPost: status=0/SUCCESS
mutation_allowed: false
```

## No-new-query / RBAC gate

The incident projection ran as `ExecStartPost` over current local evidence only.

```text
list Pods: no
list EndpointSlices: no
list Secrets: no
create Deployment: no
query-capable client markers in incident implementation: none
```

No RBAC expansion was introduced by this slice.

## Current source trust

```text
alert_attention: COMPLETE
kubernetes_events: COMPLETE
inventory: COMPLETE
change_context: COMPLETE
drift: EVALUATED
```

## Live candidate result

```text
alert attention records: 10
incident candidates: 7
active candidates: 4
suppressed candidates: 3
unknown candidates: 0
candidates requiring live verification: 7
candidates with related Warning Events: 1
candidates with related workloads: 3
candidates with exact recent change: 0
candidates with exact drift: 0
```

Candidate scope distribution:

```text
NAMESPACE: 3
PLATFORM: 1
SERVICE: 3
```

Current grouping preserved handling semantics:

- three Namespace candidates were `ACTIVE`;
- the Platform candidate was `ACTIVE` and grouped `KubeCPUOvercommit` plus `Watchdog` on the identical platform subject;
- the three Service candidates were `SUPPRESSED` because their `CPUThrottlingHigh` alerts were inhibited;
- no candidate was classified `UNKNOWN` in this run.

## Event context

One accepted Event relation was inherited without rematching raw Events:

```text
candidate: Namespace/moodle
Event: ProbeWarning
subject: Pod/moodle/moodle-b49d869bd-flsr6
basis: namespace-scoped supporting context from the accepted Event-correlation artifact
```

The Kubernetes-reported occurrence count was `758980` in this run. It is retained as structured evidence and is not interpreted as severity or root cause.

## Infrastructure context guards

Namespace candidates displayed namespace-member workloads only as breadth context. Their caveat explicitly states that namespace membership does not mean every workload is affected.

The Platform candidate retained only cluster-level context:

```text
namespaces_total: 19
workloads_total: 68
related workloads: 0
```

The three Service candidates had no supported workload relationship. The projection did not guess ownership and instead recommended EndpointSlice/Pod verification.

No exact-subject recent change or drift matched a current candidate in this run. The known Ingress drift therefore remained separate rather than being attached to an unrelated incident candidate.

## Recommended evidence targets

```text
PROMETHEUS_ALERTMANAGER: 4
KUBERNETES_ENDPOINTSLICE_POD: 3
LOKI_CANDIDATE: 3
KUBERNETES_OBJECT: 1
PROMETHEUS_KUBERNETES: 1
```

These are deterministic drill-down recommendations, not evidence already collected. In particular, `LOKI_CANDIDATE` did not execute a Loki query.

The strongest new structural evidence gap exposed by this run is `KUBERNETES_ENDPOINTSLICE_POD`: three Service-scoped candidates cannot currently be related to workload controllers because current Service-to-controller topology is selector inference only. This also aligns with the pre-existing Service/controller ambiguity in topology evidence.

## Sensitive / causal guard

```text
forbidden projected keys: none
raw URL markers: false
causal assertion markers: none
```

The artifact did not introduce Event message/note text, arbitrary annotations, receivers, generator URLs, instance endpoints, credentials, tokens, private keys, Secret payloads, or complete sensitive connection strings.

## Acceptance conclusion

Accepted.

The slice proves the roadmap sequence:

```text
signal correlation
-> incident candidate grouping
-> bounded infrastructure context
-> deterministic recommended drill-down
```

without introducing a health score, root-cause claim, business-impact claim, new infrastructure query, or remediation authority.

## Next evidence slice

Prefer a small read-only Kubernetes EndpointSlice/Pod ownership slice before adding Loki or OpenTelemetry. Its goal should be to resolve current Service routing/controller ownership using authoritative EndpointSlice membership plus Pod owner references, while storing only bounded non-sensitive Pod metadata. It must not ingest Pod logs, environment variables, Secret values, or container runtime secrets.
