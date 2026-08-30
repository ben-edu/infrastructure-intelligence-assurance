# Milestone 7 — Cross-Domain Installed Runtime Integration

Date: 2026-08-30
Status: CORRECTIVE ORDERING VALIDATED PENDING DRY-RUN AND REDEPLOYMENT
Mode: bounded management-host runtime integration in the existing five-minute collector

## Scope

This slice installs the already-accepted Kubernetes-plus-backup operator projection into the existing `infra-assurance-kubernetes.service` oneshot collector path.

No new service, timer, identity, datastore, Kubernetes RBAC, kubeconfig, Git source configuration, or filesystem permission is introduced.

Runtime identity and sandbox remain:

```text
User=infra-assurance
Group=infra-assurance
PYTHONPATH=/opt/infra-assurance/src
NoNewPrivileges=true
ProtectHome=true
existing ReadWritePaths only
```

## Initial repository validation

Initial focused integration tests:

```text
10 passed in 0.21s
```

These tests covered existing operator-attention behavior, cross-domain systemd wiring, ordering of backup assurance before operator projection, and service identity constraints.

## Initial deployment dry run and authorization

The bounded dry-run was accepted. The user then explicitly authorized only the reviewed management-host deployment scope.

The helper explicitly excluded `bootstrap-observer.sh`, Kubernetes RBAC changes, kubeconfig changes, Git source changes, new services/timers, and permission broadening.

## Initial live bounded deployment

Executed:

```bash
sudo bash scripts/deploy-operator-attention-runtime.sh --apply
```

Accepted helper output:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
runtime_scope=KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
```

## Safe generated-artifact verification

Only allowlisted fields from `/var/lib/infra-assurance/evidence/operator-attention.json` were printed.

Accepted contract metadata:

```text
operator_attention_version: 0.1
cluster_id: k3s-main
mutation_allowed: False
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
source_artifacts: inventory.json,context.json,change-context.json,backup-assurance.json
```

Accepted summary:

```text
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
```

Accepted attention items:

```text
1. topology / SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES / AMBIGUOUS / Service/monitoring/loki-headless
2. drift / DECLARED_OBSERVED_DRIFT / DRIFT / Ingress/validation/nginx-validation
3. backup_assurance / BACKUP_PROTECTION_UNKNOWN / UNKNOWN / count=37
4. backup_assurance / RESTORE_VERIFICATION_UNKNOWN / UNKNOWN / count=37
5. backup_assurance / AUTHORITATIVE_BACKUP_SOURCE_NOT_INTEGRATED / UNKNOWN
```

Accepted required verification categories:

```text
OBSERVE_BACKUP_MECHANISM -> BACKUP_MECHANISM
OBSERVE_LAST_SUCCESSFUL_BACKUP -> LAST_SUCCESSFUL_BACKUP
OBSERVE_BACKUP_RETENTION -> BACKUP_RETENTION
OBSERVE_BACKUP_FAILURE_DOMAIN -> BACKUP_FAILURE_DOMAIN
OBSERVE_BACKUP_INTEGRITY_VERIFICATION -> BACKUP_INTEGRITY_VERIFICATION
OBSERVE_RESTORE_TEST -> RESTORE_TEST
OBSERVE_RPO_TARGET_AND_RESULT -> RPO_TARGET_AND_RESULT
OBSERVE_RTO_TARGET_AND_RESULT -> RTO_TARGET_AND_RESULT
```

All eight require an authoritative source.

Accepted trust checks:

```text
unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
authoritative_backup_evidence_required_for_unprotected: True
```

Accepted truncation state:

```text
attention_now_truncated: False
required_live_verification_truncated: False
```

## Full-suite regression gate — FAILED AND PRESERVED

The first full repository suite after deployment returned:

```text
1 failed, 428 passed in 2.49s
```

Failing test:

```text
tests/test_backup_assurance_foundation_wiring.py::test_backup_assurance_runs_after_observability_post_steps
```

Observed assertion:

```text
prometheus_rule_context_integration index: 5856
backup_assurance_foundation index: 2803
required invariant: prometheus_rule_context_integration < backup_assurance_foundation
```

This was a repository/runtime ordering regression, not an evidence observation failure. The established test was not weakened or deleted.

## Corrective ordering decision

The corrected repository order is:

```text
1. kubernetes_runtime completes;
2. existing routing / incident / observability ExecStartPost chain remains in its prior order;
3. prometheus_rule_context_integration completes;
4. backup_assurance_foundation produces backup-assurance.json/md;
5. operator_attention_backup runs immediately after backup assurance and consumes inventory/context/change-context/backup-assurance.
```

This preserves both ordering invariants:

```text
prometheus_rule_context_integration < backup_assurance_foundation
backup_assurance_foundation < operator_attention_backup
```

## Corrective focused validation — ACCEPTED

Executed on `mgmt-automation`:

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

The currently installed runtime still reflects the earlier deployed ordering until corrective redeployment occurs.

## Trust boundary

- no broader infrastructure mutation was authorized or performed by this slice;
- runtime identity remains `infra-assurance`, not root;
- no new service, timer, datastore, RBAC, kubeconfig, or permission broadening is introduced;
- derived operator artifacts do not replace source evidence;
- no raw source artifact, per-asset backup detail, secret, credential, raw Terraform state, Kubernetes Secret value, or sensitive connection string was projected in validation output;
- no remediation is authorized or implied;
- generated operational semantics preserve `mutation_allowed=false`.

## Next gate

Repeat the deployment helper without `--apply` as a no-mutation dry-run against the corrected repository unit.

Because the systemd unit content changed after the original authorization, corrective redeployment requires a fresh explicit authorization before `--apply`.

After corrected deployment and safe artifact verification, rerun the full repository suite before PR/merge.
