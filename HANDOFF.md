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
cross-domain runtime deployment authorized: true
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

Accepted report:

```text
docs/reports/2026-08-30-m7-cross-domain-runtime-integration.md
```

Goal:

```text
Run the accepted cross-domain operator command in the existing five-minute collector path under infra-assurance, using backup-assurance.json generated earlier in the same oneshot service execution.
```

Prepared repository changes:

```text
HANDOFF.md
docs/reports/2026-08-30-m7-cross-domain-runtime-integration.md
scripts/deploy-operator-attention-runtime.sh
systemd/infra-assurance-kubernetes.service
tests/test_operator_attention_cross_domain_runtime_integration.py
```

Accepted runtime order:

```text
1. existing kubernetes_runtime ExecStart completes;
2. backup_assurance_foundation produces backup-assurance.json/md;
3. operator_attention_backup consumes inventory/context/change-context/backup-assurance;
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

No new service, timer, identity, datastore, Kubernetes RBAC, kubeconfig, Git source config, or filesystem permission was introduced.

## Repository focused validation — ACCEPTED

Executed on `mgmt-automation`:

```text
10 passed in 0.21s
```

## Deployment dry run — ACCEPTED

Accepted dry-run interpretation:

```text
management-host mutation performed: false
Kubernetes mutation performed: false
systemd mutation performed: false
installed runtime mutation performed: false
artifact write performed by helper: false
deployment scope operator-reviewed: true
```

## Deployment authorization — ACCEPTED

The user explicitly authorized only the bounded deployment described by the dry-run.

Authorization did not extend to broader infrastructure mutation, Kubernetes RBAC/kubeconfig changes, permission broadening, remediation, new services/timers/datastores, or unrelated changes.

## Live bounded deployment — ACCEPTED

Executed on `mgmt-automation`:

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

## Safe generated-artifact content verification — ACCEPTED

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

Accepted attention:

```text
topology / SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES / AMBIGUOUS / Service/monitoring/loki-headless
drift / DECLARED_OBSERVED_DRIFT / DRIFT / Ingress/validation/nginx-validation
backup_assurance / BACKUP_PROTECTION_UNKNOWN / UNKNOWN / count=37
backup_assurance / RESTORE_VERIFICATION_UNKNOWN / UNKNOWN / count=37
backup_assurance / AUTHORITATIVE_BACKUP_SOURCE_NOT_INTEGRATED / UNKNOWN
```

Accepted required backup/recovery verification categories:

```text
OBSERVE_BACKUP_MECHANISM
OBSERVE_LAST_SUCCESSFUL_BACKUP
OBSERVE_BACKUP_RETENTION
OBSERVE_BACKUP_FAILURE_DOMAIN
OBSERVE_BACKUP_INTEGRITY_VERIFICATION
OBSERVE_RESTORE_TEST
OBSERVE_RPO_TARGET_AND_RESULT
OBSERVE_RTO_TARGET_AND_RESULT
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

The installed runtime therefore reproduces the accepted cross-domain contract on current evidence under `infra-assurance`.

Do not infer unprotected assets from `backup_protection_unknown=37`.
Do not infer overdue restore testing from `backup_restore_verification_unknown=37`.

## Exact next gate — FULL REPOSITORY SUITE

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-cross-domain-runtime-integration
python3 -m pytest -q
```

Do not use strict interactive shell mode.

If the full suite passes:

1. record the exact pass count/time in this handoff and the runtime-integration report;
2. verify exact branch scope is five intended files:
   - `HANDOFF.md`
   - `docs/reports/2026-08-30-m7-cross-domain-runtime-integration.md`
   - `scripts/deploy-operator-attention-runtime.sh`
   - `systemd/infra-assurance-kubernetes.service`
   - `tests/test_operator_attention_cross_domain_runtime_integration.py`
3. ensure no temporary/debug/placeholder files exist;
4. create/inspect a non-draft PR;
5. verify changed filenames and mergeability;
6. squash-merge and carry the new accepted main SHA forward.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- infrastructure observation remains read-only except the explicitly authorized bounded management-host deployment already performed;
- runtime identity stays `infra-assurance`, not root;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- UNKNOWN protection is never treated as UNPROTECTED;
- restore verification UNKNOWN is never treated as overdue restore testing;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied by an attention item;
- generated operational semantics keep `mutation_allowed=false`.
