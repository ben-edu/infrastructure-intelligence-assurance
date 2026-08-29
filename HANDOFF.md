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

Runtime report:

```text
docs/reports/2026-08-29-m7-operator-attention-runtime-integration.md
```

Prepared files:

```text
HANDOFF.md
docs/reports/2026-08-29-m7-operator-attention-runtime-integration.md
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

## Live deployment — ACCEPTED

After explicit authorization, the bounded helper was run with `--apply`.

Accepted result:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
```

Accepted interpretation:

```text
- installed runtime integration completed successfully;
- existing collector service completed successfully;
- both target derived artifacts were generated;
- runtime identity remained infra-assurance;
- no root runtime design was introduced;
- broader infrastructure mutation remains unauthorized.
```

## Safe generated-artifact verification — ACCEPTED

The generated JSON was inspected only through an allowlisted safe projection. Raw artifact content was not printed.

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
source=topology code=SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES severity=AMBIGUOUS subject=Service/monitoring/loki-headless
source=drift code=DECLARED_OBSERVED_DRIFT severity=DRIFT subject=Ingress/validation/nginx-validation
```

Truncation:

```text
attention_now_truncated: False
recent_changes_truncated: False
unknowns_truncated: False
required_live_verification_truncated: False
```

Interpretation:

```text
- runtime output matches the previously accepted M7 contract for current loaded evidence;
- zero recent-change/unknown/verification counts are bounded absence only;
- no remediation or mutation is implied by attention items;
- generated artifact preserves mutation_allowed=false.
```

## Exact next gate — FULL REPOSITORY SUITE

Run on `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
python3 -m pytest -q
```

Do not use strict interactive shell mode.

If the full suite passes:

1. record the exact pass count/time in this handoff and the runtime report;
2. verify branch scope is exactly six intended files:
   - `HANDOFF.md`
   - `docs/reports/2026-08-29-m7-operator-attention-runtime-integration.md`
   - `scripts/deploy-operator-attention-runtime.sh`
   - `src/infra_assurance/operator_attention.py`
   - `systemd/infra-assurance-kubernetes.service`
   - `tests/test_operator_attention.py`
3. ensure no temporary/debug/placeholder files exist;
4. create/inspect a non-draft PR;
5. verify mergeability and changed filenames;
6. squash-merge and carry the new accepted main SHA forward.

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
