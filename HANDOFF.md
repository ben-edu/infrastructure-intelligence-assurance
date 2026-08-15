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
- current main checkpoint: `68af6664c6754d0fe6cd832e824c10f92070c2a9`
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
- PR #18 — bounded EndpointSlice/Pod/ReplicaSet routing ownership.

Known real drift remains intentionally unresolved:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## PR #18 accepted routing baseline

Merged at:

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

Accepted least-privilege RBAC:

```text
EndpointSlices: list=yes, direct get=no
Pods: get=yes, list/watch=no
ReplicaSets: get=yes, list/watch=no
Secrets/mutation: no
```

`Service/monitoring/loki-headless` is evidence-backed as routing to both `StatefulSet/monitoring/loki` and `DaemonSet/monitoring/loki-canary`.

The real kubelet Service is `Service/kube-system/kube-prom-stack-kubelet`, with three cluster-scoped Node targets and `NON_POD_ROUTING` state.

## Active work — PR #20 alert scope identity validation

- PR: `#20 Milestone 4 validate alert resource scope`
- branch: `feature/m4-alert-scope-validation`
- package version: `0.14.0`
- status: Draft; corrected repository gate accepted; live bootstrap/systemd acceptance pending

### Why this slice exists

PR #18 exposed synthetic Service subjects in alert attention:

```text
Service/keycloak/kube-prom-stack-kubelet
Service/monitoring/kube-prom-stack-kubelet
Service/moodle/kube-prom-stack-kubelet
```

Those Kubernetes Services do not exist. Alert `namespace` and `service` labels are signal dimensions and must not automatically become authoritative Service identity.

### Design

No new infrastructure query or RBAC is added.

A derived post-step reads same-cycle local artifacts:

```text
alert-attention.json
kubernetes.json
kubernetes-event-runtime.json
```

Runtime order:

```text
kubernetes_runtime
routing_ownership
alert_scope_runtime
incident_runtime
```

Final `alert-attention.json` becomes version `0.2`; Event correlation is rebuilt from corrected scopes before incident grouping.

Each attention record gains:

```text
scope_validation.status
scope_validation.claimed_subject
scope_validation.validated_subject
scope_validation.basis
scope_validation.evidence_ids
```

Validation statuses:

```text
VALIDATED_INFRASTRUCTURE_SUBJECT
UNVERIFIED_SIGNAL_DIMENSION
INFERRED_RELATION
PLATFORM_FALLBACK
```

Rules:

- exact observed Service/Node/Namespace identities may retain that resource scope;
- unobserved Service identity is never rewritten to a similarly named Service elsewhere;
- if its namespace is observed, Service scope falls back to Namespace with `UNVERIFIED_SIGNAL_DIMENSION`;
- otherwise fallback is Platform;
- existing workload association remains `INFERRED_RELATION` in this slice;
- failed/incomplete Kubernetes collection remains partial/failed observation, not absence;
- original allowlisted alert labels remain preserved;
- warning provenance uses the existing attention `evidence_ids` list, not a singular synthetic `evidence_id` field.

No routing ownership is integrated into incident impact context yet.

### Management-host gate history

First attempt static guards passed:

```text
RBAC changes: none
query-capable client markers: none
```

Pytest then stopped before bootstrap:

```text
3 failed, 153 passed in 1.56s
```

All three failures were `KeyError: 'evidence_id'` in fallback scope warning construction.

Root cause: implementation defect. Alert-attention records expose `evidence_ids`, while the validator incorrectly referenced a singular field in fallback warning paths.

Correction:

- preserve the existing alert `evidence_ids` list in fallback warning provenance;
- no synthetic singular evidence field;
- regression assertion verifies alert evidence survives Service-to-Namespace fallback.

Corrected repository gate on `mgmt-automation`:

```text
156 passed in 0.89s
```

Tested branch checkpoint before the bookkeeping commit:

```text
2d7e655 Record first PR 20 gate failure
```

Therefore repository-level correctness is established. Bootstrap/live scope-validation acceptance has not yet been run.

Relevant docs:

```text
docs/decisions/0015-validate-alert-resource-scope.md
docs/milestone-4-alert-scope-validation.md
docs/reports/2026-08-15-m4-alert-scope-validation-live-test-gate.md
```

## Exact next step

Do not rerun pytest unnecessarily. Fast-forward the active branch on `mgmt-automation`, then run the remaining bootstrap/live acceptance checks only.

Live acceptance must confirm:

1. no RBAC change and no query-capable client in scope validator;
2. observer plus routing/scope/incident post-steps succeed;
3. final alert-attention version is `0.2`;
4. `source_status.kubernetes_scope` is explicit;
5. attention cardinality is preserved;
6. every attention record contains `scope_validation`;
7. the three kubelet pseudo-Service subjects no longer remain Service-scoped unless exact Services unexpectedly exist now;
8. they are not rewritten to `Service/kube-system/kube-prom-stack-kubelet`;
9. original `service=kube-prom-stack-kubelet` labels remain preserved;
10. Event correlation and incident grouping use corrected scopes;
11. sensitive/free-form guards and `mutation_allowed=false` remain clean.

If accepted, merge PR #20. Only after that create a separate slice to integrate complete routing ownership into topology/inventory/incident context where evidence supports the upgrade.

Do not add Loki/OpenTelemetry in PR #20.

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
