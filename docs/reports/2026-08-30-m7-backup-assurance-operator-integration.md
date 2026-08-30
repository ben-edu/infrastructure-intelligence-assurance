# Milestone 7 — Backup Assurance Operator Integration

Date: 2026-08-30
Status: ACCEPTED
Mode: bounded cross-domain operator projection over existing Kubernetes and backup-assurance evidence

## Scope

This slice combines the accepted Kubernetes operator-attention projection with the accepted compact backup-assurance operator adapter.

Source artifacts:

```text
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/context.json
/var/lib/infra-assurance/evidence/change-context.json
/var/lib/infra-assurance/evidence/backup-assurance.json
```

Projection scope:

```text
KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
```

No live infrastructure query, source artifact write, service change, datastore, permission change, or management-host runtime mutation is part of this contract slice.

## Repository validation

Focused tests:

```text
6 passed in 0.06s
```

Full repository suite:

```text
424 passed in 2.13s
```

## Live validation

Accepted read-only probe:

```text
source_status: COMPLETE
source_artifacts_loaded: 4
cluster_id: k3s-main
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
discovery_rc=0
```

Safety:

```text
mutation_allowed: False
live_infrastructure_query_performed: False
source_artifacts_written: False
raw_source_artifacts_projected: False
backup_asset_details_projected: False
secrets_or_credentials_projected: False
```

## Accepted combined operator summary

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

Accepted backup verification categories:

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

All eight categories require an authoritative source.

## Accepted interpretation

The combined operator projection preserves the two existing Kubernetes attention items and adds exactly three compact backup-assurance gaps. The backup layer contributes aggregate assurance gaps only; per-asset backup details are not projected.

Current backup evidence still supports:

```text
protection_unknown: 37
restore_verification_unknown: 37
unprotected_claims: 0
```

Therefore the combined projection must preserve:

```text
UNKNOWN != UNPROTECTED
```

Likewise, restore verification UNKNOWN does not establish that recovery testing is overdue. No overdue recovery-test claim is made.

Trust checks accepted from the live probe:

```text
unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
authoritative_backup_evidence_required_for_unprotected: True
```

`recent_changes_total=0` and `unknowns_total=0` remain bounded absence statements within the loaded source artifacts and their own freshness/trust boundaries. They are not universal absence claims.

## Trust boundary

- existing infrastructure interaction remains read-only;
- only existing derived evidence artifacts are read;
- no source artifact is modified;
- raw source artifacts and backup per-asset details are not projected;
- UNKNOWN protection is never converted into UNPROTECTED;
- restore verification UNKNOWN is never converted into overdue restore testing;
- no secret, credential, raw Terraform state, Kubernetes Secret value, or sensitive connection string enters the projection;
- no remediation is authorized or implied;
- generated operational semantics keep `mutation_allowed=false`.

## Acceptance

The contract slice is accepted and merge-ready after focused, live read-only, and full-suite validation.
