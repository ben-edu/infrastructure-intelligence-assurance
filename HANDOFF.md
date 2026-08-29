# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #79: d089fdd241fcf27437f96b36a6f112b38be49608
active branch: agent/m7-operator-attention-runtime-integration
Milestone 7: ACTIVE
management host: mgmt-automation
repository mutation allowed: true
bounded management-host deployment authorized: true
broader infrastructure mutation authorized: false
```

## Accepted M7 baseline

Report:

```text
docs/reports/2026-08-29-m7-operator-attention-summary-contract.md
```

Accepted baseline:

```text
focused tests: 5 passed in 0.05s
full suite: 410 passed in 1.83s
cluster: k3s-main
scope: KUBERNETES_EXISTING_EVIDENCE_ONLY
workloads_total: 68
workloads_with_attention: 3
attention_now_total: 2
recent_changes_total: 0
unknowns_total: 0
required_live_verification_total: 0
```

Accepted attention items:

```text
Service/monitoring/loki-headless
  code=SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES
  severity=AMBIGUOUS

Ingress/validation/nginx-validation
  code=DECLARED_OBSERVED_DRIFT
  severity=DRIFT
```

Rejected/incomplete attempts preserved:

```text
interactive-user probe: FAILED_TO_OBSERVE / PermissionError
service-identity probe from /home/ben source tree: FAILED_TO_OBSERVE before code execution
```

Do not reuse either failed attempt as negative evidence.

## Active slice — operator-attention runtime integration

Goal:

```text
Generate operator-attention.json and operator-attention.md during the existing five-minute collector run, from the installed package under the existing infra-assurance identity.
```

Target artifacts:

```text
/var/lib/infra-assurance/evidence/operator-attention.json
/var/lib/infra-assurance/evidence/operator-attention.md
```

Prepared files:

```text
HANDOFF.md
scripts/deploy-operator-attention-runtime.sh
src/infra_assurance/operator_attention.py
systemd/infra-assurance-kubernetes.service
tests/test_operator_attention.py
```

Runtime boundary remains:

```text
User=infra-assurance
Group=infra-assurance
PYTHONPATH=/opt/infra-assurance/src
NoNewPrivileges=true
ProtectHome=true
ReadWritePaths includes /var/lib/infra-assurance/evidence
```

No new service, timer, identity, datastore, infrastructure query, or source of truth is introduced.

## Repository validation — ACCEPTED

```text
focused tests: 7 passed in 0.21s
```

## Deployment dry-run — ACCEPTED / NO MUTATION

The helper was run without `--apply` and printed only the bounded plan. No mutation occurred.

## Authorization — RECEIVED

Authorization applies only to the reviewed management-host deployment helper scope. It does not authorize broader infrastructure mutation, Kubernetes mutation, permission broadening, remediation, or unrelated runtime changes.

## Live deployment — ACCEPTED

The user executed:

```bash
sudo bash scripts/deploy-operator-attention-runtime.sh --apply
```

Observed result:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
```

Accepted interpretation:

```text
- installed operator-attention runtime integration completed;
- the existing collector service completed successfully;
- both target derived artifacts were produced;
- runtime identity remained infra-assurance;
- no root runtime design was introduced;
- broader infrastructure mutation remains unauthorized.
```

The deployment result does not by itself validate the generated operator-attention summary contents. A safe allowlisted read of only top-level summary metadata is still required before the runtime integration report can be finalized.

## Exact next gate — SAFE ARTIFACT VERIFICATION

On `mgmt-automation`, read only allowlisted metadata from the generated JSON. Do not print the raw artifact.

After that succeeds:

1. create `docs/reports/2026-08-29-m7-operator-attention-runtime-integration.md`;
2. record exact safe runtime summary values and focused result;
3. run the full repository suite;
4. inspect exact branch scope/no temporary files;
5. create/inspect a non-draft PR;
6. verify mergeability and filenames;
7. squash-merge and carry the new main SHA forward.

## Remaining project direction

Roadmap remaining milestones are M7 and M8. Roughly 20–30% of the core roadmap remains. Explicitly deferred M5/M6 unknowns remain preserved rather than forced closed with weak evidence.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- infrastructure remains read-only except for the explicitly authorized management-host deployment already performed;
- runtime integration stays under `infra-assurance`, not root;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied by an attention item;
- generated operational artifacts keep `mutation_allowed=false`.
