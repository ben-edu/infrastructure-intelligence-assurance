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

Prepared runtime order:

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

This confirmed the existing operator-attention tests remain green, the backup assurance step precedes the cross-domain operator projection, and runtime wiring remains under `infra-assurance`.

## Deployment dry run — ACCEPTED

Dry-run command:

```bash
sudo bash scripts/deploy-operator-attention-runtime.sh
```

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

The user explicitly authorized only this bounded management-host deployment:

```text
install operator_attention.py
install backup_operator_adapter.py
install operator_attention_backup.py
replace existing infra-assurance-kubernetes.service unit definition
systemctl daemon-reload
start existing oneshot service once
verify generated operator-attention artifacts and cross-domain scope
```

Authorization does NOT extend to broader infrastructure mutation, Kubernetes RBAC/kubeconfig changes, filesystem permission broadening, new services/timers/datastores, remediation, or unrelated changes.

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

Accepted interpretation:

```text
bounded management-host deployment completed: true
existing oneshot collector completed successfully: true
operator-attention JSON produced: true
operator-attention Markdown produced: true
runtime identity remains infra-assurance: true
cross-domain runtime scope observed: true
broader infrastructure mutation authorized/performed by this gate: false
```

This proves installed runtime deployment and artifact generation. It does not by itself validate every allowlisted content field inside the generated artifact.

## Exact next gate — SAFE GENERATED-ARTIFACT CONTENT VERIFICATION

Read only allowlisted fields from:

```text
/var/lib/infra-assurance/evidence/operator-attention.json
```

Acceptance requires:

```text
cluster_id: k3s-main
mutation_allowed: False
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
source_artifacts include inventory.json, context.json, change-context.json, backup-assurance.json
summary counts are present integers
backup_unprotected_claims: 0 unless authoritative evidence legitimately changed
unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
no raw source data, per-asset backup details, secret, credential, raw Terraform state, or Kubernetes Secret value printed
```

Current prior accepted counts are a comparison baseline only, not immutable expected values. If current evidence changed legitimately, changed counts are not a failure by themselves.

After safe content verification succeeds:

1. create `docs/reports/2026-08-30-m7-cross-domain-runtime-integration.md` with exact accepted deployment/content evidence;
2. update this handoff with the accepted content gate;
3. run the full repository suite on the current branch head;
4. verify exact intended branch scope and no temporary/debug files;
5. create/inspect a non-draft PR;
6. verify changed filenames and mergeability;
7. squash-merge and carry the new accepted main SHA forward.

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
