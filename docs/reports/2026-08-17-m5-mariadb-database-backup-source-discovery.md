# Milestone 5 — MariaDB Database-Aware Backup Source Discovery

Date: 2026-08-17
Status: ACCEPTED
Mode: bounded read-only discovery

## Purpose

Inspect the four already accepted MariaDB/MySQL-compatible Kubernetes candidates for safe metadata that could identify a database-aware backup mechanism without connecting to a database, reading Secret/env values, inspecting command/args, or reading backup contents.

## Safety regression test

```text
2 passed in 0.04s
```

## Accepted Kubernetes candidates

```text
bookstack/Deployment/mariadb
misp/Deployment/mariadb
misp/Deployment/mariadb-v2
moodle/StatefulSet/moodle-mariadb
```

All four subjects were observed successfully.

For every candidate:

```text
backup_container_signals: NONE
backup_init_signals: NONE
backup_configmap_signals: NONE
database_backup_mechanism: DATABASE_BACKUP_MECHANISM_UNKNOWN
```

The complete bounded Kubernetes CronJob/Job source returned:

```text
matching_cronjobs_jobs: 0
```

## Management-host metadata

The inspected executable scope returned:

```text
mariadb-dump: NOT_PRESENT
mysqldump: NOT_PRESENT
mariabackup: NOT_PRESENT
xtrabackup: NOT_PRESENT
mydumper: NOT_PRESENT
mysqlpump: NOT_PRESENT
mysqlbackup: NOT_PRESENT
```

System metadata:

```text
systemd_unit_source_status: COMPLETE
matching_systemd_units: NONE
instantiated_matching_units: NONE
systemd_timer_source_status: COMPLETE
active_matching_timers: NONE
matching_cron_filenames: NONE
cron_directory_observation_failures: 0
management_host_database_backup_mechanism: DATABASE_BACKUP_MECHANISM_UNKNOWN
```

## Accepted summary

```text
expected_kubernetes_mariadb_candidates: 4
kubernetes_candidates_observed: 4
kubernetes_candidates_failed_to_observe: 0
kubernetes_candidates_with_declared_backup_signal: 0
kubernetes_candidates_database_backup_mechanism_unknown: 4
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

## Interpretation

The bounded safe metadata inspected in this slice does not expose a MariaDB/MySQL-compatible database-aware backup mechanism for any of the four accepted candidates.

This is not a claim that no backup exists. The accepted state is `DATABASE_BACKUP_MECHANISM_UNKNOWN`.

Signal or tool presence would establish mechanism/source metadata only. It would not establish successful execution, artifact validity, retention effectiveness, restore verification, RPO, RTO, or protection.

## Trust boundary

The discovery did not print or persist Kubernetes env values, Secret names/keys/values, command/args, raw ConfigMap contents, raw workload objects, database rows, dumps, credentials, or connection strings.

Only read-only Kubernetes/system metadata and local executable presence were inspected. No mutation was performed.
