# Project Handoff

This is the compact continuation checkpoint for the Infrastructure Intelligence & Assurance Platform. Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable checkpoint

- repository: `ben-edu/infrastructure-intelligence-assurance`
- stable branch: `main`
- current main HEAD after post-PR30 continuity merge: `987d583ade9003e46e4dbf2e027f62f1a0ab7c0d`
- accepted PR #30 code merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- cluster: `k3s-main`
- runtime user: `infra-assurance`
- oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

Milestones 0–3 are live validated. The current evidence-first Milestone 4 vertical path is accepted and sufficiently complete. Milestone 5 is active.

Known intentional drift remains:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Accepted Milestone 5 foundation — PR #30

- merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- package version: `0.19.0`
- backup assurance artifact: `/var/lib/infra-assurance/evidence/backup-assurance.json`
- backup assurance version: `0.1`
- mutation allowed: false

Accepted live foundation:

```text
217 passed
PVC collection: COMPLETE / CURRENT
PVC assets: 37
same-cycle asset set exact match: true
assets with direct controller reference: 16
protection UNKNOWN: 37
restore verification UNKNOWN: 37
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
```

The 21 PVC assets without a direct controller relation are not classified as orphaned.

Relevant accepted docs:

```text
docs/decisions/0020-derive-kubernetes-pvc-backup-assurance-foundation.md
docs/milestone-5-kubernetes-backup-assurance-foundation.md
docs/reports/2026-08-15-m5-kubernetes-backup-assurance-foundation-live-test-gate.md
```

## Active discovery — authoritative backup source

Branch: `docs/m5-backup-source-discovery`.

First bounded management-host discovery completed without triggering backup/restore operations.

Observed backup/recovery CLI capabilities:

```text
proxmox-backup-client / pvesh / pvesm / vzdump: absent
pgbackrest / wal-g: absent
pg_dump / pg_restore / psql: present
mariadb-backup / mariabackup / mysqldump / mariadb: absent
restic / borg / kopia / rclone / velero: absent
```

Relevant systemd unit names observed:

```text
dpkg-db-backup.service
dpkg-db-backup.timer
pg_basebackup@.service
pg_basebackup@.timer
postgresql.service
postgresql@.service
```

Only `dpkg-db-backup.timer` appeared active/scheduled in the generic timer listing. A `pg_basebackup@` template is capability/declared mechanism evidence only; it does not prove an instantiated backup job, successful backup, retention, or restore verification.

No accepted PBS/Proxmox/database-native backup configuration was found in repository search. No matching SSH host aliases were available on the management host. The first config-variable-name check had an awk syntax error; this affected that subsection only and printed no secret value.

Discovery report:

```text
docs/reports/2026-08-15-m5-authoritative-backup-source-discovery.md
```

## Exact next step — bounded PostgreSQL backup preflight

PostgreSQL is the only source with a concrete local signal worth investigating next, but it is not yet selected as the authoritative source.

Run a second read-only preflight that makes no database connection and performs no backup/restore operation. Determine:

1. whether any `pg_basebackup@` service/timer instances are enabled, active, or scheduled;
2. template unit file paths and safe directive structure;
3. environment/config filenames and variable names only, never values;
4. local PostgreSQL cluster metadata only;
5. presence/metadata of plausible local backup directories without reading backup contents;
6. corrected relevant variable-name discovery for `collector.env` and `/etc/environment`;
7. whether the resulting observation path can authoritatively prove last success/retention/verification/restores without broad credentials.

Do not run `psql`, `pg_basebackup`, `pg_dump`, restore commands, or create/modify schedules or credentials during this preflight.

## Trust invariants

- observation credentials remain separate from future control credentials;
- infrastructure interaction remains read-only;
- collector failure is explicit;
- stale is not current;
- unknown is not absent;
- inference is not fact;
- declared and observed state remain separate;
- specialized systems remain authoritative;
- no passwords, tokens, private keys, raw Kubernetes Secret values, sensitive Terraform state, or complete sensitive connection strings enter evidence/AI context;
- current generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
