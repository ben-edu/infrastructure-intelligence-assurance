# Milestone 4 Incident Candidates Live Test Gate — 2026-08-15

## Status

Pending management-host live acceptance.

## Scope

Validate derived incident grouping, infrastructure context, and deterministic drill-down recommendations using only already-generated current evidence.

## Required acceptance evidence

1. Full repository tests pass.
2. Existing Git, Kubernetes, Prometheus, Alertmanager, Event, inventory, drift, and change-context generation remain healthy.
3. No Kubernetes RBAC change is introduced by this slice.
4. Normal systemd execution emits:

```text
/var/lib/infra-assurance/evidence/incident-candidates.json
/var/lib/infra-assurance/evidence/incident-candidates.md
```

5. Incident runtime performs no infrastructure query; it reads only current local evidence files.
6. `mutation_allowed=false`.
7. Candidate count is less than or equal to alert-attention record count because grouping occurs only on identical supported scope type + subject.
8. Alerts with the same exact scope/subject can group; different scope types or subjects remain separate.
9. `ACTIVE`, `SUPPRESSED`, and `UNKNOWN` remain distinct. Inhibited/silenced alerts are not presented as resolved.
10. Event context is inherited only from the accepted Event-correlation artifact and remains supporting evidence, not root cause.
11. Workload context follows only supported inventory relations.
12. Service workload context retains selector-inference caveats.
13. Namespace workload context is explicitly breadth context and not affected-workload proof.
14. Platform scope does not expand into all workloads.
15. Node scope does not invent placement without Pod evidence.
16. Recent change and drift attach only on exact subject identity.
17. Recommended checks are deterministic and have `live_verification_required=true`.
18. A recommendation such as `LOKI_CANDIDATE` does not execute a Loki query.
19. Sensitive/free-form material is not introduced by the derived artifact.
20. The top-level recommended evidence targets provide a compact basis for choosing the next specialized source.

## Expected live interpretation

The gate does not require a particular number of incident candidates or Event matches because current alert state is time-varying.

A candidate may legitimately be `SUPPRESSED` if its current alerts are inhibited/silenced. It remains operational evidence.

An `ACTIVE` platform candidate such as a cluster capacity alert may recommend verifying current rule inputs/capacity and possibly logs, but must not mark all workloads affected.

A Service candidate without a supported workload relation should recommend EndpointSlice/Pod ownership verification rather than guessing ownership.

## Trust boundary

This artifact is derived current investigation context. It does not replace Prometheus, Alertmanager, Kubernetes, Git, history, inventory, or future log/trace systems. It does not establish root cause, business impact, or remediation authority.
