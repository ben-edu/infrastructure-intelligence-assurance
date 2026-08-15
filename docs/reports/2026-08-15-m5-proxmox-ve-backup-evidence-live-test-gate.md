# Milestone 5 Proxmox VE Backup Evidence Live Test Gate — 2026-08-15

## Status

Accepted.

## Scope

Validate package `0.20.0` source artifact `proxmox_ve_backup_evidence_version=0.1` without runtime/systemd wiring and without provisioning or modifying Proxmox credentials.

## Repository gate

Accepted on `mgmt-automation`:

```text
package version: 0.20.0
RBAC changes: none
systemd changes: none
read-only required markers: complete
control/mutation markers: none
runtime Proxmox wiring: none
228 passed in 1.34s
```

A stale package-version pin in the historical Milestone 5 foundation wiring test was found during the first run and removed. The foundation test now validates its CLI contract while package `0.20.0` is enforced by the Proxmox adapter slice.

## Manual BM2 live gate

The existing BM2 credential was used only as a temporary manual GET-only discovery/test credential with explicit overrides. It remained rejected for runtime.

Accepted trust facts:

```text
source status: COMPLETE
mutation_allowed: false
credential_runtime_approved: false
credential_file_mode_secure: false
TLS verification: false
discovery override used: true
```

All bounded observations completed with HTTP 200:

```text
GET_VERSION
GET_NODES
GET_GUEST_RESOURCES
GET_STORAGE_CONFIG
GET_CLUSTER_BACKUP_JOBS
GET_STORAGE_BACKUP_CONTENT:local
```

Observed BM2 source facts:

```text
PVE version: 9.1.9
release: 9.1
node: delfan / ONLINE
storage: local / dir
backup content enabled: true
storage disabled: false
retention projection: keep-all=1
pbs backend: false
cluster backup jobs: 0
current guests: 12
recovery points observed: 12
```

Current guest VMIDs:

```text
100,101,102,103,104,105,106,107,108,109,110,9000
```

Recovery-point coverage in the complete `delfan/local` scope:

```text
RECOVERY_POINT_OBSERVED: 6
NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE: 6
UNKNOWN: 0
```

VMIDs with at least one observed recovery point:

```text
100,101,106,107,108,109
```

VMIDs with no recovery point observed in the complete selected storage scope:

```text
102,103,104,105,110,9000
```

Observed recovery points:

```text
VMID 100: 2; latest 2026-05-08T06:13:59Z
VMID 101: 1; latest 2026-05-08T10:36:12Z
VMID 106: 3; latest 2026-08-14T16:13:14Z
VMID 107: 3; latest 2026-08-14T16:40:35Z
VMID 108: 2; latest 2026-04-15T12:30:02Z
VMID 109: 1; latest 2026-04-13T10:34:52Z
```

The source-native archive protection flag was `false` on the observed records. This remains source-native metadata only and was not mapped to platform protection state.

## Assurance boundary

The artifact retained the required unknowns:

```text
INTEGRITY_VERIFICATION_NOT_OBSERVED
RESTORE_VERIFICATION_NOT_OBSERVED
RPO_RTO_NOT_OBSERVED
SCHEDULED_PROTECTION_NOT_INFERRED
```

No platform `protection_status` field was emitted.

Recovery-point presence therefore establishes only that a PVE-local backup artifact was observed in the bounded source scope. It does not establish restore verification, integrity verification, current scheduled protection, RPO compliance, or RTO compliance.

A complete selected storage scope with zero artifacts for a VM is a valid negative observation for that exact scope only. It must not be generalized to all possible backup sources and must not be converted to platform `UNPROTECTED` without stronger source-neutral assurance rules.

## Sensitive-data and mutation gate

Accepted:

```text
forbidden projected keys: none
raw URL markers: false
credential material projection: none
```

No token ID/secret, endpoint URL, raw `volid`, guest name, storage server/path/username, fingerprint, encryption-key reference, Terraform state/tfvars, or raw API payload entered the artifact.

No backup, restore, snapshot, prune, verify, garbage collection, schedule change, ACL change, guest mutation, credential mutation, RBAC change, or systemd/runtime credential wiring occurred.

## Acceptance result

```text
PR #33 LIVE ACCEPTANCE: PASS
```

The Proxmox VE source adapter is accepted as authoritative bounded recovery-point source evidence. Runtime wiring remains blocked until a dedicated least-privilege Proxmox observer identity and trusted TLS path are separately accepted.
