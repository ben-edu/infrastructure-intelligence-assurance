# Milestone 5 Proxmox VE Backup Evidence Live Test Gate — 2026-08-15

## Status

Pending management-host repository and manual BM2 live acceptance.

## Scope

Validate package `0.20.0` source artifact `proxmox_ve_backup_evidence_version=0.1` without runtime/systemd wiring and without provisioning or modifying Proxmox credentials.

## Required repository gate

- full pytest suite passes;
- adapter uses HTTP GET only;
- no Proxmox control CLI/client is present;
- existing systemd unit has no Proxmox adapter/token wiring;
- schema validation and unsafe-field rejection tests pass;
- complete empty storage scope and failed observation semantics remain distinct.

## Required live gate

Use the existing BM2 broad token only as a temporary manual discovery/test credential with explicit overrides. It must remain `credential_runtime_approved=false`.

Validate current BM2 safe projections:

- PVE identity and `delfan` node;
- current guest VMIDs/statuses;
- storage `local` safe configuration;
- current backup-job count;
- complete `local` backup-content scope;
- recovery-point artifact count and per-guest latest recovery point;
- current guest/storage coverage status.

Live state may differ from the discovery baseline; acceptance is based on trust invariants and source-consistent current facts, not immutable counts.

## Trust gates

- `mutation_allowed=false`;
- no runtime credential approval;
- no token ID/secret in output;
- no raw URL;
- no raw `volid` or archive path;
- no guest names;
- no storage server/path/username/fingerprint/encryption-key projection;
- Proxmox archive `protected` appears only as `archive_protection_flag`;
- no platform `PROTECTED`/`UNPROTECTED` classification;
- failed observation remains unknown;
- no backup, restore, snapshot, prune, verify, garbage collection, schedule change, guest mutation, ACL change, or credential mutation.

## Acceptance result

Not yet executed.
