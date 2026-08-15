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
- current main HEAD before PR #32 merge: `987d583ade9003e46e4dbf2e027f62f1a0ab7c0d`
- accepted PR #30 code merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- cluster: `k3s-main`
- runtime user: `infra-assurance`
- oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

Milestones 0–3 are live validated. The evidence-first Milestone 4 vertical path is accepted and sufficiently complete. Milestone 5 is active.

Known intentional drift remains:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Accepted Milestone 5 foundation — PR #30

```text
backup_assurance_version: 0.1
PVC assets: 37
protection UNKNOWN: 37
restore verification UNKNOWN: 37
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
```

The 21 PVCs without a direct controller relation are not classified as orphaned.

## Accepted discovery — PR #32 authoritative backup source

- PR: `#32 Milestone 5 authoritative backup source discovery`
- branch: `docs/m5-backup-source-discovery`
- code/runtime mutation: none
- backup/restore operations: none
- credentials created/changed: none
- status: discovery accepted; ready for merge

Discovery report:

```text
docs/reports/2026-08-15-m5-authoritative-backup-source-discovery.md
```

### PostgreSQL

Local PostgreSQL `15/main` is online, but no instantiated `pg_basebackup` schedule, enabled timer, or bounded active archive/backup configuration was observed. PostgreSQL is not selected as the first authoritative source.

### Network/firewall semantics

BM1 uses UFW source-IP restrictions. Similar restrictions may exist for VMs/services. Never map timeout/unreachable evidence to `ABSENT` unless the observation path is known complete. Use `FAILED_TO_REACH / UNKNOWN` where firewall restrictions may explain non-reachability.

### Proxmox endpoint evidence

Both PVE API endpoints are reachable from `mgmt-automation` on TCP/8006 and require authentication.

BM1 TLS certificate observed expired `2025-08-04`; reachability does not imply healthy certificate trust.

BM2 authenticated GET discovery:

```text
PVE version: 9.1.9
node: delfan online
storage: local / type dir
content capability includes backup
retention projection: keep-all=1
configured PBS storage: none
cluster backup jobs: 0
current QEMU guests: 12
```

Operator confirms there is no PBS today.

### BM2 observed recovery-point artifacts

A complete GET of `local` backup content returned 12 `vma.zst` artifacts.

```text
VMID 100: 2; latest 2026-05-08T06:13:59Z
VMID 101: 1; latest 2026-05-08T10:36:12Z
VMID 106: 3; latest 2026-08-14T16:13:14Z
VMID 107: 3; latest 2026-08-14T16:40:35Z
VMID 108: 2; latest 2026-04-15T12:30:02Z
VMID 109: 1; latest 2026-04-13T10:34:52Z
```

Current VMIDs without a local backup artifact in this complete storage scope:

```text
102 103 104 105 110 9000
```

Interpretation boundaries:

- artifact presence is recovery-point evidence;
- artifact presence is not restore verification, integrity verification, RPO/RTO compliance, or proof of a current scheduled protection mechanism;
- `protected=false` is a Proxmox archive retention/protection flag and must never map to platform `UNPROTECTED`;
- zero cluster backup jobs means no current cluster backup job was observed; historical/manual/external creation remains possible;
- BM2 evidence must not be projected onto BM1 or future PBS.

### Existing Proxmox token is rejected for runtime

Effective privileges are broad/admin-like and include control-capable privileges such as:

```text
Datastore.Allocate*
Permissions.Modify
Sys.Console
Sys.Modify
Sys.PowerMgmt
VM.Allocate
VM.Console
VM.PowerMgmt
VM.Snapshot
VM.Snapshot.Rollback
```

The token is `DISCOVERY_ONLY` and must not be wired into runtime. Its local env file is Git-ignored but mode `0644`; TLS verification is disabled. A dedicated least-privilege observer credential will be required before runtime wiring, but current project phases remain read-only and must not provision it yet.

### Mandatory future PBS compatibility

The core Backup and Recovery Assurance model remains source-neutral. Current PVE/local backup and future PBS-native evidence are separate adapters with explicit provenance and the same common evidence dimensions:

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

PBS-specific datastore/namespace/snapshot identities must stay in source-specific evidence/provenance, not core asset semantics.

## Exact next implementation slice — BM2 Proxmox VE backup evidence adapter

Implement the first authoritative backup source adapter against BM2 PVE with these boundaries:

1. HTTP GET only; no mutating API method or subprocess-based control command.
2. Safe projections of PVE identity, current guest VMIDs, storage capability/retention metadata, cluster backup-job summary, and local backup recovery-point metadata.
3. Explicit source observation status and failure semantics; complete empty content scope is different from failed observation.
4. Explicit source/storage/VM provenance; never expose token IDs/secrets or raw sensitive storage configuration.
5. Preserve archive timestamp/count/format/size/protection-flag metadata only as needed; do not persist raw API payloads.
6. Never map PVE archive `protected=false` to platform `UNPROTECTED`.
7. Do not claim restore verification, integrity, RPO/RTO or current scheduled protection from artifact presence alone.
8. Keep adapter source-neutral/future-PBS compatible.
9. Do not wire the current broad discovery token into systemd/runtime.
10. Repository tests and a manual live gate may use the existing token only as a temporary GET-only discovery/test credential; runtime integration remains blocked until a separately approved least-privilege observer identity exists.

Likely implementation branch:

```text
feature/m5-proxmox-ve-backup-evidence
```

Package version should advance from `0.19.0` to `0.20.0` if repository convention remains unchanged.

## Trust invariants

- infrastructure interaction remains read-only;
- observation credentials stay separate from control credentials;
- collector failure is explicit;
- stale is not current;
- unknown is not absent;
- network timeout is not absence unless observation path is complete;
- inference is not fact;
- declared and observed state remain separate;
- specialized systems remain authoritative;
- no passwords, tokens, private keys, raw Kubernetes Secret values, sensitive Terraform state, raw sensitive Proxmox storage configuration, or complete sensitive connection strings enter evidence/AI context;
- current generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
