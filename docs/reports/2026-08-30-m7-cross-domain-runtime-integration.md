# Milestone 7 — Cross-Domain Installed Runtime Integration

Date: 2026-08-30
Status: CORRECTIVE REDEPLOYMENT ACCEPTED / CONTENT REVERIFICATION PENDING
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

## Initial deployment and content evidence

The initial bounded deployment completed successfully and produced cross-domain operator artifacts under `infra-assurance`:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
runtime_scope=KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
```

Initial safe generated-artifact verification established:

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

## Preserved full-suite regression

The first full repository suite after deployment returned:

```text
1 failed, 428 passed in 2.49s
```

Failing test:

```text
tests/test_backup_assurance_foundation_wiring.py::test_backup_assurance_runs_after_observability_post_steps
```

Observed required invariant:

```text
prometheus_rule_context_integration < backup_assurance_foundation
```

This was a repository/runtime ordering regression, not an evidence observation failure. The established test was preserved rather than weakened or removed.

## Corrective ordering decision

Corrected repository/runtime order:

```text
1. kubernetes_runtime completes;
2. existing routing / incident / observability ExecStartPost chain remains in prior order;
3. prometheus_rule_context_integration completes;
4. backup_assurance_foundation produces backup-assurance.json/md;
5. operator_attention_backup runs immediately after backup assurance.
```

This preserves both invariants:

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
```

## Corrective deployment dry run — ACCEPTED

The helper was rerun without `--apply` and performed no mutation. It reconfirmed the bounded deployment plan and explicitly excluded `bootstrap-observer.sh`, Kubernetes RBAC changes, kubeconfig changes, Git source changes, new services/timers, and permission broadening.

## Fresh corrective authorization — ACCEPTED

The user explicitly authorized only the corrective redeployment of the reviewed corrected existing unit and the same bounded operator-attention runtime modules.

This authorization did not extend to broader infrastructure mutation, Kubernetes RBAC/kubeconfig changes, permission broadening, new services/timers/datastores, remediation, or unrelated changes.

## Corrective bounded redeployment — ACCEPTED

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

Accepted interpretation:

```text
corrected existing systemd unit installed: true
existing oneshot collector completed successfully: true
operator-attention JSON produced: true
operator-attention Markdown produced: true
runtime identity remains infra-assurance: true
cross-domain runtime scope observed: true
new service/timer created: false
RBAC/kubeconfig/permission broadening performed: false
```

The corrective redeployment proves the corrected installed runtime completed and produced cross-domain artifacts. It does not by itself prove that every allowlisted content/trust field in the newly generated artifact remains valid; that is the next read-only gate.

## Trust boundary

- runtime identity remains `infra-assurance`, not root;
- no new service, timer, datastore, RBAC, kubeconfig, or permission broadening is introduced;
- derived operator artifacts do not replace source evidence;
- no raw source artifact, per-asset backup detail, secret, credential, raw Terraform state, Kubernetes Secret value, or sensitive connection string is needed for validation;
- no remediation is authorized or implied;
- generated operational semantics must preserve `mutation_allowed=false`;
- `UNKNOWN` protection must not be treated as `UNPROTECTED`;
- restore-verification UNKNOWN must not be treated as overdue recovery testing.

## Next gate

Re-read only allowlisted fields from the newly generated `/var/lib/infra-assurance/evidence/operator-attention.json`.

If the content/trust gate is accepted, rerun the full repository suite. PR/merge is permitted only if the full suite passes and exact branch scope remains the five intended files.
