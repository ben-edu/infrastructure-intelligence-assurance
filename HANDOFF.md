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
- current main HEAD before PR #30 merge: `434079ec90edc0cccd94b4e697f92b615aa87cd1`
- accepted PR #28 code merge: `9b32c7657a648c04081c9bcc4f5112872c2ecd2c`
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

## Active accepted work — PR #30 Milestone 5 Kubernetes backup assurance foundation

- PR: `#30 Milestone 5 Kubernetes backup assurance foundation`
- branch: `feature/m5-kubernetes-backup-assurance-foundation`
- base main: `434079ec90edc0cccd94b4e697f92b615aa87cd1`
- package version: `0.19.0`
- status: repository/live accepted; ready for squash merge
- RBAC change: none
- new infrastructure/backup/database query: none
- new credentials: none
- mutation: none

Purpose: identify Kubernetes PVC stateful assets requiring backup/recovery assurance while representing absent authoritative backup evidence as `UNKNOWN`, never as `UNPROTECTED`.

Accepted artifacts:

```text
/var/lib/infra-assurance/evidence/backup-assurance.json
/var/lib/infra-assurance/evidence/backup-assurance.md
```

Inputs remain local accepted evidence only:

```text
/var/lib/infra-assurance/evidence/kubernetes.json
/var/lib/infra-assurance/evidence/topology.json
```

Accepted contract:

```text
backup_assurance_version: 0.1
scope.asset_type: KUBERNETES_PVC
scope.derived_only: true
scope.authoritative_backup_source_integrated: false
mutation_allowed: false
```

Accepted repository/live evidence:

```text
RBAC changes: none
query / external-source markers: none
217 passed in 1.94s
all runtime stages: status=0/SUCCESS
backup_assurance_foundation: status=0/SUCCESS
PVC collection: COMPLETE / CURRENT
workload/PVC relationship scope: COMPLETE
PVC assets: 37
same-cycle asset set exact match: true
current assets: 37
stale assets: 0
assets with direct controller reference: 16
protection UNKNOWN: 37
restore verification UNKNOWN: 37
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
unknown: AUTHORITATIVE_BACKUP_SOURCE_NOT_INTEGRATED
forbidden projected keys: none
raw URL markers: false
```

Every asset retained exactly eight future authoritative evidence targets:

```text
BACKUP_MECHANISM
LAST_SUCCESSFUL_BACKUP
BACKUP_RETENTION
BACKUP_FAILURE_DOMAIN
BACKUP_INTEGRITY_VERIFICATION
RESTORE_TEST
RPO_TARGET_AND_RESULT
RTO_TARGET_AND_RESULT
```

The 21 PVC assets without a direct Deployment/StatefulSet/DaemonSet controller relation are not classified as orphaned. The current relation model is controller-spec context only and does not cover all Pod-level/generated consumers.

Relevant accepted docs:

```text
docs/decisions/0020-derive-kubernetes-pvc-backup-assurance-foundation.md
docs/milestone-5-kubernetes-backup-assurance-foundation.md
docs/reports/2026-08-15-m5-kubernetes-backup-assurance-foundation-live-test-gate.md
```

## Exact next step after PR #30 merge — authoritative backup-source discovery

Do not choose or implement a PBS, Proxmox, PostgreSQL, MariaDB, or external-target collector by assumption.

Repository search currently provides no accepted configuration proving which authoritative backup source is live, which assets it covers, or what least-privilege observation path already exists.

Run a bounded read-only source-discovery/preflight first. The discovery should determine, without printing secrets or complete sensitive connection strings:

1. which backup/recovery engines are actually present and active;
2. whether PBS/Proxmox VM backup evidence exists;
3. whether PostgreSQL or MariaDB use database-native backup tooling;
4. whether external backup targets are configured;
5. whether an existing least-privilege read-only identity/access path is available;
6. what evidence each source can authoritatively prove: mechanism, last success, retention, failure domain, verification, restore tests, RPO/RTO;
7. what asset identity can be safely joined to the foundation artifact;
8. whether source observation can be performed without changing schedules, jobs, credentials, or infrastructure.

Choose exactly one source for the next implementation slice based on that evidence. Prefer the smallest source that has a clear authoritative contract and safe read-only observation path.

Do not create new broad/admin credentials as part of source discovery. Do not modify backup schedules or trigger backup/restore jobs.

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
