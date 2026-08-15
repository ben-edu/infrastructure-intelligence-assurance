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
- current main HEAD after PR #35 merge: `59924eb93cbed0ecfef6c2dc6ffbd98af031c547`
- accepted PR #30 foundation merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- accepted PR #32 discovery merge: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
- accepted PR #33 PVE source adapter merge: `58dca4289a3c302ef9098564da59b7d312aae71e`
- accepted PR #35 VM assurance merge: `59924eb93cbed0ecfef6c2dc6ffbd98af031c547`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- PVE source collector remains manual-only; no systemd credential wiring

Milestones 0–3 are live validated. Milestone 4 evidence-first vertical path is accepted and sufficiently complete. Milestone 5 is active.

## Stable Milestone 5 evidence

Kubernetes PVC foundation remains separate:

```text
backup_assurance_version: 0.1
PVC assets: 37
protection UNKNOWN: 37
unprotected_claims: 0
```

Accepted BM2 PVE source evidence from PR #33:

```text
package: 0.20.0
proxmox_ve_backup_evidence_version: 0.1
source: pve-bm2
PVE: 9.1.9
node: delfan / ONLINE
source status: COMPLETE
current guests: 12
storage: local / dir / backup-enabled
retention projection: keep-all=1
PBS backend: false
cluster backup jobs: 0
recovery points: 12
VMIDs with recovery points: 100,101,106,107,108,109
VMIDs with no recovery point in complete local scope: 102,103,104,105,110,9000
credential_runtime_approved: false
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

PVE archive `protected=false` is source-native and must never map to platform `UNPROTECTED`.

The existing BM2 token is broad/admin-like, env file mode `0644`, TLS verification false, and remains discovery-only. Runtime PVE collection is blocked until a separate least-privilege identity and trusted TLS path are accepted.

Operator confirms there is no PBS today. Future PBS compatibility is mandatory through a separate source adapter with explicit provenance and no redesign of common assurance semantics.

## Accepted implementation — PR #35 VM Backup Assurance integration

- merge: `59924eb93cbed0ecfef6c2dc6ffbd98af031c547`
- package: `0.21.0`
- artifact: `vm_backup_assurance_version=0.1`
- query/network client: none
- Proxmox credential access: none
- RBAC change: none
- systemd change: none
- infrastructure mutation: none
- Kubernetes PVC assurance mutation: none

Relevant files:

```text
src/infra_assurance/vm_backup_assurance.py
schemas/vm-backup-assurance.schema.json
tests/test_vm_backup_assurance.py
tests/test_vm_backup_assurance_wiring.py
docs/decisions/0022-derive-vm-backup-assurance-from-source-evidence.md
docs/milestone-5-vm-backup-assurance-integration.md
docs/reports/2026-08-15-m5-vm-backup-assurance-integration-live-test-gate.md
```

Accepted repository/live gate:

```text
240 passed in 1.25s
source artifact unchanged during derivation: true
source status: COMPLETE
source freshness: UNKNOWN
VM assets: 12
recovery-point observed: 6
complete selected-scope negative: 6
recovery-point unknown: 0
backup mechanism observed: 6
retention configuration observed: 12
protection unknown: 12
restore verification unknown: 12
integrity verification unknown: 12
RPO unknown: 12
RTO unknown: 12
unprotected claims: 0
Kubernetes PVC assets modified: 0
forbidden projected keys: none
raw URL markers: false
```

Observed-recovery-point semantics:

```text
recovery_point_status: OBSERVED
backup_mechanism_status: OBSERVED
backup_mechanism.type: PROXMOX_VE_STORAGE_ARCHIVE
protection_status: UNKNOWN
last_successful_backup_status: UNKNOWN
integrity_verification_status: UNKNOWN
restore_verification_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

Complete selected-source negative semantics:

```text
recovery_point_status: NOT_OBSERVED_IN_COMPLETE_SELECTED_SCOPE
protection_status: UNKNOWN
```

No VMID-to-Kubernetes-PVC relation is inferred.

Every VM retains the common eight evidence dimensions:

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

Archive presence does not satisfy `LAST_SUCCESSFUL_BACKUP`; task-result evidence is still missing.

## Exact next step — bounded PVE backup task-result preflight

Reduce a real remaining assurance unknown rather than adding more recovery-point inventory.

Run a bounded manual read-only preflight against BM2 PVE task history to determine whether authoritative completed `vzdump`/backup task-result metadata is available and safely correlatable to current VMIDs/recovery-point times.

The preflight must:

1. use HTTP GET only;
2. use the existing broad token only as a temporary manual discovery credential, never runtime;
3. make no backup, restore, snapshot, prune, verify, GC, schedule, ACL, credential, or guest mutation;
4. project only safe task metadata needed to assess feasibility, such as task type, node, VMID when safely present, start/end time, and normalized success/failure status;
5. not persist raw task logs, command lines, user/token identity, raw error text, URLs, credentials, or complete UPIDs in platform evidence;
6. distinguish task-history observation failure from no matching task;
7. determine whether a successful task can support `LAST_SUCCESSFUL_BACKUP` without claiming restore verification;
8. not infer a task/archive join unless identity/time evidence is sufficient;
9. preserve future PBS adapter separation;
10. stop at discovery if API scope or task semantics are insufficiently clear.

If preflight proves a safe authoritative task-result path, implement it as a separate source-evidence slice before integrating it into VM assurance.

Do not wire PVE runtime collection until a dedicated least-privilege observer identity and trusted TLS path are separately accepted.

## Milestone 5 roadmap coverage still open

Project roadmap still requires broader evidence for:

```text
PostgreSQL
MariaDB
PVCs
VM backups
PBS (future; not present today)
external backup targets
retention
RPO/RTO
restore tests
```

Current work covers PVC stateful-asset foundation plus PVE-local VM recovery-point evidence and derived VM assurance. It does not close the full milestone.

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance are separate evidence layers;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not restore verification or task-result success;
- observation credentials remain separate from control credentials;
- stale/current/unknown semantics remain explicit;
- network timeout is not absence unless observation scope is known complete;
- no secrets, tokens, private keys, raw Kubernetes Secret values, Terraform state, raw sensitive Proxmox configuration, complete sensitive connection strings, or raw task logs enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
