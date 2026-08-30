# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #83: 7411cfe3f84c29750761f42dd74ee6f870773076
active branch: agent/m7-cross-domain-runtime-integration
Milestone 7: ACTIVE
management host: mgmt-automation
broader infrastructure mutation authorized: false
cross-domain runtime deployment authorized: false
```

## Accepted M7 cross-domain contract

Accepted report:

```text
docs/reports/2026-08-30-m7-cross-domain-runtime-contract.md
```

Accepted validation:

```text
focused tests: 8 passed in 0.46s
live no-deploy contract check: source_status=COMPLETE / discovery_rc=0
full suite: 426 passed in 2.48s
cluster_id: k3s-main
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
attention_now_total: 5
required_live_verification_total: 8
backup_assets_total: 37
backup_protection_unknown: 37
backup_restore_verification_unknown: 37
backup_unprotected_claims: 0
```

Trust semantics that must remain true:

```text
UNKNOWN protection != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
unprotected claims require authoritative backup evidence
```

## Installed runtime before this slice

The existing five-minute collector is still installed with Kubernetes-only operator attention:

```text
runtime identity: infra-assurance
installed operator scope: KUBERNETES_EXISTING_EVIDENCE_ONLY
```

The existing unit generated `backup-assurance.json` after the Kubernetes-only operator-attention `ExecStartPost`, so cross-domain runtime wiring requires a bounded ordering change.

## Active slice — cross-domain installed-runtime integration

Goal:

```text
Run the accepted cross-domain operator command in the existing five-minute collector path under infra-assurance, using backup-assurance.json generated earlier in the same oneshot service execution.
```

Prepared repository changes:

```text
HANDOFF.md
scripts/deploy-operator-attention-runtime.sh
systemd/infra-assurance-kubernetes.service
tests/test_operator_attention_cross_domain_runtime_integration.py
```

Runtime wiring prepared:

```text
1. existing kubernetes_runtime ExecStart completes;
2. backup_assurance_foundation runs as ExecStartPost and produces backup-assurance.json/md;
3. operator_attention_backup runs next and consumes inventory/context/change-context/backup-assurance;
4. remaining existing ExecStartPost commands continue unchanged.
```

Runtime identity/sandbox remains:

```text
User=infra-assurance
Group=infra-assurance
PYTHONPATH=/opt/infra-assurance/src
NoNewPrivileges=true
ProtectHome=true
existing ReadWritePaths only
```

No new service, timer, identity, datastore, Kubernetes RBAC, kubeconfig, Git source config, or filesystem permission is introduced.

## Bounded deployment helper

`scripts/deploy-operator-attention-runtime.sh` remains dry-run unless `--apply` is supplied.

If later explicitly authorized, it will only:

```text
- install operator_attention.py;
- install backup_operator_adapter.py;
- install operator_attention_backup.py;
- install the existing infra-assurance-kubernetes.service unit definition;
- python-compile those installed modules;
- run systemctl daemon-reload;
- start the existing oneshot service once;
- verify operator-attention JSON/Markdown ownership;
- verify runtime scope equals KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY.
```

It does not run `bootstrap-observer.sh` and does not broaden infrastructure access.

## Mutation boundary

Repository preparation and tests are allowed. Actual deployment is NOT yet authorized.

Do not run:

```text
scripts/deploy-operator-attention-runtime.sh --apply
```

until explicit authorization is obtained.

## Exact next gate — repository focused tests

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m7-cross-domain-runtime-integration

python3 -m pytest -q \
  tests/test_operator_attention.py \
  tests/test_operator_attention_cross_domain_runtime_integration.py
```

Do not use strict interactive shell mode.

If focused tests pass, run the deployment helper without `--apply` only. That dry-run must print the bounded mutation plan and perform no mutation. Actual `--apply` remains a separate explicit authorization gate.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- infrastructure observation remains read-only except separately authorized bounded management-host deployment;
- runtime identity stays `infra-assurance`, not root;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- UNKNOWN protection is never treated as UNPROTECTED;
- restore verification UNKNOWN is never treated as overdue restore testing;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied by an attention item;
- generated operational semantics keep `mutation_allowed=false`.
