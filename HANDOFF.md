# Project Handoff

This is the compact continuation checkpoint for the Infrastructure Intelligence & Assurance Platform. Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read the Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable checkpoint

- repository: `ben-edu/infrastructure-intelligence-assurance`
- stable branch: `main`
- current main checkpoint: `62c75f863c053be5e353c15f62523c27a52be9d3`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- cluster: `k3s-main`
- runtime user: `infra-assurance`
- oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

Milestones 0–3 are live validated for the evidence contract, Kubernetes observation/context/topology/preflight, history/diff, Git declared-state/drift, workload inventory, and Prometheus Operator coverage.

Milestone 4 accepted/live-validated slices:

- PR #10 — Prometheus runtime;
- PR #13 — Alertmanager handling correlation;
- PR #14 — Kubernetes Event correlation;
- PR #16 — incident candidates/drill-down;
- PR #18 — bounded EndpointSlice/Pod/ReplicaSet routing ownership;
- PR #20 — alert resource scope identity validation.

Known real drift remains intentionally unresolved:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## PR #18 routing ownership baseline

Merged commit:

```text
c26688e4f6cfe9d93fd0c91935a4034342b17fc5
```

Accepted live evidence:

```text
pytest: 146 passed in 0.92s
routing source: COMPLETE
EndpointSlices: 79
Pod exact GETs: 60 / 60 present
ReplicaSet exact GETs: 37 / 37 present
resolved workload paths: 75
services with resolved workloads: 63
mutation_allowed: false
```

Least-privilege RBAC:

```text
EndpointSlices: list=yes, direct get=no
Pods: get=yes, list/watch=no
ReplicaSets: get=yes, list/watch=no
Secrets/mutation: no
```

`Service/monitoring/loki-headless` is evidence-backed as routing to both `StatefulSet/monitoring/loki` and `DaemonSet/monitoring/loki-canary`.

The real kubelet Service is `Service/kube-system/kube-prom-stack-kubelet`, with three cluster-scoped Node targets and `NON_POD_ROUTING` state.

## PR #20 accepted alert scope validation

Merged commit:

```text
62c75f863c053be5e353c15f62523c27a52be9d3
```

Package version: `0.14.0`.

No RBAC or new infrastructure/telemetry query was added.

Accepted semantics:

- alert labels remain signal dimensions;
- exact observed Service/Node/Namespace identities may remain infrastructure-scoped;
- unobserved Service identity is never rewritten to a similarly named Service elsewhere;
- with an observed namespace, invalid Service scope falls back to Namespace with `UNVERIFIED_SIGNAL_DIMENSION`;
- otherwise fallback is Platform;
- existing workload association remains `INFERRED_RELATION` until routing ownership is integrated separately;
- failed/incomplete Kubernetes observation remains partial/failed, not absence;
- original allowlisted alert labels remain preserved.

Repository gate history:

```text
first attempt: 3 failed, 153 passed in 1.56s
root cause: incorrect singular alert["evidence_id"] reference in fallback warnings
corrected gate: 156 passed in 0.89s
```

Accepted live execution:

```text
kubernetes_runtime   status=0/SUCCESS
routing_ownership   status=0/SUCCESS
alert_scope_runtime status=0/SUCCESS
incident_runtime    status=0/SUCCESS
```

Final artifact acceptance:

```text
PR #20 LIVE ACCEPTANCE: PASS
alert_attention_version: 0.2
Prometheus: COMPLETE
Alertmanager: COMPLETE
Kubernetes scope: COMPLETE
Alertmanager alerts: 11
Alert attention: 11
Event correlations: 11
NAMESPACE scopes: 9
PLATFORM scopes: 2
SERVICE scopes: 0
VALIDATED_INFRASTRUCTURE_SUBJECT: 3
UNVERIFIED_SIGNAL_DIMENSION: 6
PLATFORM_FALLBACK: 2
pseudo attention scopes: none
pseudo incident scopes: none
automatic kube-system rewrite: none
label mismatches: none
current kubelet-labelled alerts: 6
forbidden projected keys: none
raw URL markers: false
mutation_allowed: false
```

Current incident grouping after correction:

```text
Namespace/keycloak    alerts=2
Namespace/monitoring  alerts=5
Namespace/moodle      alerts=2
Platform/k3s-main     alerts=2
```

Relevant docs:

```text
docs/decisions/0015-validate-alert-resource-scope.md
docs/milestone-4-alert-scope-validation.md
docs/reports/2026-08-15-m4-alert-scope-validation-live-test-gate.md
```

## Exact next step

Create a separate Milestone 4 routing-ownership integration slice.

Requirements:

1. Consume the already accepted local artifact `kubernetes-routing-ownership.json`; no new infrastructure query or RBAC.
2. Prefer `RESOLVED_WORKLOAD_ROUTING` over `SERVICE_SELECTOR_MATCH_INFERENCE` only where routing source evidence is complete and the exact Service subject joins.
3. Preserve multiple real routing workload targets; never choose one heuristically.
4. Keep `NON_POD_ROUTING`, `NO_ENDPOINTS_OBSERVED`, `UNKNOWN`, and partial/failed routing states explicit.
5. Do not turn Namespace fallback alerts into Service/workload ownership merely because signal labels resemble a Service elsewhere.
6. Enrich operational inventory and incident impact context only where exact accepted subjects join.
7. Keep selector inference available as weaker evidence when no accepted routing relation exists; label the difference explicitly.
8. Live validate changes in workload-impact context and the `loki-headless` multi-controller case.
9. No root-cause or business-impact claim.
10. Do not add Loki/OpenTelemetry in this integration slice.

## Trust invariants

- observation credentials remain separate from future control credentials;
- infrastructure interaction remains read-only;
- collector failure is explicit;
- stale is not current;
- unknown is not absent;
- inference is not fact;
- declared and observed state remain separate;
- specialized systems remain authoritative;
- no passwords, tokens, private keys, raw Kubernetes Secret values, sensitive Terraform state, or complete sensitive connection strings enter evidence/AI context;
- current generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
