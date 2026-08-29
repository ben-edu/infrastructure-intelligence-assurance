# Milestone 7 — Backup Assurance Operator Adapter

Date: 2026-08-29
Status: ACCEPTED PENDING FULL-SUITE GATE
Mode: compact read-only operator projection over existing backup-assurance evidence

## Scope

This slice adapts the already-generated backup assurance artifact into a compact operator-facing summary without querying infrastructure or creating a new source of truth.

Source artifact:

```text
/var/lib/infra-assurance/evidence/backup-assurance.json
```

Projection scope:

```text
BACKUP_ASSURANCE_EXISTING_EVIDENCE_ONLY
```

The adapter projects only aggregate counts, compact attention codes, and deduplicated authoritative verification categories. Per-asset details and raw unknown text are discarded.

## Repository validation

Focused tests:

```text
6 passed in 0.05s
```

## Live validation

Accepted live probe:

```text
source_status: COMPLETE
backup_assurance_source_status: COMPLETE
cluster_id: k3s-main
scope: BACKUP_ASSURANCE_EXISTING_EVIDENCE_ONLY
discovery_rc=0
```

Safety:

```text
mutation_allowed: False
live_infrastructure_query_performed: False
source_artifact_written: False
raw_source_artifact_projected: False
asset_details_projected: False
secrets_or_credentials_projected: False
```

Accepted compact summary:

```text
assets_total: 37
assets_stale: 0
assets_freshness_unknown: 0
protection_unknown: 37
restore_verification_unknown: 37
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
attention_total: 3
required_verification_categories_total: 8
```

Accepted attention items:

```text
BACKUP_PROTECTION_UNKNOWN / UNKNOWN / count=37
RESTORE_VERIFICATION_UNKNOWN / UNKNOWN / count=37
AUTHORITATIVE_BACKUP_SOURCE_NOT_INTEGRATED / UNKNOWN
```

Accepted authoritative verification categories:

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

The current backup-assurance foundation identifies 37 Kubernetes PVC assets and shows that protection and restore verification remain UNKNOWN for all 37 because no authoritative backup source is integrated into this foundation artifact.

This is not evidence that the assets are unprotected. The source reports:

```text
unprotected_claims: 0
```

Therefore the adapter must preserve:

```text
UNKNOWN != UNPROTECTED
```

Likewise, restore verification UNKNOWN is not evidence that a recovery test is overdue. This slice does not make a recovery-test-overdue claim because no authoritative schedule/timing evidence is integrated.

Trust checks accepted from the probe:

```text
unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
authoritative_backup_evidence_required_for_unprotected: True
```

The eight verification categories describe what authoritative evidence is still required. They are evidence-routing requirements, not remediation instructions.

## Trust boundary

- infrastructure interaction remains read-only;
- only the existing backup-assurance artifact is read;
- raw source content and per-asset details are not projected;
- UNKNOWN protection is never converted into UNPROTECTED;
- restore verification UNKNOWN is never converted into overdue restore testing;
- no secret, credential, raw Terraform state, Kubernetes Secret value, or sensitive connection string enters the projection;
- no remediation is authorized or implied.

## Remaining gate

A full repository regression suite is required before PR/merge because reusable implementation and tests changed.
