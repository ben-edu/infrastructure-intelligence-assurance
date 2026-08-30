# Milestone 7 — Cross-Domain Installed Runtime Integration

Date: 2026-08-30
Status: CORRECTIVE ORDERING VALIDATION IN PROGRESS
Mode: bounded management-host runtime integration in the existing five-minute collector

## Scope

This slice installs the already-accepted Kubernetes-plus-backup operator projection into the existing `infra-assurance-kubernetes.service` oneshot collector path.

No new service, timer, identity, datastore, Kubernetes RBAC, kubeconfig, Git source configuration, or filesystem permission was introduced.

Runtime identity and sandbox remain:

```text
User=infra-assurance
Group=infra-assurance
PYTHONPATH=/opt/infra-assurance/src
NoNewPrivileges=true
ProtectHome=true
existing ReadWritePaths only
```

## Repository focused validation

Initial focused integration tests:

```text
10 passed in 0.21s
```

These tests covered existing operator-attention behavior, cross-domain systemd wiring, ordering of backup assurance before operator projection, and service identity constraints.

## Deployment dry run

Dry-run command:

```bash
sudo bash scripts/deploy-operator-attention-runtime.sh
```

Accepted interpretation:

```text
management-host mutation performed: false
Kubernetes mutation performed: false
systemd mutation performed: false
installed runtime mutation performed: false
artifact write performed by helper: false
deployment scope operator-reviewed: true
```

The helper explicitly excluded `bootstrap-observer.sh`, Kubernetes RBAC changes, kubeconfig changes, Git source changes, new services/timers, and permission broadening.

## Explicit authorization

The user explicitly authorized only the bounded deployment described by the dry-run.

Authorization covered:

```text
install operator_attention.py
install backup_operator_adapter.py
install operator_attention_backup.py
replace the existing infra-assurance-kubernetes.service unit definition
systemctl daemon-reload
start the existing oneshot service once
verify generated operator-attention artifacts and cross-domain scope
```

Authorization did not extend to broader infrastructure mutation, Kubernetes RBAC/kubeconfig changes, permission broadening, remediation, new services/timers/datastores, or unrelated changes.

## Live bounded deployment

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

This establishes that the existing oneshot collector completed successfully and produced the expected cross-domain operator artifacts under the intended service identity.

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

## Full-suite regression gate — FAILED

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

This is a repository/runtime ordering regression, not an evidence observation failure and not evidence that backup protection is absent.

The deployed runtime still completed successfully and produced a valid cross-domain artifact, but the slice is not merge-ready while this ordering invariant is violated.

## Corrective ordering decision

The existing backup-assurance ordering invariant is preserved rather than weakening or deleting its test.

The corrected repository order is:

```text
1. kubernetes_runtime completes;
2. existing routing / incident / observability ExecStartPost chain remains in its prior order;
3. prometheus_rule_context_integration completes;
4. backup_assurance_foundation produces backup-assurance.json/md;
5. operator_attention_backup runs immediately after backup assurance and consumes inventory/context/change-context/backup-assurance.
```

This is the smallest compatible ordering because:

- `backup_assurance_foundation` retains its established position after observability post-steps;
- `operator_attention_backup` still receives a backup artifact generated in the same oneshot service execution;
- no service, timer, permission, RBAC, kubeconfig, datastore, or runtime identity changes are introduced.

Repository corrective commit:

```text
1ca5d15bd925322e641af5c395f48623c3353d59
```

The corrective unit has NOT yet been redeployed. The currently installed runtime still reflects the earlier ordering until a separately reviewed corrective redeployment occurs.

## Trust boundary

- no broader infrastructure mutation was authorized or performed by this slice;
- runtime identity remains `infra-assurance`, not root;
- no new service, timer, datastore, RBAC, kubeconfig, or permission broadening was introduced;
- derived operator artifacts do not replace source evidence;
- no raw source artifact, per-asset backup detail, secret, credential, raw Terraform state, Kubernetes Secret value, or sensitive connection string was projected in validation output;
- no remediation is authorized or implied;
- generated operational semantics preserve `mutation_allowed=false`.

## Next gate

Run focused repository tests covering the preserved backup ordering invariant and cross-domain operator wiring.

Only after those tests pass should a dry-run of the unchanged bounded deployment helper be repeated. Because the unit content changed after the original authorization, corrective redeployment requires a fresh explicit authorization before `--apply`.

After corrected deployment and safe artifact verification, rerun the full repository suite before PR/merge.
