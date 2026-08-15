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
- current main HEAD before PR #33 merge: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
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

## Accepted source discovery — PR #32

PR #32 selected BM2 Proxmox VE as the first real VM recovery-point source.

PostgreSQL `15/main` is online on `mgmt-automation`, but no instantiated `pg_basebackup` schedule, enabled timer, or bounded active archive/backup configuration was observed. It was not selected as the first source.

BM1 uses UFW source-IP restrictions and similar restrictions may exist on VMs/services. Timeout/unreachable evidence remains `FAILED_TO_REACH / UNKNOWN` unless the observation path is known complete.

BM1 TLS certificate was observed expired `2025-08-04`; reachability does not imply healthy TLS trust.

Operator confirms there is no PBS today, but future PBS compatibility is mandatory.

## Accepted implementation — PR #33 Proxmox VE backup evidence adapter

- PR: `#33 Milestone 5 Proxmox VE backup evidence adapter`
- branch: `feature/m5-proxmox-ve-backup-evidence`
- base main: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
- package: `0.20.0`
- artifact version: `proxmox_ve_backup_evidence_version=0.1`
- status: repository/live accepted; ready for squash merge
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

### Accepted adapter contract

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

Normal collector execution rejects group/world-readable credential files and disabled TLS verification. Manual live acceptance used explicit discovery override flags against the current credential. No permanent runtime wiring exists.

`credential_runtime_approved` remains `false`; this adapter never auto-approves a credential based only on file mode or TLS settings.

### Accepted repository/live evidence

```text
228 passed in 1.34s
source status: COMPLETE
mutation_allowed: false
credential_runtime_approved: false
credential_file_mode_secure: false
TLS verification: false
discovery override used: true
all bounded GET observations: COMPLETE / HTTP 200
PVE: 9.1.9 / release 9.1
node: delfan / ONLINE
storage: local / dir / backup-enabled
retention projection: keep-all=1
pbs backend: false
cluster backup jobs: 0
current guests: 12
recovery points: 12
VMs with selected-scope recovery point: 6
VMs without selected-scope recovery point in complete scope: 6
selected-scope UNKNOWN: 0
forbidden projected keys: none
raw URL markers: false
credential material projection: none
```

Current VMIDs with recovery points:

```text
100,101,106,107,108,109
```

Current VMIDs with no recovery point observed in the complete `delfan/local` scope:

```text
102,103,104,105,110,9000
```

Latest observed recovery points:

```text
100 -> 2026-05-08T06:13:59Z
101 -> 2026-05-08T10:36:12Z
106 -> 2026-08-14T16:13:14Z
107 -> 2026-08-14T16:40:35Z
108 -> 2026-04-15T12:30:02Z
109 -> 2026-04-13T10:34:52Z
```

Artifact unknowns remain:

```text
RESTORE_VERIFICATION_NOT_OBSERVED
INTEGRITY_VERIFICATION_NOT_OBSERVED
RPO_RTO_NOT_OBSERVED
SCHEDULED_PROTECTION_NOT_INFERRED
```

No platform `protection_status` field is emitted.

PVE archive `protected=false` is a source-native retention/deletion-protection flag and must never map to platform `UNPROTECTED`.

A complete selected storage scope with no recovery point is a valid negative fact only for that exact source/node/storage scope. It is not proof that a VM has no backup in every possible source.

### Existing BM2 credential remains discovery-only

Current env file:

```text
/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env
Git ignored: yes
mode: 0644
TLS verification: false
```

Effective privileges are broad/admin-like and include control capabilities such as `Permissions.Modify`, `Sys.Modify`, `Sys.PowerMgmt`, `VM.PowerMgmt`, `VM.Snapshot`, and datastore allocation privileges.

The token is rejected for runtime. Current project phases remain read-only and must not provision a replacement credential unless a later explicitly approved access-control step allows it.

## Mandatory future PBS compatibility

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

## Exact next step after PR #33 merge — derived PVE assurance integration

Build the smallest derived-only integration slice. It must consume accepted local artifacts only and perform no Proxmox query.

The first integration should model **VM backup assurance separately from Kubernetes PVC assurance**; do not force Proxmox VMIDs into Kubernetes PVC identity.

Required behavior:

1. consume accepted `proxmox-ve-backup-evidence.json` as a source artifact;
2. add VM assets/assurance records with source-neutral fields and explicit PVE provenance;
3. `RECOVERY_POINT_OBSERVED` may establish that a backup mechanism/recovery point is observed for that selected source scope, but must not establish restore/integrity/RPO/RTO compliance;
4. `NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE` must remain a scoped negative observation, not automatically universal `UNPROTECTED` because other sources may exist or be added later;
5. `UNKNOWN`/failed PVE observations must remain unknown;
6. retain source-specific storage/node/VMID context behind common assurance semantics;
7. do not interpret PVE archive `protected=false` as assurance failure;
8. retain PBS-ready adapter separation;
9. no query, systemd change, RBAC change, credential wiring, or infrastructure mutation;
10. do not change the accepted 37 Kubernetes PVC assurance records as a side effect unless the slice has explicit evidence joining a PVC to a VM, which is not currently established.

Runtime PVE collection remains blocked until a dedicated least-privilege Proxmox observer identity and trusted TLS path are separately accepted.

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
- source-scoped negative evidence is not universal absence;
- no passwords, tokens, private keys, raw Kubernetes Secret values, sensitive Terraform state, raw sensitive Proxmox configuration, or complete sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
