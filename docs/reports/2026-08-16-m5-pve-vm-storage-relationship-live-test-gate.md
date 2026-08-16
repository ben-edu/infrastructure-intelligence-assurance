# Milestone 5 PVE VM Storage Relationship Live Test Gate — 2026-08-16

## Status

Pending live source-artifact acceptance.

The bounded manual preflight has passed. The versioned collector introduced by this slice has not yet been accepted against BM2.

## Preflight result already established

Operator-run manual preflight on `mgmt-automation` used the existing discovery-only BM2 credential and issued HTTP GET requests only.

Accepted input scope:

```text
VM Backup Assurance version: 0.2
VM assets: 12
VMIDs: 100,101,102,103,104,105,106,107,108,109,110,9000
backup storage ID: local
node: delfan
```

Safe storage projection:

```text
storage ID: local
type: dir
shared: NOT_EXPLICITLY_RETURNED
node restrictions: none returned
images: true
backup: true
disabled: false
```

Every selected VM produced:

```text
observation: COMPLETE
managed primary storage IDs: [local]
direct/unresolved disk count: 0
relationship candidate: SAME_PVE_STORAGE_ID_AS_BACKUP
```

Preflight summary:

```text
SAME_PVE_STORAGE_ID_AS_BACKUP = 12
SAME_NODE_NON_SHARED_STORAGE_CANDIDATE = 0
UNKNOWN = 0
FAILED_TO_OBSERVE = 0
```

The preflight intentionally did not promote `BACKUP_FAILURE_DOMAIN`.

No raw VM config, disk value, volume ID, path, serial, cloud-init value, network value, MAC/IP value, credential, or snippet was printed or persisted.

No VM, storage, backup, snapshot, schedule, ACL, credential, or other infrastructure mutation occurred.

## Repository gate required

Run from the feature branch:

```bash
python3 -m pytest -q
```

Expected requirements:

```text
all tests pass
new schema validates generated artifact
manual-only wiring remains unchanged
no control methods are introduced
package version: 0.24.0
```

## Live collector gate required

On `mgmt-automation`:

```bash
set -euo pipefail

cd ~/projects/infrastructure-intelligence-assurance

ENV_FILE="/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env"
OUT="/tmp/pve-vm-storage-relationship-v0.1.json"
SUMMARY="/tmp/pve-vm-storage-relationship-v0.1.md"

PYTHONPATH=src python3 -m infra_assurance.proxmox_ve_vm_storage_relationship \
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

If package `0.24.0` is installed rather than source-tree execution, the equivalent CLI is `iia-proxmox-ve-vm-storage-relationship`.

## Acceptance checks

The live artifact should be inspected only through its bounded fields.

Required checks:

```text
pve_vm_storage_relationship_version = 0.1
mutation_allowed = false
source.type = proxmox_ve_api
source.source_id = pve-bm2
source.node = delfan
source.credential_runtime_approved = false
target_vms = 12
direct_or_unresolved_disks = 0
```

For the current preflight-equivalent state, the expected relationship count is:

```text
SAME_PVE_STORAGE_ID_AS_BACKUP = 12
DIFFERENT_PVE_STORAGE_ID_FROM_BACKUP = 0
UNKNOWN = 0
FAILED_TO_OBSERVE = 0
```

The expected storage metadata for `local` is currently:

```text
storage_type = dir
shared_status = NOT_EXPLICITLY_RETURNED
node_restrictions_status = NOT_EXPLICITLY_RETURNED
```

If live evidence differs, the live result wins and the difference must be investigated rather than forced to match this preflight.

## Trust acceptance

Even if all 12 relationships are `SAME_PVE_STORAGE_ID_AS_BACKUP`, acceptance means only that the bounded PVE storage-ID join is authoritative for this source snapshot.

It does not establish the same physical disk or hardware failure domain.

It does not establish failure-domain separation.

`BACKUP_FAILURE_DOMAIN` must remain unchanged until a separate accepted derived rule has sufficient evidence.
