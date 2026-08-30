# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #81: 27dad7917299b90688fd418b70bbec585c94ea7b
active branch: agent/m7-backup-assurance-operator-integration
Milestone 7: ACTIVE
management host: mgmt-automation
broader infrastructure mutation authorized: false
```

## Accepted M7 operator-attention runtime baseline

Accepted reports:

```text
docs/reports/2026-08-29-m7-operator-attention-summary-contract.md
docs/reports/2026-08-29-m7-operator-attention-runtime-integration.md
```

Accepted runtime state:

```text
operator-attention runtime identity: infra-assurance
operator-attention JSON/Markdown: generated in existing collector cycle
full suite at runtime integration: 412 passed in 2.00s
cluster: k3s-main
scope: KUBERNETES_EXISTING_EVIDENCE_ONLY
workloads_total: 68
workloads_with_attention: 3
attention_now_total: 2
recent_changes_total: 0
unknowns_total: 0
required_live_verification_total: 0
```

Accepted Kubernetes attention items:

```text
Service/monitoring/loki-headless
  SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES / AMBIGUOUS

Ingress/validation/nginx-validation
  DECLARED_OBSERVED_DRIFT / DRIFT
```

Preserve rejected/incomplete attempts:

```text
interactive-user operator-attention probe: FAILED_TO_OBSERVE / PermissionError
service-identity probe from /home/ben source tree: FAILED_TO_OBSERVE before code execution
```

Do not reuse either as negative evidence.

## Accepted compact backup-assurance adapter

Accepted report:

```text
docs/reports/2026-08-29-m7-backup-assurance-operator-adapter.md
```

Accepted validation:

```text
focused tests: 6 passed in 0.05s
live read-only probe: source_status=COMPLETE / discovery_rc=0
full suite: 418 passed in 1.96s
```

Accepted compact backup summary:

```text
assets_total: 37
protection_unknown: 37
restore_verification_unknown: 37
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
attention_total: 3
required_verification_categories_total: 8
```

Trust semantics that must remain true:

```text
UNKNOWN protection != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
unprotected claims require authoritative backup evidence
```

## Active slice — integrate backup assurance into operator attention

Accepted report:

```text
docs/reports/2026-08-30-m7-backup-assurance-operator-integration.md
```

Goal:

```text
Combine the accepted Kubernetes operator-attention projection with the accepted compact backup-assurance adapter into one bounded cross-domain operator summary, without changing the existing runtime yet.
```

Prepared implementation:

```text
src/infra_assurance/operator_attention_backup.py
tests/test_operator_attention_backup.py
scripts/discovery/m7_backup_assurance_operator_integration_probe.py
```

Cross-domain scope:

```text
KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
```

The active branch does NOT change:

```text
systemd
installed runtime under /opt
collector timer/service
infrastructure
permissions
datastores
```

## Validation — ACCEPTED PENDING FULL SUITE

Focused tests:

```text
6 passed in 0.06s
```

Accepted live read-only probe:

```text
source_status: COMPLETE
source_artifacts_loaded: 4
cluster_id: k3s-main
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
discovery_rc=0
```

Safety:

```text
mutation_allowed: false
live infrastructure query: false
source artifact write: false
raw source projection: false
backup asset detail projection: false
secrets/credentials projection: false
```

Accepted combined summary:

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

Accepted combined attention:

```text
topology / SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES / AMBIGUOUS / Service/monitoring/loki-headless
drift / DECLARED_OBSERVED_DRIFT / DRIFT / Ingress/validation/nginx-validation
backup_assurance / BACKUP_PROTECTION_UNKNOWN / UNKNOWN / count=37
backup_assurance / RESTORE_VERIFICATION_UNKNOWN / UNKNOWN / count=37
backup_assurance / AUTHORITATIVE_BACKUP_SOURCE_NOT_INTEGRATED / UNKNOWN
```

Accepted authoritative backup/recovery verification categories:

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

Trust checks:

```text
unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
authoritative_backup_evidence_required_for_unprotected: True
```

Do not infer unprotected assets from `backup_protection_unknown=37`.
Do not infer overdue restore testing from `backup_restore_verification_unknown=37`.

## Exact next gate — FULL REPOSITORY SUITE

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-backup-assurance-operator-integration
python3 -m pytest -q
```

Do not use strict interactive shell mode.

If the full suite passes:

1. record the exact pass count/time in this handoff and the report;
2. verify branch scope is exactly five intended files:
   - `HANDOFF.md`
   - `docs/reports/2026-08-30-m7-backup-assurance-operator-integration.md`
   - `scripts/discovery/m7_backup_assurance_operator_integration_probe.py`
   - `src/infra_assurance/operator_attention_backup.py`
   - `tests/test_operator_attention_backup.py`
3. ensure no temporary/debug/placeholder files exist;
4. create/inspect a non-draft PR;
5. verify changed filenames and mergeability;
6. squash-merge and carry the new accepted main SHA forward.

Only after this contract slice is merged should runtime integration be considered. Any runtime/systemd deployment remains a separate management-host mutation gate requiring explicit authorization.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- existing infrastructure observation remains read-only;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- UNKNOWN protection is never treated as UNPROTECTED;
- restore verification UNKNOWN is never treated as overdue restore testing;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied by an attention item;
- generated operational semantics keep `mutation_allowed=false`.
