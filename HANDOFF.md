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
cross-domain runtime deployment previously authorized/performed: true
corrective redeployment authorized: false
```

## Accepted cross-domain contract baseline

Accepted reports:

```text
docs/reports/2026-08-30-m7-backup-assurance-operator-integration.md
docs/reports/2026-08-30-m7-cross-domain-runtime-contract.md
```

Accepted contract validation:

```text
focused runtime-contract tests: 8 passed in 0.46s
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

## Active slice — cross-domain installed-runtime integration

Active report:

```text
docs/reports/2026-08-30-m7-cross-domain-runtime-integration.md
```

Goal:

```text
Run the accepted cross-domain operator command in the existing five-minute collector path under infra-assurance while preserving established collector ordering invariants.
```

Branch scope:

```text
HANDOFF.md
docs/reports/2026-08-30-m7-cross-domain-runtime-integration.md
scripts/deploy-operator-attention-runtime.sh
systemd/infra-assurance-kubernetes.service
tests/test_operator_attention_cross_domain_runtime_integration.py
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

No new service, timer, identity, datastore, Kubernetes RBAC, kubeconfig, Git source config, or filesystem permission was introduced.

## Initial repository/deployment validation

Initial focused tests:

```text
10 passed in 0.21s
```

The bounded dry-run was accepted and the user explicitly authorized the first deployment. The first deployment completed successfully:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
runtime_scope=KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
```

Safe generated-artifact verification also succeeded:

```text
operator_attention_version: 0.1
cluster_id: k3s-main
mutation_allowed: False
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
source_artifacts: inventory.json,context.json,change-context.json,backup-assurance.json
workloads_total: 68
workloads_with_attention: 3
attention_now_total: 5
recent_changes_total: 0
unknowns_total: 0
required_live_verification_total: 8
backup_assets_total: 37
backup_protection_unknown: 37
backup_restore_verification_unknown: 37
backup_unprotected_claims: 0
unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
authoritative_backup_evidence_required_for_unprotected: True
attention_now_truncated: False
required_live_verification_truncated: False
```

## Preserved full-suite failure

The first full suite after deployment returned:

```text
1 failed, 428 passed in 2.49s
```

Failure:

```text
tests/test_backup_assurance_foundation_wiring.py::test_backup_assurance_runs_after_observability_post_steps
```

This was a real repository/runtime ordering regression, not an evidence observation failure. The established invariant is preserved; its test was not weakened or removed.

## Corrective ordering — REPOSITORY VALIDATED

Corrected intended order:

```text
1. kubernetes_runtime completes;
2. existing routing / incident / observability ExecStartPost chain remains in its prior order;
3. prometheus_rule_context_integration completes;
4. backup_assurance_foundation produces backup-assurance.json/md;
5. operator_attention_backup runs immediately after backup assurance.
```

Preserved invariants:

```text
prometheus_rule_context_integration < backup_assurance_foundation
backup_assurance_foundation < operator_attention_backup
```

Corrective focused gate executed on `mgmt-automation`:

```text
14 passed in 0.26s
```

Covered tests:

```text
tests/test_backup_assurance_foundation_wiring.py
tests/test_operator_attention.py
tests/test_operator_attention_cross_domain_runtime_integration.py
```

Accepted interpretation:

```text
established backup ordering invariant preserved: true
cross-domain backup-before-operator dependency preserved: true
existing operator-attention behavior remains green: true
corrective repository wiring accepted: true
corrective unit deployed: false
```

The currently installed unit still reflects the earlier deployed ordering until corrective redeployment occurs.

## Exact next gate — CORRECTIVE DRY RUN ONLY

Run on `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-cross-domain-runtime-integration
sudo bash scripts/deploy-operator-attention-runtime.sh
```

This must perform no mutation and print the same bounded deployment plan. Do not use `--apply` yet.

If dry-run is accepted:

1. record the dry-run;
2. request fresh explicit authorization because the systemd unit content changed after the original authorization;
3. only after fresh authorization, run the same helper with `--apply`;
4. verify safe cross-domain artifact content again;
5. rerun the full repository suite;
6. PR/squash-merge only if all gates pass.

## Authorization boundary

Previous authorization does not automatically cover the corrected unit content.

Corrective `--apply` is NOT authorized yet.

Do not broaden permissions, rerun bootstrap, change Kubernetes RBAC/kubeconfig, add services/timers/datastores, or perform remediation.

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
