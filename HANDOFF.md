# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and live-test report relevant to the active slice.
6. Prefer repository/live evidence over chat reconstruction.

## Stable checkpoint

- repository: `ben-edu/infrastructure-intelligence-assurance`
- current `main` ref before PR #43: `cf6fabc20e962e8b37a48c1962a9865aa66fe394`
- accepted PR #41 implementation merge: `d0c9d28711aecb19150988dbf53003a98aa91ff8`
- `cf6fabc` is the post-PR41 handoff refresh commit
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- Kubernetes cluster: `k3s-main`
- PVE collectors remain manual-only; no systemd credential wiring

Milestones 0–3 are live validated. Milestone 4 evidence-first path is accepted and sufficiently complete. Milestone 5 is active.

## Stable Milestone 5 evidence

Kubernetes PVC foundation:

```text
backup_assurance_version: 0.1
PVC assets: 37
protection UNKNOWN: 37
unprotected_claims: 0
```

Accepted BM2 PVE recovery-point source:

```text
proxmox_ve_backup_evidence_version: 0.1
source: pve-bm2
current guests: 12
recovery points: 12
with recovery points: 100,101,106,107,108,109
no recovery point in complete local scope: 102,103,104,105,110,9000
PBS backend: false
runtime credential approved: false
```

Accepted PVE task-result evidence:

```text
pve_backup_task_results_version: 0.1
rows returned: 22
successful task results: 22
strict recovery-point/task matches: 9
unmatched retained recovery points: 3
historical completeness: NOT_ESTABLISHED
```

Accepted VM Backup Assurance v0.2:

```text
package: 0.23.0
assets: 12
mode: STRICT_CORRELATION_ONLY
last_successful_backup OBSERVED: 6
last_successful_backup UNKNOWN: 6
protection UNKNOWN: 12
restore/integrity/failure-domain/RPO/RTO: UNKNOWN
unprotected_claims: 0
```

Observed VMIDs for `LAST_SUCCESSFUL_BACKUP`:

```text
100,101,106,107,108,109
```

Unknown VMIDs:

```text
102,103,104,105,110,9000
```

## Completed bounded VM primary-storage preflight

The manual read-only BM2 preflight requested by the previous handoff has now passed.

Current safe result:

```text
VMIDs: 100,101,102,103,104,105,106,107,108,109,110,9000
backup storage ID: local
all 12 VM observations: COMPLETE
all 12 resolved primary storage IDs: local
direct/unresolved disk count: 0
SAME_PVE_STORAGE_ID_AS_BACKUP: 12
UNKNOWN: 0
FAILED_TO_OBSERVE: 0
storage local type: dir
storage local shared: NOT_EXPLICITLY_RETURNED
storage local node restrictions: none explicitly returned
```

This proves a bounded PVE storage-ID relationship only. It does not prove same physical disk/hardware failure domain or failure-domain separation. `BACKUP_FAILURE_DOMAIN` remains `UNKNOWN`.

No raw VM config, raw disk value, volid, path, serial, cloud-init, network/MAC/IP value, credential, or snippet was persisted. Only HTTP GET requests were used and no infrastructure mutation occurred.

## Active slice — PR #43

- PR: `#43 Milestone 5 add bounded PVE VM storage relationship evidence`
- branch: `agent/m5-pve-vm-storage-relationship`
- base: current `main` checkpoint `cf6fabc20e962e8b37a48c1962a9865aa66fe394`
- package: `0.24.0`
- source artifact: `pve_vm_storage_relationship_version=0.1`
- ADR: `docs/decisions/0025-observe-bounded-pve-vm-storage-relationships.md`
- milestone doc: `docs/milestone-5-pve-vm-storage-relationship.md`
- live gate: `docs/reports/2026-08-16-m5-pve-vm-storage-relationship-live-test-gate.md`
- PR status: draft; do not merge before full repository and live acceptance gates pass

The new collector records only bounded storage relationships:

```text
SAME_PVE_STORAGE_ID_AS_BACKUP
DIFFERENT_PVE_STORAGE_ID_FROM_BACKUP
UNKNOWN
FAILED_TO_OBSERVE
```

It does not modify VM Backup Assurance and does not promote `BACKUP_FAILURE_DOMAIN`.

Focused fixture testing of the proposed logic passed before publication. The authoritative full-repository gate and live collector gate are still pending.

## Exact next step — PR #43 repository + live gate

On `mgmt-automation`, update the checkout and switch to the active branch, then run the full repository tests and the manual collector:

```bash
set -euo pipefail

cd ~/projects/infrastructure-intelligence-assurance
git fetch origin
git switch agent/m5-pve-vm-storage-relationship
git pull --ff-only origin agent/m5-pve-vm-storage-relationship

python3 -m pytest -q

ENV_FILE="/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env"
OUT="/tmp/pve-vm-storage-relationship-v0.1.json"
SUMMARY="/tmp/pve-vm-storage-relationship-v0.1.md"

python3 -m infra_assurance.proxmox_ve_vm_storage_relationship \
  --credential-env-file "$ENV_FILE" \
  --source-id pve-bm2 \
  --node delfan \
  --backup-storage-id local \
  --vmids 100,101,102,103,104,105,106,107,108,109,110,9000 \
  --out "$OUT" \
  --summary-out "$SUMMARY" \
  --allow-discovery-credential \
  --allow-insecure-tls-discovery

cat "$SUMMARY"
```

Expected only if live state remains equivalent to the accepted preflight:

```text
target_vms: 12
same_pve_storage_id_as_backup: 12
different_pve_storage_id_from_backup: 0
unknown: 0
failed_to_observe: 0
direct_or_unresolved_disks: 0
local storage_type: dir
local shared_status: NOT_EXPLICITLY_RETURNED
local node_restrictions_status: NOT_EXPLICITLY_RETURNED
```

If live evidence differs, preserve the live result and investigate; do not force it to match the preflight.

After the gate, update the live-test report and ADR status only if acceptance actually passes. Keep PR #43 unmerged until then.

## PVE credential/runtime boundary

The existing BM2 token remains discovery-only: broad/admin-like, env file mode `0644`, TLS verification false. Runtime PVE collection remains blocked until a separate least-privilege observer identity and trusted TLS path are accepted.

There is no PBS today. Future PBS compatibility remains mandatory through separate source adapters and common assurance dimensions.

## Milestone 5 gaps still open

```text
PostgreSQL
MariaDB
PVC assurance beyond foundation
PBS (future)
external backup targets
failure-domain assurance beyond storage-ID relationship
retention effectiveness
RPO/RTO
restore tests
```

## Trust invariants

- infrastructure interaction remains read-only;
- source artifacts and derived assurance remain separate;
- source-scoped negative evidence is not universal absence;
- recovery-point presence is not task-result success;
- task-result success is not restore verification;
- observation credentials remain separate from control credentials;
- stale/current/unknown semantics remain explicit;
- network timeout is not absence unless observation scope is known complete;
- no secrets, raw sensitive config/state, raw task logs, or raw VM config enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
