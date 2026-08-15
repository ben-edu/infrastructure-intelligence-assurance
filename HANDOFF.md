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
- main checkpoint after PR #18: `c26688e4f6cfe9d93fd0c91935a4034342b17fc5`
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

## PR #18 accepted routing ownership baseline

Merged commit:

```text
c26688e4f6cfe9d93fd0c91935a4034342b17fc5
```

Repository gate:

```text
146 passed in 0.92s
```

Accepted RBAC:

```text
EndpointSlices: list=yes, direct get=no
Pods:           get=yes, list/watch=no
ReplicaSets:    get=yes, list/watch=no
Secrets:        no
mutation:       no
```

Accepted source:

```text
overall: COMPLETE
EndpointSlices: 79
Pod exact GETs: 60 requested / 60 present / 0 unknown / 0 skipped
ReplicaSet exact GETs: 37 requested / 37 present / 0 unknown / 0 skipped
mutation_allowed: false
```

Accepted routing summary:

```text
Endpoint paths:                   79
Pod targets:                      75
Non-Pod targets:                   3
TargetRef missing:                 1
Resolved workload paths:          75
Services with EndpointSlices:     78
Services with resolved workloads: 63
RESOLVED_WORKLOAD_ROUTING:         63
NON_POD_ROUTING:                    1
NO_ENDPOINTS_OBSERVED:             13
UNKNOWN:                            1
```

`Service/monitoring/loki-headless` is now evidence-backed as routing to both:

```text
StatefulSet/monitoring/loki
DaemonSet/monitoring/loki-canary
```

The actual kubelet Service is:

```text
Service/kube-system/kube-prom-stack-kubelet
```

and its EndpointSlice targets are cluster-scoped Nodes:

```text
Node/k3s-master-01
Node/k3s-worker-01
Node/k3s-worker-02
```

Therefore its routing state is `NON_POD_ROUTING`, with all Node target namespaces correctly null.

Sensitive/full-object guard passed:

```text
forbidden projected keys: none
raw URL markers: false
```

Detailed report:

```text
docs/reports/2026-08-15-m4-routing-ownership-live-test-gate.md
```

## Newly exposed alert scope identity defect

The accepted incident projection currently contains Service-scoped subjects such as:

```text
Service/keycloak/kube-prom-stack-kubelet
Service/monitoring/kube-prom-stack-kubelet
Service/moodle/kube-prom-stack-kubelet
```

No Kubernetes Service with those identities exists. The real Service is `Service/kube-system/kube-prom-stack-kubelet`.

This demonstrates that Prometheus/Alertmanager label dimensions such as `namespace` and `service` must not automatically be combined into an authoritative Kubernetes Service subject identity. In kubelet/container metrics, those labels can describe different dimensions.

PR #18 remained safe because its routing artifact is not yet consumed by incident candidates.

## Exact next step

Create a small Milestone 4 alert-scope validation/correction slice before integrating routing ownership downstream.

Requirements:

1. preserve raw allowlisted alert labels as signal dimensions;
2. validate any claimed Kubernetes Service subject against current observed Service evidence before classifying the alert scope as `SERVICE`;
3. distinguish `VALIDATED_INFRASTRUCTURE_SUBJECT`, `UNVERIFIED_SIGNAL_DIMENSION`, and unknown/ambiguous scope explicitly;
4. do not rewrite the three kubelet alert subjects to `Service/kube-system/kube-prom-stack-kubelet` merely because that Service exists;
5. when a valid namespace dimension exists but Service identity is invalid, Namespace scope may be retained only as a weaker signal scope, not Service ownership;
6. platform scope remains available when no stronger evidence-backed subject exists;
7. no new infrastructure read/RBAC is required: use the same-cycle Kubernetes snapshot/local artifacts;
8. update alert attention, Event correlation and incident grouping semantics only as needed to preserve cardinality/trust;
9. live validate the corrected scope distribution before allowing routing ownership to enrich incident candidates;
10. do not add Loki/OpenTelemetry in this slice.

After this correction is accepted, create a separate integration slice that prefers complete routing ownership over selector inference where evidence supports the upgrade.

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
