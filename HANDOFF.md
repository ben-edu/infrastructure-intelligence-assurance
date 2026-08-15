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
- stable main before active PR: `e24b86e7431cecaea01a6984b57f6b2185390f73`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- cluster: `k3s-main`
- runtime user: `infra-assurance`
- oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

Milestones 0–3 are live validated for the evidence contract, Kubernetes observation/context/topology/preflight, history/diff, Git declared-state/drift, workload inventory, and Prometheus Operator coverage.

Milestone 4 accepted slices before the active PR:

- PR #10 — Prometheus runtime;
- PR #13 — Alertmanager handling correlation;
- PR #14 — Kubernetes Event correlation;
- PR #16 — incident candidates/drill-down.

Known real drift remains intentionally unresolved:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Active work — PR #18 accepted, pending merge

- PR: `#18 Milestone 4 bounded EndpointSlice and Pod routing ownership`
- branch: `feature/m4-endpointslice-pod-ownership`
- package version: `0.13.0`
- status: live accepted; ready to merge

### Repository gate

First management-host test attempt exposed a regression-test parsing defect and stopped before bootstrap:

```text
1 failed, 145 passed in 0.98s
```

The RBAC implementation was not the cause. After correcting the test parser, the complete repository suite passed:

```text
146 passed in 0.92s
```

### Accepted least-privilege RBAC

```text
List EndpointSlices : yes
Get EndpointSlices  : no
Get Pods            : yes
List Pods           : no
Watch Pods          : no
Get ReplicaSets     : yes
List ReplicaSets    : no
Watch ReplicaSets   : no
List Secrets        : no
Create Deployment   : no
```

Pod exact GETs follow only Pod targetRefs observed in EndpointSlices. ReplicaSet exact GETs follow only controller ownerReferences observed from those Pods.

Default bounds:

```text
max Pod GETs:        500
max ReplicaSet GETs: 250
```

### Accepted live source

```text
overall: COMPLETE
EndpointSlices: 79 / COMPLETE
Pod exact GETs: 60 requested / 60 present / 0 unknown / 0 skipped
ReplicaSet exact GETs: 37 requested / 37 present / 0 unknown / 0 skipped
mutation_allowed: false
```

Routing summary:

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

The only unknown path is `Service/default/kubernetes` with a missing targetRef. It remains `UNKNOWN`.

### Stronger evidence for Loki

`Service/monitoring/loki-headless` is live resolved through EndpointSlices/Pod ownerReferences to both:

```text
StatefulSet/monitoring/loki
DaemonSet/monitoring/loki-canary
```

This replaces the earlier selector ambiguity with current routing evidence. It is not a business-ownership statement.

### Kubelet routing

The actual observed Service is:

```text
Service/kube-system/kube-prom-stack-kubelet
```

It routes to three Node targetRefs:

```text
Node/k3s-master-01
Node/k3s-worker-01
Node/k3s-worker-02
```

State:

```text
NON_POD_ROUTING
```

All Node targets have `namespace=null`.

### Newly exposed downstream scope defect

Current incident candidates still contain:

```text
Service/keycloak/kube-prom-stack-kubelet
Service/monitoring/kube-prom-stack-kubelet
Service/moodle/kube-prom-stack-kubelet
```

No corresponding Kubernetes Services exist in those namespaces. The real kubelet Service is in `kube-system`.

This proves that existing alert attention logic can incorrectly combine Prometheus/Alertmanager metric labels `namespace + service` and treat them as an authoritative Kubernetes Service identity. For kubelet/container alerts, those labels can represent different metric dimensions.

PR #18 is still safe because routing ownership is not yet consumed by incident candidates:

```text
incident consumes routing artifact: false
```

### Sensitive/full-object guard

```text
forbidden projected keys: none
raw URL markers: false
```

Persisted routing evidence excludes endpoint addresses/IPs, Pod IP/spec/status, labels, annotations, env/container data, logs, volumes, UIDs, Secret references, service-account tokens, credentials, and other full-object content.

Detailed report:

```text
docs/reports/2026-08-15-m4-routing-ownership-live-test-gate.md
```

## Exact next step

1. Mark PR #18 ready and squash merge it.
2. Create a separate Milestone 4 slice for alert attention scope validation/correction before routing ownership is integrated downstream.
3. Validate claimed Kubernetes Service identities against current observed Service inventory/topology instead of assuming `alert.labels.namespace + alert.labels.service` is a Service key.
4. Preserve original alert labels as signal dimensions, but distinguish them from validated infrastructure subject identity.
5. For invalid/unverified Service identity, degrade to a supported scope such as Namespace/Platform/Node only when evidence supports that scope; otherwise keep scope unknown and require verification.
6. Do not use routing ownership to force-match the three current kubelet candidates to `Service/kube-system/kube-prom-stack-kubelet`; their alert `namespace` labels are evidence about metric dimensions, not proof that the Kubernetes Service subject should be rewritten.
7. After scope correction is live validated, create a separate integration slice that prefers accepted routing ownership over selector inference where current evidence is complete.

Do not add Loki/OpenTelemetry in the scope-correction slice.

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
