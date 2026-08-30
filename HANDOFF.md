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
corrective redeployment authorized/performed: true
```

## Accepted cross-domain contract baseline

Accepted reports:

```text
docs/reports/2026-08-30-m7-backup-assurance-operator-integration.md
docs/reports/2026-08-30-m7-cross-domain-runtime-contract.md
docs/reports/2026-08-30-m7-cross-domain-runtime-integration.md
```

Accepted cross-domain contract state:

```text
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

Goal:

```text
Run the accepted cross-domain operator command in the existing five-minute collector path under infra-assurance while preserving established collector ordering invariants.
```

Exact branch scope:

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

## Validation — ACCEPTED

Initial focused tests:

```text
10 passed in 0.21s
```

The first bounded deployment completed successfully and generated valid cross-domain artifacts, but the first full suite exposed a real ordering regression:

```text
1 failed, 428 passed in 2.49s
```

Preserved failing invariant:

```text
prometheus_rule_context_integration < backup_assurance_foundation
```

The established test was not weakened or removed.

Corrective intended/runtime order:

```text
prometheus_rule_context_integration
< backup_assurance_foundation
< operator_attention_backup
```

Corrective focused validation:

```text
14 passed in 0.26s
```

A fresh dry-run and fresh explicit authorization were obtained before corrective redeployment.

Corrective bounded redeployment output:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
runtime_scope=KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
```

Installed-order verification:

```text
observability_before_backup: True
backup_before_operator: True
correct_order: True
```

Regenerated artifact contract/trust verification:

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

Final full repository suite:

```text
429 passed in 2.15s
```

The previously observed ordering regression is therefore closed on the corrected branch and corrected installed runtime.

## Merge gate — READY

Before merge:

1. compare branch against accepted main `7411cfe3f84c29750761f42dd74ee6f870773076`;
2. verify exactly the five intended files listed above;
3. ensure no temporary/debug/placeholder files exist;
4. create a non-draft PR;
5. verify changed filenames and mergeability;
6. squash-merge;
7. carry the new accepted main SHA forward.

## Exact next useful step after merge

Do not broaden backup probing merely to eliminate UNKNOWNs. The next M7 slice should build on the now-installed cross-domain operator projection and address the next smallest operator-intelligence capability justified by the roadmap and current evidence.

Any further management-host or infrastructure mutation requires its own explicit authorization boundary.

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
