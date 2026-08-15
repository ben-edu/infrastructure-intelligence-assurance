# Milestone 5 — Proxmox VE Backup Evidence

## Goal

Add the first authoritative backup-source adapter without changing infrastructure, reusing an administrative credential in runtime, or prematurely classifying protection quality.

Selected source: BM2 Proxmox VE.

## Output

Manual/live-test artifact paths are caller-selected. The accepted source artifact contract is:

```text
proxmox_ve_backup_evidence_version: 0.1
source.type: proxmox_ve_api
source.operation: BOUNDED_HTTP_GET_BACKUP_EVIDENCE
mutation_allowed: false
```

This slice is not wired into `infra-assurance-kubernetes.service`.

## Queries

HTTP GET only:

```text
/api2/json/version
/api2/json/nodes
/api2/json/cluster/resources?type=vm
/api2/json/storage
/api2/json/cluster/backup
/api2/json/nodes/<node>/storage/<selected-storage>/content?content=backup
```

No mutating API method or Proxmox control CLI is permitted.

## Safe projection

Persist:

- PVE version/release/repository identity;
- node identity/status;
- guest VMID/type/status/node;
- storage ID/type/backup capability/disabled state/bounded retention policy/PBS-backend boolean;
- bounded cluster backup-job metadata;
- storage-content observation status;
- recovery-point VMID/node/storage/format/time/size/source-native archive protection flag;
- deterministic projected recovery-point ID;
- per-guest selected-storage recovery-point coverage.

Do not persist:

- token ID or secret;
- raw endpoint URL;
- raw API payload;
- raw volume ID/path;
- guest name;
- storage server/path/username/password;
- certificate fingerprint;
- encryption-key references;
- Terraform state/tfvars;
- arbitrary labels/configuration.

## Credential boundary

Normal collector execution rejects:

- credential files readable by group/other;
- disabled TLS verification.

Manual discovery/live-test may use explicit flags:

```text
--allow-discovery-credential
--allow-insecure-tls-discovery
```

These flags do not approve the credential for runtime. The current BM2 token is broad/admin-like and must remain discovery-only.

## Failure semantics

A successful empty storage-content response is complete evidence for that exact selected storage scope:

```text
NO_RECOVERY_POINT_OBSERVED_IN_COMPLETE_STORAGE_SCOPE
```

A failed/unauthorized content request is:

```text
FAILED_TO_OBSERVE
coverage: UNKNOWN
```

Do not convert failed observation into zero backup artifacts.

Overall source status:

```text
COMPLETE
PARTIAL
FAILED_TO_OBSERVE
```

## Recovery-point semantics

A projected backup-content record is an observed recovery-point artifact.

It does not prove:

```text
restore verification
integrity verification
application consistency
current scheduled protection
RPO compliance
RTO compliance
```

The Proxmox field `protected` is persisted only as:

```text
archive_protection_flag
```

It is never platform `protection_status` and never maps to `PROTECTED` or `UNPROTECTED`.

## Current live discovery baseline

Before implementation, source discovery observed on BM2:

```text
PVE: 9.1.9
node: delfan
current QEMU guests: 12
storage: local / dir / backup-enabled
retention projection: keep-all=1
PBS storage: none configured
cluster backup jobs: 0
local recovery-point artifacts: 12
VMIDs with local recovery points: 100,101,106,107,108,109
current VMIDs without local recovery point in this complete scope: 102,103,104,105,110,9000
```

This baseline may change; live acceptance should verify invariants and current-source agreement rather than treating every count as immutable.

## Future PBS compatibility

PBS is not present today, but future support is mandatory.

Do not encode PBS-specific identifiers into common assurance semantics. A future PBS-native adapter must preserve separate source provenance and satisfy the same common assurance dimensions where authoritative evidence exists.

## Acceptance boundary

Repository acceptance must prove:

- package version `0.20.0`;
- full tests pass;
- schema validation passes;
- adapter contains only HTTP GET and no control CLI/client;
- existing systemd runtime does not invoke the adapter or expose Proxmox credentials;
- complete empty scope differs from failed observation;
- source-native `protected` cannot become platform protection classification;
- unsafe/raw fields are absent from projections.

Manual BM2 live acceptance must prove:

- source status `COMPLETE` for the bounded GET scope;
- runtime credential approved remains false;
- discovery override is explicit for the current 0644/TLS-insecure credential;
- current node/storage/guest/recovery-point facts are safely projected;
- every current guest has exactly one selected-storage coverage record;
- complete storage scope can identify observed and not-observed recovery-point states without global `UNPROTECTED` claims;
- no token/URL/raw volume/config sensitive field enters JSON/Markdown;
- no backup/restore/snapshot/prune/verify/GC or other mutation occurs.

Do not wire runtime credentials or systemd in this slice.
