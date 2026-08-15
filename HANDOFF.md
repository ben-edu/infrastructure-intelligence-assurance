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
- current main HEAD after PR #32 discovery merge: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
- accepted PR #30 foundation merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- accepted PR #32 discovery merge: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- existing infra-assurance runtime remains Kubernetes/observability-only; Proxmox is not systemd-wired

Milestones 0–3 are live validated. Milestone 4 evidence-first vertical path is accepted and sufficiently complete. Milestone 5 is active.

Known intentional Kubernetes drift remains:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Accepted Milestone 5 foundation

PR #30 established:

```text
backup_assurance_version: 0.1
PVC assets: 37
protection UNKNOWN: 37
restore verification UNKNOWN: 37
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
```

## Accepted authoritative-source discovery

PR #32 selected BM2 Proxmox VE as the first real VM recovery-point source.

### PostgreSQL

Local PostgreSQL `15/main` is online, but no instantiated `pg_basebackup` schedule, enabled timer, or bounded active archive/backup configuration was observed. It is not selected as the first backup source.

### Network/firewall semantics

BM1 uses UFW source-IP restrictions and similar restrictions may exist on VMs/services. Timeout/unreachable evidence is `FAILED_TO_REACH / UNKNOWN` unless the observation path is known complete. Network timeout is not absence.

### Proxmox discovery facts

Both PVE APIs are reachable on TCP/8006 and authentication-required.

BM1 TLS certificate was observed expired `2025-08-04`; reachability does not imply healthy TLS trust.

BM2 current facts from bounded authenticated GET discovery:

```text
PVE: 9.1.9
node: delfan online
storage: local / dir / backup-enabled
retention projection: keep-all=1
configured PBS storage: none
cluster backup jobs: 0
current QEMU guests: 12
local recovery-point artifacts: 12
VMIDs with local recovery points: 100,101,106,107,108,109
current VMIDs without local artifact in complete local scope: 102,103,104,105,110,9000
```

Operator confirms there is no PBS today but future PBS compatibility is mandatory.

Artifact presence is recovery-point evidence only. It is not restore verification, integrity verification, current scheduled protection, application consistency, RPO compliance, or RTO compliance.

PVE archive `protected=false` is a source-native retention/deletion-protection flag and must never map to platform `UNPROTECTED`.

### Existing BM2 credential is discovery-only

Current env file:

```text
/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env
Git ignored: yes
mode: 0644
TLS verification: false
```

Effective token privileges are broad/admin-like and include control capabilities such as `Permissions.Modify`, `Sys.Modify`, `Sys.PowerMgmt`, `VM.PowerMgmt`, `VM.Snapshot`, and datastore allocation privileges.

The token is rejected for platform runtime. Current project phases remain read-only and must not provision a replacement credential yet.

## Active implementation — PR #33 Proxmox VE backup evidence adapter

- PR: `#33 Milestone 5 Proxmox VE backup evidence adapter`
- branch: `feature/m5-proxmox-ve-backup-evidence`
- base main: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
- package: `0.20.0`
- artifact version: `proxmox_ve_backup_evidence_version=0.1`
- status: Draft; repository/live gate pending
- RBAC change: none
- systemd change: none
- credential provisioning: none
- infrastructure mutation: none

Relevant files:

```text
src/infra_assurance/proxmox_ve_backup_evidence.py
schemas/proxmox-ve-backup-evidence.schema.json
tests/test_proxmox_ve_backup_evidence.py
tests/test_proxmox_ve_backup_evidence_wiring.py
docs/decisions/0021-observe-proxmox-ve-recovery-points-as-source-evidence.md
docs/milestone-5-proxmox-ve-backup-evidence.md
docs/reports/2026-08-15-m5-proxmox-ve-backup-evidence-live-test-gate.md
```

### Adapter contract

HTTP GET only:

```text
/api2/json/version
/api2/json/nodes
/api2/json/cluster/resources?type=vm
/api2/json/storage
/api2/json/cluster/backup
/api2/json/nodes/<node>/storage/<selected-storage>/content?content=backup
```

Persist only bounded safe projections. Do not persist raw `volid`, raw API payload, raw endpoint URL, guest names, token material, storage server/path/username, fingerprints, encryption-key references, or Terraform state/tfvars.

Source statuses:

```text
COMPLETE
PARTIAL
FAILED_TO_OBSERVE
```

Selected-storage guest coverage statuses:

```text
RECOVERY_POINT_OBSERVED
NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE
UNKNOWN
```

Complete empty content scope is not the same as failed observation.

Normal collector execution rejects group/world-readable credential files and disabled TLS verification. Manual live acceptance may use explicit discovery override flags against the current credential, but no permanent runtime wiring is allowed.

### Mandatory future PBS compatibility

Core assurance semantics remain source-neutral. Current PVE-local evidence and future PBS-native evidence are separate source adapters with explicit provenance and common assurance dimensions:

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

PBS datastore/namespace/snapshot identifiers belong in PBS-specific evidence, not common asset identity.

## Exact next step

Run PR #33 repository tests and the manual BM2 live gate.

Acceptance must prove:

1. full pytest passes;
2. adapter is GET-only with no Proxmox control CLI/client;
3. existing systemd unit contains no Proxmox/token wiring;
4. source artifact validates against schema;
5. source status is COMPLETE for the current bounded BM2 scope;
6. runtime credential approval remains false and discovery override is explicit;
7. current guest/storage/recovery-point facts are safely projected;
8. every current guest has one selected-storage coverage record;
9. archive `protected` appears only as `archive_protection_flag` and never platform PROTECTED/UNPROTECTED;
10. failed observation stays UNKNOWN rather than zero/absent;
11. no token, raw URL, raw volid, guest name, storage server/path or other sensitive source field enters output;
12. no backup, restore, snapshot, prune, verify, GC, schedule, ACL, guest, or credential mutation occurs.

After live PASS, update ADR/report/HANDOFF, squash-merge PR #33, then choose the smallest derived integration slice. Do not wire runtime until a dedicated least-privilege Proxmox observer identity and trusted TLS path are separately accepted.

## Trust invariants

- infrastructure interaction remains read-only;
- observation credentials remain separate from control credentials;
- collector failure is explicit;
- stale is not current;
- unknown is not absent;
- network timeout is not absence unless the observation path is complete;
- inference is not fact;
- declared and observed state remain separate;
- specialized systems remain authoritative;
- no passwords, tokens, private keys, raw Kubernetes Secret values, sensitive Terraform state, raw sensitive Proxmox configuration, or complete sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
