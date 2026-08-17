# Milestone 5 — PostgreSQL Database-Aware Backup Source Discovery

Date: 2026-08-17
Host: `mgmt-automation`
Branch: `agent/m5-postgresql-database-backup-source-discovery`
Mode: read-only discovery

## Result

Accepted bounded discovery completed successfully with `discovery_rc=0`.

### Kubernetes accepted PostgreSQL workload scope

Eight previously accepted PostgreSQL workload subjects were observed successfully:

- `drfarah-staging/StatefulSet/drfarah-staging-postgres`
- `fastapi-platform/Deployment/postgres`
- `fastapi-platform-dev/Deployment/postgres`
- `keycloak/StatefulSet/keycloak-postgresql`
- `openproject/StatefulSet/openproject-postgresql`
- `soria-academie/StatefulSet/academie-postgres`
- `soria-prospecting/Deployment/soria-postgres`
- `toilettage/StatefulSet/toilettage-postgres`

For all eight subjects:

```text
observation: OBSERVED
backup_container_signals: NONE
backup_init_signals: NONE
backup_configmap_signals: NONE
database_backup_mechanism: DATABASE_BACKUP_MECHANISM_UNKNOWN
```

The bounded Kubernetes CronJob/Job source was complete and returned:

```text
matching_cronjobs_jobs: 0
```

This is source-scoped negative evidence only. It is not an `UNPROTECTED` classification.

## Management-host PostgreSQL metadata

Backup-capable tooling observed:

```text
pg_basebackup: PRESENT
pg_dump: PRESENT
pg_dumpall: PRESENT
```

Specialized backup tooling not observed in the inspected executable scope:

```text
pgBackRest: NOT_PRESENT
Barman: NOT_PRESENT
barman-cloud-backup: NOT_PRESENT
WAL-G / walg: NOT_PRESENT
```

Systemd metadata source was complete. Matching template units were present:

```text
pg_basebackup@.service
pg_basebackup@.timer
pg_dump@.service
pg_dump@.timer
```

No instantiated matching units were observed, no active matching timers were observed, and no matching cron filenames were observed.

Therefore:

```text
backup-capable tooling: OBSERVED
configured PostgreSQL database-aware backup mechanism: UNKNOWN
successful database-aware backup execution: UNKNOWN
```

## Summary

```text
expected_kubernetes_postgresql_workloads: 8
kubernetes_workloads_observed: 8
kubernetes_workloads_failed_to_observe: 0
kubernetes_workloads_with_declared_backup_signal: 0
kubernetes_workloads_database_backup_mechanism_unknown: 8
matching_kubernetes_cronjobs_jobs: 0
management_host_configured_backup_signal: 0
backup_execution_success_claims: 0
backup_artifact_validity_claims: 0
retention_effectiveness_claims: 0
restore_verification_claims: 0
unprotected_claims: 0
rpo_violation_claims: 0
discovery_rc: 0
```

## Interpretation boundary

A backup-looking container/image, ConfigMap name, systemd unit, timer, cron filename, or installed tool is mechanism/source metadata only.

Tool presence alone is backup capability, not configured execution and not successful database-aware backup evidence.

Absence of a signal in this bounded projection remains `DATABASE_BACKUP_MECHANISM_UNKNOWN`, not `UNPROTECTED`.

No database connection, dump/WAL inspection, backup-content inspection, retention-effectiveness evaluation, restore verification, RPO evaluation, or RTO evaluation was performed.

## Trust boundary

Kubernetes env values, Secret names/keys/values, command/args, raw ConfigMap contents, and raw workload objects were not printed.

Management-host cron contents, script contents, database rows, dumps, WAL contents, credentials, and connection strings were not read or printed.

Only read-only Kubernetes/system metadata and local executable presence were inspected. No infrastructure, workload, database, backup, or scheduling state was changed.
