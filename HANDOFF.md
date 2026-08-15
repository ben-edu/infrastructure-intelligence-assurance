# Project Handoff

This file is the compact continuation checkpoint for the Infrastructure Intelligence & Assurance Platform.

It is operational state, not the architecture contract. Project Sources remain authoritative for goals, trust principles, roadmap, and operating rules. This file records where implementation actually is now.

## Resume protocol

For a fresh ChatGPT/AI session:

1. Read the Project Sources.
2. Read this `HANDOFF.md` from `main`.
3. Check open pull requests in `ben-edu/infrastructure-intelligence-assurance`.
4. If there is an active project PR, prefer the `HANDOFF.md` from that PR branch when present and inspect that PR metadata.
5. Read only the ADR, milestone document, and live-test report directly relevant to the active slice.
6. Do not reconstruct project state from chat memory when repository evidence is available.

This protocol is intentionally narrow to reduce context-window consumption.

## Repository

- Repository: `ben-edu/infrastructure-intelligence-assurance`
- Stable branch: `main`
- Stable implementation commit before this continuity document: `283b1ee51b18a9ac629b56ae021654f6e698fd24`
- Management host checkout: `~/projects/infrastructure-intelligence-assurance`
- Management host: `mgmt-automation`
- Kubernetes cluster identity: `k3s-main`

## Stable implementation status

### Milestone 0 — Evidence Contract

Complete.

Core semantics:

- `existence`: `PRESENT | ABSENT | UNKNOWN`
- `observation_status`: `COMPLETE | PARTIAL | FAILED_TO_OBSERVE`
- freshness: `CURRENT | STALE`
- failed or insufficient observation never becomes `ABSENT`
- declared and observed planes remain separate
- sensitive values are excluded from evidence and AI context

### Milestone 1 — Kubernetes Vertical Slice

Complete and live validated.

Read-only Kubernetes observer currently covers:

- Namespace
- Node
- Deployment
- StatefulSet
- DaemonSet
- Service
- Ingress
- PersistentVolumeClaim

Derived artifacts include operational context, topology, and read-only deployment planning preflight.

### Milestone 2 — History, Diff, Git Drift

Complete and live validated.

Implemented:

- bounded immutable Kubernetes snapshot history
- trust-aware previous/current diff
- dedicated read-only Git declared-state observer
- declared-vs-observed drift
- compact change context

Git declared source:

- repository: `ben-edu/api-cluster-infra`
- branch: `main`
- dedicated read-only deploy key
- latest repeatedly observed revision: `5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4`
- 27 normalized declared records in the accepted live run

Known real drift retained intentionally:

- subject: `Ingress/validation/nginx-validation`
- Git declared host: `k3s-master.soria-academie.fr`
- live observed host: `k3s-master.behnam.fr`
- this is evidence-backed drift; no automatic correction was made

### Milestone 3 — Operational Inventory / Observability Configuration Coverage

Complete for the implemented slices and live validated.

Workload-centric inventory covers Deployment, StatefulSet, and DaemonSet entities and joins:

- current Kubernetes evidence
- Git declaration coverage and workload drift
- Service relationships
- Ingress route candidates
- PVC relationships
- latest change state
- topology/drift attention
- Prometheus Operator configuration coverage

Latest accepted live inventory cardinality:

- workloads: 68
- Git-declared workloads: 9
- workloads outside configured Git scope: 59
- Service links: 77
- Ingress route candidates: 26
- PVC links: 18

Prometheus Operator configuration coverage accepted live:

- Prometheus objects: 1
- ServiceMonitors: 11
- PodMonitors: 0
- selected ServiceMonitors: 9
- workload `OPERATOR_MONITOR_MATCH`: 7
- workload `NO_OPERATOR_MONITOR_MATCH`: 61
- unknown coverage: 0

Important semantic boundary:

`OPERATOR_MONITOR_MATCH` means a current evidence-backed Prometheus Operator configuration path exists. It does not prove target health or successful scraping.

## Runtime installation

Observer runtime:

- OS service user: `infra-assurance`
- source: `/opt/infra-assurance/src`
- config: `/etc/infra-assurance`
- current evidence: `/var/lib/infra-assurance/evidence`
- Kubernetes history: `/var/lib/infra-assurance/history/kubernetes`
- Git cache/state: `/var/lib/infra-assurance/git`
- normalized declared state: `/var/lib/infra-assurance/declared/current`
- systemd oneshot: `infra-assurance-kubernetes.service`
- timer: `infra-assurance-kubernetes.timer`
- cadence: every 5 minutes

