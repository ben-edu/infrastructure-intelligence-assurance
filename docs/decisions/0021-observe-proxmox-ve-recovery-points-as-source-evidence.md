# ADR 0021 — Observe Proxmox VE Recovery Points as Source Evidence

## Status

Proposed. Repository implementation is in progress and requires manual live acceptance before merge.

## Context

Milestone 5 foundation identifies Kubernetes PVC stateful assets but keeps backup protection `UNKNOWN` until authoritative backup evidence exists.

Bounded source discovery established BM2 Proxmox VE as the first viable authoritative backup evidence source:

- PVE 9.1.9 is live on BM2;
- node `delfan` is online;
- storage `local` supports backup content;
- 12 current QEMU guests were observed;
- 12 `vma.zst` recovery-point artifacts were observed across six current VMIDs;
- six other current VMIDs had no artifact in the complete `local` storage scope;
- cluster backup jobs were zero;
- no PBS storage is configured today;
- the existing discovery token is broad/admin-like and is rejected for runtime.

The operator requires future Proxmox Backup Server support without redesigning the core assurance model.

## Decision

Add a Proxmox VE source adapter that emits bounded backup/recovery-point evidence as a separate artifact before any downstream assurance integration.

The adapter is source evidence, not a protection classifier.

### Read-only boundary

The adapter uses HTTP GET only. It must not expose or implement backup, restore, snapshot, prune, verify, garbage collection, schedule mutation, guest mutation, or credential mutation.

The first implementation is intentionally not wired into systemd because the currently available token is not an acceptable runtime observer credential.

### Credential boundary

Normal collector execution refuses a group/world-readable credential file and refuses disabled TLS verification.

Manual discovery/live-test execution may use explicit override flags, but the produced artifact must show that the credential is not runtime-approved.

A dedicated least-privilege observer identity is a separate future access-control decision and is not provisioned during the current read-only phase.

### Source projection

Persist only bounded safe fields:

- PVE version/release identity;
- node name/status;
- guest VMID/type/status/node;
- storage ID/type, whether backup content is enabled, disabled state, bounded retention policy, and whether the backend type is `pbs`;
- bounded backup-job metadata;
- selected storage-content scope status;
- recovery-point VMID, storage, node, format, creation time, size, and source-native archive protection flag;
- deterministic projected recovery-point ID;
- per-guest selected-storage recovery-point coverage.

Do not persist raw volume IDs, raw API payloads, guest names, endpoint URLs, token material, storage server/path fields, usernames, fingerprints, encryption-key references, or arbitrary storage configuration.

### Failure semantics

A complete empty storage-content response means no recovery-point artifact was observed in that exact node/storage scope.

A failed or unauthorized content observation remains `UNKNOWN` / `FAILED_TO_OBSERVE`. It must not be converted to an empty scope.

Overall source status is:

- `COMPLETE` when all bounded GET observations complete;
- `PARTIAL` when identity succeeds but one or more later observations fail;
- `FAILED_TO_OBSERVE` when source identity cannot be observed.

### Assurance semantics

A returned PVE backup artifact is evidence of an observed recovery point. It is not evidence of:

- restore verification;
- integrity verification;
- current scheduled protection;
- application consistency;
- RPO compliance;
- RTO compliance.

The PVE archive field `protected=false` is a source-native retention/deletion-protection flag. It must never map to platform assurance `UNPROTECTED`.

### Future PBS compatibility

Keep the core Backup and Recovery Assurance model source-neutral.

PVE-local and future PBS-native evidence are separate adapters with explicit provenance. Both may satisfy common assurance dimensions such as mechanism, last observed recovery point/success evidence, retention, failure domain, integrity verification, restore test, RPO, and RTO.

PBS datastore/namespace/snapshot identifiers belong in PBS source-specific evidence, not in common asset/protection identity.

PVE may later report that a storage backend type is `pbs`; that configuration evidence must remain distinct from stronger PBS-native evidence.

## Consequences

The platform can begin consuming authoritative VM recovery-point evidence without reusing an administrative credential in runtime and without prematurely asserting protection quality.

A later slice may integrate accepted PVE recovery-point evidence into a source-neutral backup assurance model. Runtime wiring remains blocked until a dedicated least-privilege Proxmox observer credential and trustworthy TLS path are separately accepted.
