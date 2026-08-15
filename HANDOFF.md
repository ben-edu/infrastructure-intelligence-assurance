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

## Active discovery — PR #32 authoritative backup source

- PR: `#32 Milestone 5 authoritative backup source discovery`
- branch: `docs/m5-backup-source-discovery`
- code/runtime mutation: none
- backup/restore operations: none
- credentials created/changed: none

Discovery report:

```text
docs/reports/2026-08-15-m5-authoritative-backup-source-discovery.md
```

### Management-host generic discovery

No PBS/Proxmox/Velero/restic/borg/kopia clients were observed on `mgmt-automation`.

Observed PostgreSQL tools:

```text
pg_dump / pg_restore / psql: present
pgbackrest / wal-g: absent
```

### PostgreSQL metadata-only discovery

Current local PostgreSQL runtime:

```text
cluster: 15/main
status: online
systemd: postgresql@15-main.service active/running
```

`pg_basebackup@.service/.timer` templates exist and describe a weekly `pg_backupcluster` mechanism, but no instantiated service/timer, enabled symlink, or scheduled `pg_basebackup` timer was observed.

No active backup/replication-related PostgreSQL config keys were observed in the bounded scan. No relevant backup/PBS/Proxmox/database environment variable names were observed. `/var/backups` exists but contents were not read and directory existence is not backup evidence.

Conclusion: PostgreSQL on this host is **not selected as an authoritative backup source**. Current evidence proves capability/template presence, not an active backup mechanism or successful recovery evidence.

### Historical Proxmox/PBS context

Historical infrastructure material records two Proxmox VE bare-metal environments and documents PBS as the selected infrastructure backup approach. This is discovery context only, not current live evidence.

Do not infer that PBS is currently configured, reachable, scheduled, healthy, or protecting any VM until live verification succeeds.

## Exact next step — bounded Proxmox/PBS preflight

Verify the current Proxmox/PBS path read-only before designing a collector.

The preflight must:

1. verify current Proxmox VE endpoint reachability and endpoint identity safely;
2. inspect only existing local metadata for Proxmox observer/API credential names or file paths, never secret values;
3. determine whether an existing least-privilege read-only API path exists;
4. distinguish Proxmox VE reachability from PBS presence;
5. only if a safe authenticated read path already exists, inspect whether PBS-backed storage/backup jobs are configured using bounded safe projections;
6. never print tokens, passwords, private keys, full sensitive connection strings, or raw config containing them;
7. do not run backup, restore, prune, verify, garbage collection, snapshot, or schedule changes;
8. if no safe read identity exists, stop at UNKNOWN and design a dedicated observer identity separately rather than reusing admin access.

Do not implement a PBS collector until this preflight proves a real source and safe observation contract.

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
