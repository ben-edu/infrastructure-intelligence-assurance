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

The installed five-minute collector currently produces Kubernetes-only operator-attention JSON/Markdown under `infra-assurance`.

Accepted reports:

```text
docs/reports/2026-08-29-m7-operator-attention-summary-contract.md
docs/reports/2026-08-29-m7-operator-attention-runtime-integration.md
```

Current installed runtime scope remains:

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

Accepted cross-domain contract validation:

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

Prepared changes:

```text
HANDOFF.md
docs/reports/2026-08-30-m7-cross-domain-runtime-contract.md
src/infra_assurance/operator_attention_backup.py
tests/test_operator_attention_backup_runtime.py
```

The cross-domain module provides a CLI contract:

```text
python3 -m infra_assurance.operator_attention_backup
  --inventory <inventory.json>
  --context <context.json>
  --change-context <change-context.json>
  --backup-assurance <backup-assurance.json>
  --out <operator-attention.json>
  --summary-out <operator-attention.md>
```

The writer:

```text
- reads only the four accepted derived artifacts;
- uses the accepted cross-domain builder;
- writes JSON and Markdown atomically using existing io_utils;
- performs no live infrastructure query;
- projects no per-asset backup details;
- preserves mutation_allowed=false;
- preserves UNKNOWN != UNPROTECTED;
- preserves restore verification UNKNOWN != recovery test overdue.
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

## Repository validation — ACCEPTED

Focused tests executed on `mgmt-automation`:

```text
8 passed in 0.46s
```

## Live no-deploy runtime contract check — ACCEPTED

The one-time privileged projection used repository code only to read the four protected existing artifacts. It did not write output files, modify systemd, modify `/opt`, or query live infrastructure.

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

Accepted source state:

```text
source_status: COMPLETE
source_artifacts_loaded: 4
cluster_id: k3s-main
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
discovery_rc=0
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

The one-time `sudo` execution is validation-only because repository code remains under `/home/ben` while the evidence artifacts are protected. It is not the target runtime privilege model.

## Exact next gate — FULL REPOSITORY SUITE

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-cross-domain-runtime-contract
python3 -m pytest -q
```

Do not use strict interactive shell mode.

If the full suite passes:

1. record exact pass count/time in this handoff and the runtime-contract report;
2. verify exact branch scope is four intended files:
   - `HANDOFF.md`
   - `docs/reports/2026-08-30-m7-cross-domain-runtime-contract.md`
   - `src/infra_assurance/operator_attention_backup.py`
   - `tests/test_operator_attention_backup_runtime.py`
3. ensure no temporary/debug/placeholder files exist;
4. create/inspect a non-draft PR;
5. verify changed filenames and mergeability;
6. squash-merge and carry the new accepted main SHA forward.

Only after merge should installed runtime/systemd integration be considered. That remains a separate management-host mutation gate requiring explicit authorization.

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
