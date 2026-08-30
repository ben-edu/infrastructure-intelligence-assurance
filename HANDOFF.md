# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #82: 0649699dfcd09828fce6937fcc27ec870daf057a
active branch: agent/m7-cross-domain-runtime-contract
Milestone 7: ACTIVE
management host: mgmt-automation
broader infrastructure mutation authorized: false
```

## Accepted M7 runtime baseline

The installed five-minute collector still produces Kubernetes-only operator-attention JSON/Markdown under `infra-assurance`.

Installed runtime scope remains:

```text
KUBERNETES_EXISTING_EVIDENCE_ONLY
```

Accepted Kubernetes attention baseline:

```text
attention_now_total: 2
Service/monitoring/loki-headless -> SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES / AMBIGUOUS
Ingress/validation/nginx-validation -> DECLARED_OBSERVED_DRIFT / DRIFT
```

Preserve rejected/incomplete attempts:

```text
interactive-user operator-attention probe: FAILED_TO_OBSERVE / PermissionError
service-identity probe from /home/ben source tree: FAILED_TO_OBSERVE before code execution
```

Do not reuse either as negative evidence.

## Accepted backup-assurance operator evidence

Accepted reports:

```text
docs/reports/2026-08-29-m7-backup-assurance-operator-adapter.md
docs/reports/2026-08-30-m7-backup-assurance-operator-integration.md
```

Accepted cross-domain evidence:

```text
focused tests: 6 passed in 0.06s
live read-only probe: source_status=COMPLETE / discovery_rc=0
full suite: 424 passed in 2.13s
source_artifacts_loaded: 4
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

## Active slice — cross-domain runtime contract

Accepted report:

```text
docs/reports/2026-08-30-m7-cross-domain-runtime-contract.md
```

Goal:

```text
Make the already-accepted cross-domain operator projection executable as a file-writing runtime command, without changing the installed collector or systemd yet.
```

Changed files expected for this slice:

```text
HANDOFF.md
docs/reports/2026-08-30-m7-cross-domain-runtime-contract.md
src/infra_assurance/operator_attention_backup.py
tests/test_operator_attention_backup_runtime.py
```

Accepted CLI contract:

```text
python3 -m infra_assurance.operator_attention_backup
  --inventory <inventory.json>
  --context <context.json>
  --change-context <change-context.json>
  --backup-assurance <backup-assurance.json>
  --out <operator-attention.json>
  --summary-out <operator-attention.md>
```

This branch does NOT change:

```text
systemd
/opt installed runtime
collector service/timer
infrastructure
permissions
datastores
```

## Validation — ACCEPTED / MERGE-READY

Repository validation:

```text
focused tests: 8 passed in 0.46s
full repository suite: 426 passed in 2.48s
```

Live no-deploy contract check:

```text
source_status: COMPLETE
source_artifacts_loaded: 4
cluster_id: k3s-main
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
discovery_rc=0
```

Accepted safety:

```text
mutation_allowed: False
live_infrastructure_query_performed: False
source_artifacts_written: False
systemd_modified: False
installed_runtime_modified: False
raw_source_artifacts_projected: False
backup_asset_details_projected: False
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

Accepted trust checks:

```text
unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
authoritative_backup_evidence_required_for_unprotected: True
```

The one-time `sudo` execution was validation-only because repository code is under `/home/ben` while evidence artifacts are protected. It is not the target runtime privilege model.

## Merge gate

All contract gates passed. Before merge:

1. verify branch scope is exactly the four intended files listed above;
2. ensure no temporary/debug/placeholder files exist;
3. create/inspect a non-draft PR;
4. verify changed filenames and mergeability;
5. squash-merge;
6. carry the new accepted main SHA into the next checkpoint.

## Exact next useful step after merge

The next smallest useful M7 step is a separate installed-runtime integration slice: replace the currently installed Kubernetes-only operator command with the accepted cross-domain command in the existing five-minute collector path.

That step is a management-host mutation because it changes installed code/systemd/runtime behavior. It must remain separately authorized and bounded; do not broaden Kubernetes RBAC, kubeconfig, permissions, services, timers, or datastores.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- existing infrastructure observation remains read-only except separately authorized bounded management-host deployment;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- UNKNOWN protection is never treated as UNPROTECTED;
- restore verification UNKNOWN is never treated as overdue restore testing;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied by an attention item;
- generated operational semantics keep `mutation_allowed=false`.
