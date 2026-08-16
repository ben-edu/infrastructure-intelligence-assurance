# Project Handoff

This is the compact continuation checkpoint for the Infrastructure Intelligence & Assurance Platform. Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable checkpoint

- repository: `ben-edu/infrastructure-intelligence-assurance`
- stable branch: `main`
- main before PR #41 merge: `7a86faffa33c4cbe6d8fc46695f6d4c032e95d5b`
- accepted PR #30 foundation merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- accepted PR #32 discovery merge: `b0f139a531536531cff2a76bf2243c0cc7ca1770`
- accepted PR #33 PVE recovery-point adapter merge: `58dca4289a3c302ef9098564da59b7d312aae71e`
- accepted PR #35 VM assurance merge: `59924eb93cbed0ecfef6c2dc6ffbd98af031c547`
- accepted PR #38 PVE task-result merge: `f33506ba59281dac31485616c439126d7b41c30d`
- post-PR38 Handoff merge: `7a86faffa33c4cbe6d8fc46695f6d4c032e95d5b`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- PVE collectors remain manual-only; no systemd credential wiring

Milestones 0–3 are live validated. Milestone 4 evidence-first vertical path is accepted and sufficiently complete. Milestone 5 is active.

## Stable Milestone 5 evidence

Kubernetes PVC foundation remains separate:

```text
backup_assurance_version: 0.1
PVC assets: 37
protection UNKNOWN: 37
unprotected_claims: 0
```

Accepted BM2 PVE recovery-point source from PR #33:

```text
proxmox_ve_backup_evidence_version: 0.1
source: pve-bm2
current guests: 12
recovery points: 12
VMIDs with recovery points: 100,101,106,107,108,109
VMIDs with no recovery point in complete local scope: 102,103,104,105,110,9000
PBS backend: false
credential_runtime_approved: false
```

Accepted VM Backup Assurance v0.1 from PR #35:

```text
VM assets: 12
recovery-point observed: 6
complete selected-scope negative: 6
protection unknown: 12
restore/integrity/RPO/RTO unknown: 12
unprotected claims: 0
Kubernetes PVC assets modified: 0
```

Accepted PVE task-result evidence from PR #38:

```text
pve_backup_task_results_version: 0.1
source: pve-bm2
rows returned: 22
successful task results: 22
strict recovery-point/task matches: 9
unmatched retained recovery points: 3
historical completeness: NOT_ESTABLISHED
runtime credential approved: false
```

Strict correlation contract is same VMID + successful VZDUMP + recovery-point/task-start delta <=2 seconds. Current accepted deltas are 0 or 1 second.

## Accepted PR #41 — VM LAST_SUCCESSFUL_BACKUP integration

- PR: `#41 Milestone 5 integrate last successful VM backup evidence`
- branch: `feature/m5-vm-last-successful-backup`
- package: `0.23.0`
- output: `vm_backup_assurance_version=0.2`
- integration version: `0.1`
- mode: `STRICT_CORRELATION_ONLY`
- repository/manual-derived gate: Accepted on 2026-08-16 after focused retry
- network/Proxmox query: none
- credential access: none
- RBAC change: none
- systemd change: none
- infrastructure mutation: none
- Kubernetes PVC mutation: none

The first PR #41 gate was rejected because the integration schema expected an incorrect task-result ID shape. Accepted PR #38 source IDs use:

```text
^pve-backup-task:[a-f0-9]{24}$
```

The schema, fixtures, and regression tests were corrected to reuse that authoritative contract. The focused retry passed:

```text
262 passed in 1.32s
task ID contract alignment: PASS
both source artifacts unchanged: true
output schema: PASS
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
strict success correlations consumed: 9
unmatched historical recovery points: 3
unprotected_claims: 0
kubernetes_pvc_assets_modified: 0
sensitive/raw projection: none
```

Observed VMIDs:

```text
100, 101, 106, 107, 108, 109
```

Unknown VMIDs:

```text
102, 103, 104, 105, 110, 9000
```

Current last successful backup timestamps use the successful task `end_time`, not archive creation time.

Every VM still preserves:

```text
protection_status: UNKNOWN
integrity_verification_status: UNKNOWN
restore_verification_status: UNKNOWN
failure_domain_status: UNKNOWN
scheduled_protection_status: UNKNOWN
rpo_status: UNKNOWN
rto_status: RTO_UNKNOWN
```

Missing historical task evidence remains a history limitation, not backup failure.

## PVE credential/runtime boundary

The existing BM2 token remains discovery-only: broad/admin-like, env file mode `0644`, TLS verification false. Runtime PVE collection remains blocked until a separate least-privilege observer identity and trusted TLS path are accepted.

Operator confirms there is no PBS today. Future PBS compatibility remains mandatory through separate source adapters with explicit provenance and common assurance dimensions.

## Exact next step — bounded VM primary-storage failure-domain preflight

The next smallest useful M5 gap is `BACKUP_FAILURE_DOMAIN` for the current PVE VM domain.

Current backup recovery points are on `pve-bm2 / delfan / local`, a PVE-local backup storage scope. This does not by itself prove whether the backup copy is in the same failure domain as each VM's primary disks.

Run a manual read-only preflight against BM2 using the existing discovery-only credential. Do not persist or print raw VM config.

The preflight should determine only safe primary-storage identity for current accepted VMIDs:

```text
100,101,102,103,104,105,106,107,108,109,110,9000
```

Required safe projection per VM:

```text
vmid
node
primary storage IDs referenced by VM disk devices
whether each storage is shared or node-local, when authoritative storage metadata proves it
```

Do not project:

```text
raw disk strings
volid
file paths
serial numbers
cloud-init content
network config
MAC addresses
IP addresses
credentials
snippets
raw VM config
```

Trust rules:

1. same node alone is not enough to classify failure-domain separation;
2. storage type/name alone must not be overinterpreted without authoritative shared/local metadata;
3. if VM primary disks and backup storage are authoritatively node-local on the same PVE node, record a bounded same-node failure-domain candidate only; do not promote VM assurance until a separate source artifact is accepted;
4. if evidence is incomplete or permission-limited, result is UNKNOWN/FAILED_TO_OBSERVE, not separated or absent;
5. no VM config, storage, backup, snapshot, schedule, ACL, token, or infrastructure mutation;
6. do not use raw broad-token data in runtime artifacts; this remains manual discovery only.

Only if the preflight proves a safe authoritative join should a new source artifact/ADR be implemented.

## Milestone 5 roadmap coverage still open

```text
PostgreSQL
MariaDB
PVC assurance beyond foundation
PBS (future; not present today)
external backup targets
failure-domain evidence
retention effectiveness
RPO/RTO
restore tests
```

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance remain separate evidence layers;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- historical task incompleteness is not backup failure;
- observation credentials remain separate from control credentials;
- stale/current/unknown semantics remain explicit;
- network timeout is not absence unless observation scope is known complete;
- no secrets, tokens, private keys, raw Kubernetes Secret values, Terraform state, raw sensitive Proxmox configuration, complete sensitive connection strings, raw task logs, or raw VM config enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
