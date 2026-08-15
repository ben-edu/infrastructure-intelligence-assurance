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
- current main checkpoint before PR #20 merge: `68af6664c6754d0fe6cd832e824c10f92070c2a9`
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
- PR #20 — alert resource scope identity validation; accepted and ready to merge.

Known real drift remains intentionally unresolved:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## PR #18 accepted routing baseline

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

Least-privilege RBAC remains:

```text
EndpointSlices: list=yes, direct get=no
Pods: get=yes, list/watch=no
ReplicaSets: get=yes, list/watch=no
Secrets/mutation: no
```

`Service/monitoring/loki-headless` is evidence-backed as routing to both `StatefulSet/monitoring/loki` and `DaemonSet/monitoring/loki-canary`.

The real kubelet Service is `Service/kube-system/kube-prom-stack-kubelet`, with three cluster-scoped Node targets and `NON_POD_ROUTING` state.

## PR #20 accepted alert scope validation

- PR: `#20 Milestone 4 validate alert resource scope`
- branch: `feature/m4-alert-scope-validation`
- package version: `0.14.0`
- status: live accepted; ready for squash merge
- no RBAC change
- no new infrastructure/telemetry query

Why it exists: PR #18 exposed synthetic Service subjects built from alert label dimensions:

```text
Service/keycloak/kube-prom-stack-kubelet
Service/monitoring/kube-prom-stack-kubelet
Service/moodle/kube-prom-stack-kubelet
```

Those Services do not exist. Alert `namespace` and `service` labels are signal dimensions, not authoritative compound Service identity.

Accepted rule:

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

Runtime/systemd acceptance:

```text
kubernetes_runtime   status=0/SUCCESS
routing_ownership   status=0/SUCCESS
alert_scope_runtime status=0/SUCCESS
incident_runtime    status=0/SUCCESS
```

Final stdlib-only artifact acceptance:

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

Corrected incident grouping:

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

1. Squash merge PR #20.
2. Update `main` Handoff after merge with the actual merge commit.
3. Create a separate Milestone 4 routing-ownership integration slice.
4. That slice must consume the existing `kubernetes-routing-ownership.json` artifact only; no new infrastructure query or RBAC is required.
5. Prefer `RESOLVED_WORKLOAD_ROUTING` over `SERVICE_SELECTOR_MATCH_INFERENCE` only where routing evidence is complete and unambiguous.
6. Preserve multiple routing workload targets when real routing has multiple controllers; do not select one heuristically.
7. Keep `NON_POD_ROUTING`, `NO_ENDPOINTS_OBSERVED`, `UNKNOWN`, and partial/failed source states explicit.
8. Do not turn Namespace fallback alerts into Service/workload ownership merely because a routing record with a similar signal label exists.
9. Update operational inventory/incident impact context only where the accepted identity and routing subjects actually join.
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
