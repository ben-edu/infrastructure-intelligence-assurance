# Milestone 7 — Operator Attention Runtime Integration

Date: 2026-08-29
Status: ACCEPTED
Mode: installed read-only derived-artifact integration in the existing five-minute collector

## Scope

This slice integrates the accepted operator-attention contract into the existing `infra-assurance-kubernetes.service` execution path.

Generated artifacts:

```text
/var/lib/infra-assurance/evidence/operator-attention.json
/var/lib/infra-assurance/evidence/operator-attention.md
```

Runtime remains under:

```text
User=infra-assurance
Group=infra-assurance
PYTHONPATH=/opt/infra-assurance/src
NoNewPrivileges=true
ProtectHome=true
```

No new service, timer, identity, datastore, infrastructure query, or source of truth is introduced.

## Repository validation

Focused tests:

```text
7 passed in 0.21s
```

Full repository regression suite:

```text
412 passed in 2.00s
```

## Deployment validation

The reviewed bounded deployment helper was first run without `--apply` and made no changes.

After explicit authorization, the user executed the bounded deployment with `--apply`.

Accepted result:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
```

The deployment scope was limited to installing the operator-attention module, installing the existing collector unit definition, `systemctl daemon-reload`, one run of the existing collector service, and verification of the two derived artifacts.

The deployment did not run the broad bootstrap path, change Kubernetes RBAC, change kubeconfig, change Git source configuration, add a service/timer, broaden filesystem permissions, or introduce root runtime execution.

## Safe artifact verification

The generated `operator-attention.json` was verified through an allowlisted projection only. The raw artifact was not printed.

Accepted metadata:

```text
operator_attention_version: 0.1
cluster_id: k3s-main
mutation_allowed: False
scope: KUBERNETES_EXISTING_EVIDENCE_ONLY
source_artifacts: inventory.json,context.json,change-context.json
```

Accepted summary:

```text
workloads_total: 68
workloads_with_attention: 3
attention_now_total: 2
recent_changes_total: 0
unknowns_total: 0
required_live_verification_total: 0
```

Accepted attention items:

```text
1. source=topology code=SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES severity=AMBIGUOUS subject=Service/monitoring/loki-headless
2. source=drift code=DECLARED_OBSERVED_DRIFT severity=DRIFT subject=Ingress/validation/nginx-validation
```

Truncation:

```text
attention_now_truncated: False
recent_changes_truncated: False
unknowns_truncated: False
required_live_verification_truncated: False
```

## Accepted interpretation

The operator-attention contract now runs from the installed package inside the existing collector cycle under `infra-assurance` and produces both JSON and Markdown derived artifacts.

The runtime output matches the previously accepted contract-level live projection for the currently loaded Kubernetes evidence artifacts.

`recent_changes_total=0`, `unknowns_total=0`, and `required_live_verification_total=0` are bounded absence statements only within the loaded source artifacts and their own freshness/trust boundaries. They are not universal absence claims.

The two attention items are evidence-routing signals only. No remediation or mutation is authorized or implied.

## Trust boundary

- infrastructure observation remains read-only;
- the only mutation in this slice was the explicitly authorized management-host deployment and derived artifact writes;
- runtime remains `infra-assurance`, not root;
- operator-attention artifacts do not replace their source evidence;
- no raw Kubernetes Secret value, credential, raw Terraform state, sensitive connection string, or unallowlisted raw source content was projected;
- `mutation_allowed=false` is preserved in the generated artifact.

## Acceptance

This slice is accepted for merge. Repository, live runtime, generated-artifact, and full-suite gates all passed.

Next step after merge: reassess the smallest remaining Milestone 7 gap before adding any dashboard or broad cross-domain layer. Prefer one small operator-facing integration over new infrastructure.