The oneshot service being `inactive (dead)` after `status=0/SUCCESS` is expected.

Current Kubernetes observer remains non-mutating and cannot list Secrets.

## Active work — Milestone 4

### Goal

First runtime observability intelligence slice using Prometheus as the authoritative runtime signal source.

Current active PR:

- PR: `#10 Milestone 4 Prometheus runtime intelligence`
- branch: `feature/m4-prometheus-runtime-intelligence`
- branch checkpoint before the next correction: `d54379b0a7711fe12973f2d5d33dee0dd3993a0d`
- status: Draft; do not merge until corrected live acceptance passes

The slice reads Prometheus through the Kubernetes API Service proxy and projects only a narrow runtime evidence set:

- target health `UP | DOWN | UNKNOWN`
- last scrape time and duration
- sanitized target error code
- allowlisted labels
- active Prometheus alert state
- workload attribution through existing Service-to-workload inference

It deliberately excludes raw scrape URLs, discovered labels, arbitrary alert annotations, metric series, credentials, Secret values, and complete sensitive connection data.

### Latest live attempt

User ran the PR #10 gate on `mgmt-automation`.

Repository tests passed:

```text
102 passed in 0.72s
```

The observer service itself completed successfully with `status=0/SUCCESS` and Git source remained `COMPLETE`.

Bootstrap then stopped on this assertion:

```text
RBAC verification failed: expected 'no' for:
kubectl auth can-i get services/proxy -n default
got 'yes'
```

This is currently understood as a test-command bug, not evidence of cross-namespace proxy permission.

Reason:

`kubectl auth can-i VERB TYPE/NAME` treats the slash form as resource/name. Subresources must be tested with `--subresource=...`.

Therefore:

```text
kubectl auth can-i get services/proxy -n default
```

does not safely test the `services/proxy` subresource boundary.

### Required correction before rerun

1. Change bootstrap RBAC checks to use `--subresource=proxy`.
2. Tighten the namespace-scoped `monitoring` Role further with `resourceNames: [kube-prom-stack-prometheus]`, so the observer can proxy only the intended Prometheus Service rather than every Service in `monitoring`.
3. Add/update regression tests for the corrected authorization syntax and resource-name restriction.
4. Keep Secret access denied and all Kubernetes mutating verbs denied.
5. Rerun the full management-host acceptance.
6. Inspect actual Prometheus target and active-alert runtime evidence.
7. Record real live results in `docs/reports/2026-08-15-m4-prometheus-runtime-live-test-gate.md`.
8. Only then mark PR #10 ready and merge.

Do not treat M4 as accepted yet.

## Current trust invariants

These remain binding unless an explicit ADR revises them:

- observation and control credentials stay separate
- initial infrastructure interaction remains read-only
- collector failure is explicit
- stale evidence is not current evidence
- unknown is not absent
- inference is not promoted to fact
- declared and observed state are not conflated
- specialized systems remain authoritative for their domains
- Kubernetes Secret values, credentials, private keys, sensitive Terraform state, and sensitive connection strings never enter evidence or AI context
- `mutation_allowed=false` for current generated operational artifacts
- high-impact changes require fresh verification and explicit approval

## Useful current artifacts

```text
/var/lib/infra-assurance/evidence/kubernetes.json
/var/lib/infra-assurance/evidence/context.json
/var/lib/infra-assurance/evidence/topology.json
/var/lib/infra-assurance/evidence/diff.json
/var/lib/infra-assurance/evidence/drift.json
/var/lib/infra-assurance/evidence/change-context.json
/var/lib/infra-assurance/evidence/observability-coverage.json
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/prometheus-runtime.json   # M4 branch/runtime, not yet accepted
```

## Handoff maintenance rule

Keep this file compact. Update it only when one of these changes materially:

- accepted/merged milestone or vertical slice
- active branch/PR
- live acceptance result
- important unresolved defect or risk
- exact next step
- runtime topology/identity relevant to continuation

Do not append session transcripts or command logs. Summarize verified outcomes and point to detailed ADR/report files instead.

Before ending a long context-heavy session, update this file on the active branch. Before/after merge, ensure `main` receives an accurate checkpoint.
