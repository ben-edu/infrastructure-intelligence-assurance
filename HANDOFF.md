# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

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
infrastructure mutation allowed: false
repository mutation allowed: true
management host: mgmt-automation
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

## Active slice — runtime integration into the existing five-minute collector

Goal:

```text
Generate operator-attention.json and operator-attention.md from the installed package during the existing collector run, under the existing infra-assurance identity.
```

Target artifacts:

```text
/var/lib/infra-assurance/evidence/operator-attention.json
/var/lib/infra-assurance/evidence/operator-attention.md
```

No new timer, service identity, datastore, infrastructure query, or source of truth is introduced.

Prepared files:

```text
src/infra_assurance/operator_attention.py
systemd/infra-assurance-kubernetes.service
tests/test_operator_attention.py
scripts/deploy-operator-attention-runtime.sh
HANDOFF.md
```

The runtime module:

```text
python3 -m infra_assurance.operator_attention
  --inventory <inventory.json>
  --context <context.json>
  --change-context <change-context.json>
  --out <operator-attention.json>
  --summary-out <operator-attention.md>
```

The service integration remains under:

```text
User=infra-assurance
Group=infra-assurance
PYTHONPATH=/opt/infra-assurance/src
NoNewPrivileges=true
ProtectHome=true
ReadWritePaths includes /var/lib/infra-assurance/evidence
```

No root runtime execution is introduced.

## Repository validation — ACCEPTED

Focused tests on the active branch:

```text
7 passed in 0.21s
```

This validates the projection contract, runtime JSON/Markdown writer, safe loader behavior, and systemd wiring under the `infra-assurance` identity.

A repository-wide suite is still required after the live integration is accepted and before PR/merge.

## Narrow deployment helper

Prepared helper:

```text
scripts/deploy-operator-attention-runtime.sh
```

Without `--apply`, it makes no changes and prints the bounded mutation plan.

With `--apply`, it performs only:

```text
1. install src/infra_assurance/operator_attention.py -> /opt/infra-assurance/src/infra_assurance/operator_attention.py
2. install systemd/infra-assurance-kubernetes.service -> /etc/systemd/system/infra-assurance-kubernetes.service
3. python compile-check of the installed module
4. systemctl daemon-reload
5. start the existing infra-assurance-kubernetes.service once
6. verify service Result=success
7. verify operator-attention.json and operator-attention.md exist and are owned by infra-assurance:infra-assurance
```

It explicitly does NOT:

```text
run bootstrap-observer.sh
change Kubernetes RBAC
change kubeconfig
change Git source configuration
add a service or timer
broaden filesystem permissions
run the operator-attention runtime as root
```

The existing collector run remains read-only against infrastructure, but deployment itself mutates the management-host installed code and systemd definition and writes derived evidence artifacts.

## Deployment dry-run — ACCEPTED / NO MUTATION

The user pulled the active branch and ran the helper without `--apply`:

```bash
sudo bash scripts/deploy-operator-attention-runtime.sh
```

Observed result:

```text
This deployment helper performs only these bounded mutations:
- installs src/infra_assurance/operator_attention.py into /opt/infra-assurance/src/infra_assurance/operator_attention.py
- installs systemd/infra-assurance-kubernetes.service into /etc/systemd/system/infra-assurance-kubernetes.service
- runs systemctl daemon-reload
- starts the existing infra-assurance-kubernetes.service once
- verifies operator-attention.json and operator-attention.md were produced

It does not run bootstrap-observer.sh, change Kubernetes RBAC, change kubeconfig, change Git source configuration, add a new service/timer, or broaden filesystem permissions.

Re-run with --apply only after explicit authorization.
```

Accepted interpretation:

```text
- dry-run completed successfully;
- no management-host runtime mutation occurred;
- no Kubernetes mutation occurred;
- no artifact was written by the helper;
- the bounded deployment scope is now operator-reviewed;
- live deployment remains blocked on explicit authorization.
```

## Mutation boundary — WAITING FOR EXPLICIT AUTHORIZATION

Do not run the deployment helper with `--apply` until the user explicitly authorizes this management-host runtime mutation.

Repository preparation, focused tests, and no-op deployment review are complete. The next live gate is blocked only by authorization.

If authorized, execute only:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-operator-attention-runtime-integration
sudo bash scripts/deploy-operator-attention-runtime.sh --apply
```

After deployment, collect only safe verification metadata and operator-attention summary counts; do not print raw source artifacts or sensitive values.

## Acceptance rules for the live integration

Accept only if:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
```

Then verify the generated JSON only through an allowlisted safe summary projection. Preserve source failures as FAILED_TO_OBSERVE, never as zero-attention evidence.

If live integration is accepted:

1. create `docs/reports/2026-08-29-m7-operator-attention-runtime-integration.md`;
2. record exact safe live values and focused result;
3. run the full repository suite;
4. inspect exact branch scope and no temporary files;
5. create/inspect a non-draft PR;
6. verify mergeability and changed filenames;
7. squash-merge and carry the new main SHA forward.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- infrastructure interaction remains read-only unless separately authorized;
- repository changes do not imply deployment authorization;
- runtime integration remains under `infra-assurance`, not root;
- deployment mutation is limited to the installed module, existing systemd unit, daemon reload, one existing collector run, and derived artifact writes;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied by an attention item;
- generated operational artifacts keep `mutation_allowed=false`.

## Continuity rule

At every accepted slice before merge:

1. create/update the accepted report when reusable evidence changed;
2. update `HANDOFF.md` with accepted SHA context, evidence, preserved unknowns, trust boundary, merge gate, and exact next step;
3. update roadmap/current-state/README only when milestone status, architecture, or user-facing project status materially changes;
4. ensure no temporary/debug/placeholder files remain;
5. run focused tests and a full repository suite when reusable implementation/contracts change materially;
6. inspect PR scope and mergeability and squash-merge when clean;
7. carry the new accepted `main` SHA into the next checkpoint.
