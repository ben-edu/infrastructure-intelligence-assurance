# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then the reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #79: d089fdd241fcf27437f96b36a6f112b38be49608
active branch: agent/m7-operator-attention-runtime-integration
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6 overall: NOT COMPLETE
Milestone 6 current read-only governance phase: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES AND SAFE OBSERVATION PATHS
Milestone 7: ACTIVE
management host: mgmt-automation
repository mutation allowed: true
bounded management-host deployment authorized: true
broader infrastructure mutation authorized: false
```

## Accepted M7 baseline

Accepted report:

```text
docs/reports/2026-08-29-m7-operator-attention-summary-contract.md
```

Accepted baseline validation:

```text
focused tests: 5 passed in 0.05s
full suite: 410 passed in 1.83s
live source status: COMPLETE
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

Do not reuse either failed attempt as zero-attention or source-absence evidence.

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

Runtime remains:

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
focused tests on active branch: 7 passed in 0.21s
```

The repository-wide suite is required after accepted live deployment and before PR/merge.

## Deployment dry-run — ACCEPTED / NO MUTATION

The user ran:

```bash
sudo bash scripts/deploy-operator-attention-runtime.sh
```

The helper printed the bounded plan and exited without mutation.

Accepted dry-run scope:

```text
- install operator_attention.py into /opt/infra-assurance/src/infra_assurance/
- install the existing collector unit definition into /etc/systemd/system/
- compile-check installed module
- systemctl daemon-reload
- start the existing infra-assurance-kubernetes.service once
- verify Result=success
- verify operator-attention.json and operator-attention.md exist and are owned by infra-assurance:infra-assurance
```

Explicitly excluded:

```text
bootstrap-observer.sh
Kubernetes RBAC changes
kubeconfig changes
Git source configuration changes
new service/timer
filesystem permission broadening
root runtime execution of operator attention
```

## Authorization — RECEIVED

The user explicitly said to proceed to the next step after reviewing the remaining project work. Treat that as authorization for this exact bounded management-host deployment only.

Authorization does NOT extend to broader infrastructure mutation, Kubernetes mutation, permission broadening, remediation, or unrelated runtime changes.

## Exact next live gate

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-operator-attention-runtime-integration
sudo bash scripts/deploy-operator-attention-runtime.sh --apply
```

Do not use strict interactive shell mode.

Accept only if the helper reports:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
```

After deployment, inspect only safe allowlisted summary metadata. Do not print raw evidence or sensitive values.

If accepted:

1. create `docs/reports/2026-08-29-m7-operator-attention-runtime-integration.md`;
2. record exact safe live values and focused result;
3. run full repository suite;
4. inspect exact branch scope/no temporary files;
5. create/inspect non-draft PR;
6. verify mergeability and filenames;
7. squash-merge and carry new main SHA forward.

## Remaining project direction

Roadmap remaining milestones are M7 and M8. M7 is the unified operator experience; M8 is reliability/hardening. Current rough remaining effort is about 20–30% of the core roadmap, while explicitly deferred M5/M6 unknowns remain preserved rather than forced closed with weak evidence.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- infrastructure remains read-only except for this explicitly authorized management-host deployment;
- runtime integration stays under `infra-assurance`, not root;
- deployment mutation is limited to installed module, existing systemd unit, daemon reload, one existing collector run, and derived artifact writes;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied by an attention item;
- generated operational artifacts keep `mutation_allowed=false`.
