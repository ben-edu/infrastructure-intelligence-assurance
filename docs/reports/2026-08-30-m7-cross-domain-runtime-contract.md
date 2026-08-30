# Milestone 7 — Cross-Domain Runtime Contract

Date: 2026-08-30
Status: ACCEPTED
Mode: read-only runtime command contract over existing Kubernetes and backup-assurance evidence

## Scope

This slice makes the already-accepted cross-domain operator projection executable as a file-writing command without changing the installed collector, systemd unit, `/opt` runtime, infrastructure, permissions, or datastores.

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

The command reads only existing derived artifacts and uses the accepted cross-domain builder. The live gate in this slice was no-deploy and performed no file write.

## Repository validation

Focused tests:

```text
8 passed in 0.46s
```

Full repository suite:

```text
426 passed in 2.48s
```

The focused gate covers the existing cross-domain builder plus runtime JSON/Markdown writing behavior and fail-closed handling for invalid `max-items`.

## Live no-deploy validation

A one-time bounded privileged projection was run from repository code because the repository resides under `/home/ben` while the protected evidence artifacts require elevated read access. This `sudo` use is validation-only and is not the target runtime privilege model.

Accepted safety output:

```text
mutation_allowed: False
live_infrastructure_query_performed: False
source_artifacts_written: False
systemd_modified: False
installed_runtime_modified: False
raw_source_artifacts_projected: False
backup_asset_details_projected: False
```

Accepted source status:

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

## Accepted interpretation

The executable cross-domain runtime contract reproduces the accepted Kubernetes-plus-backup operator projection against current derived evidence without a deployment.

The current evidence supports five aggregate attention items and eight required backup/recovery verification categories. Backup protection and restore verification remain UNKNOWN for 37 assets, while the source still reports zero authoritative unprotected claims.

Therefore:

```text
UNKNOWN != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
```

`recent_changes_total=0` and `unknowns_total=0` remain bounded absence statements within the loaded artifacts and their own freshness/trust boundaries.

## Trust boundary

- no live infrastructure query was performed;
- no evidence source artifact was written;
- no systemd or installed runtime change occurred;
- no raw source artifact or per-asset backup detail was projected;
- no secret, credential, raw Terraform state, Kubernetes Secret value, or sensitive connection string entered the projection;
- no remediation is authorized or implied;
- generated runtime semantics preserve `mutation_allowed=false`.

## Closure

All contract gates passed. Installed runtime/systemd integration remains a separate management-host mutation slice and requires explicit authorization before deployment.
