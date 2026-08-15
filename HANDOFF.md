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
- current main HEAD after post-PR33 continuity: `0a45be9c3fea71b1c8b009c0a4eae9816e0cb6be`
- accepted PR #30 foundation merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- accepted PR #32 discovery merge: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
- accepted PR #33 PVE source adapter merge: `58dca4289a3c302ef9098564da59b7d312aae71e`
- post-PR33 Handoff merge: `0a45be9c3fea71b1c8b009c0a4eae9816e0cb6be`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- Proxmox source collector remains manual-only; no systemd credential wiring

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

## Active implementation — PR #35 VM Backup Assurance integration

- PR: `#35 Milestone 5 derive VM backup assurance from PVE evidence`
- branch: `feature/m5-vm-backup-assurance-integration`
- base main: `0a45be9c3fea71b1c8b009c0a4eae9816e0cb6be`
- package: `0.21.0`
- output contract: `vm_backup_assurance_version=0.1`
- status: Draft; repository/manual-derived gate pending
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

### VM assurance contract

VM assets are a separate domain:

```text
asset_type: VIRTUAL_MACHINE
scope.derived_only: true
scope.source_neutral_assurance: true
scope.kubernetes_pvc_assurance_modified: false
mutation_allowed: false
```

No VMID-to-Kubernetes-PVC relation is inferred.

Observed recovery-point semantics:

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

Incomplete/failed source semantics:

```text
recovery_point_status: UNKNOWN
protection_status: UNKNOWN
```

Every VM retains the common eight dimensions:

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

Dimension state is `OBSERVED`, `PARTIAL`, or `REQUIRED`. A recovery point may satisfy `BACKUP_MECHANISM`; retention configuration may partially satisfy `BACKUP_RETENTION`; archive presence does not satisfy `LAST_SUCCESSFUL_BACKUP` task-result semantics.

Source artifact v0.1 has no expiry/TTL contract, so derived source freshness remains `UNKNOWN`.

### Acceptance boundary

Use the already generated PR #33 source artifact:

```text
/tmp/proxmox-ve-backup-evidence.json
```

Do not rerun PVE collection in the PR #35 gate. If the file is absent, stop rather than silently making a new Proxmox request.

Acceptance must prove:

1. full pytest passes;
2. package `0.21.0` and CLI `iia-vm-backup-assurance` are present;
3. integration has no network/query/control markers;
4. RBAC/systemd unchanged;
5. source artifact validates as accepted input and output validates against VM assurance schema;
6. current VM asset set exactly matches current guest VMIDs from the supplied source artifact;
7. source `RECOVERY_POINT_OBSERVED` maps to mechanism/recovery-point evidence only while protection stays UNKNOWN;
8. complete selected-scope negative maps to scoped negative only while protection stays UNKNOWN;
9. source UNKNOWN stays UNKNOWN;
10. all VM restore/integrity/RPO/RTO remain unknown;
11. `unprotected_claims=0` and `kubernetes_pvc_assets_modified=0`;
12. no unsafe source fields or credential material enter output;
13. no PVE request or infrastructure mutation occurs.

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance are separate evidence layers;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not restore verification or task-result success;
- observation credentials remain separate from control credentials;
- stale/current/unknown semantics remain explicit;
- no secrets, tokens, private keys, raw Kubernetes Secret values, Terraform state, raw sensitive Proxmox configuration, or complete sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
