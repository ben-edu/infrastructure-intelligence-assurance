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
- current main HEAD after post-PR30 continuity merge: `987d583ade9003e46e4dbf2e027f62f1a0ab7c0d`
- accepted PR #30 code merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- management host: `mgmt-automation`
- checkout: `~/projects/infrastructure-intelligence-assurance`
- cluster: `k3s-main`
- runtime user: `infra-assurance`
- oneshot: `infra-assurance-kubernetes.service`
- timer: every 5 minutes

Milestones 0–3 are live validated. The current evidence-first Milestone 4 vertical path is accepted and sufficiently complete. Milestone 5 is active.

Known intentional drift remains:

```text
Ingress/validation/nginx-validation
Git:  k3s-master.soria-academie.fr
Live: k3s-master.behnam.fr
```

## Accepted Milestone 5 foundation — PR #30

- merge: `0e6f96a9f1b4adba34c43803a21a70116423b65c`
- package version: `0.19.0`
- backup assurance artifact: `/var/lib/infra-assurance/evidence/backup-assurance.json`
- backup assurance version: `0.1`
- mutation allowed: false

Accepted live foundation:

```text
217 passed
PVC collection: COMPLETE / CURRENT
PVC assets: 37
same-cycle asset set exact match: true
assets with direct controller reference: 16
protection UNKNOWN: 37
restore verification UNKNOWN: 37
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
```

## Active discovery — PR #32 authoritative backup source

- PR: `#32 Milestone 5 authoritative backup source discovery`
- branch: `docs/m5-backup-source-discovery`
- code/runtime mutation: none
- backup/restore operations: none
- credentials created/changed: none

Discovery report:

```text
docs/reports/2026-08-15-m5-authoritative-backup-source-discovery.md
```

### PostgreSQL conclusion

Current local PostgreSQL `15/main` is online, but no instantiated `pg_basebackup` schedule, no enabled instance symlink, and no bounded active archive/backup configuration were observed. PostgreSQL is not selected as the next authoritative backup source from this host.

### Current Proxmox/PBS discovery

Live from `mgmt-automation`:

```text
BM1 PVE API TCP/8006: REACHABLE
BM2 PVE API TCP/8006: REACHABLE
BM1 unauthenticated PVE /version: HTTP 401
BM2 unauthenticated PVE /version: HTTP 401
BM1 same-address TCP/8007: TIMEOUT
BM2 same-address TCP/8007: TIMEOUT
```

Both PVE endpoints are therefore currently reachable and authentication-required.

Do not classify the TCP/8007 timeouts as PBS absence. Operator-provided current context states that BM1 uses UFW source-IP restrictions, and similar restrictions may exist for VMs/services. Negative network reachability is therefore `FAILED_TO_REACH / UNKNOWN` when firewall path is not proven complete. PBS may also live on another host/VM.

Observed TLS metadata:

```text
BM1 CN=proxbenovh.cloud; certificate expired 2025-08-04
BM2 CN=delfan.local; certificate valid through 2027-10-13
```

BM1 reachability was observed using insecure TLS verification; certificate trust is not healthy/verified and must remain a separate fact.

Safe local/project metadata proves that an existing Proxmox API-token access pattern exists:

```text
api-cluster-infra Terraform provider uses API URL + token ID + token secret
bm1/bm2 Terraform variable declarations exist
local afpa-infra-rebuild Proxmox env file path exists
Proxmox env example defines BASE_URL / TOKEN_ID / TOKEN_SECRET / TLS options
```

Potentially sensitive Terraform state/tfvars were identified by filename only and must not be read for discovery.

A non-root check of `/etc/infra-assurance/collector.env` hit `PermissionError`; this was a helper limitation only and did not print secret data.

### Current interpretation

Proxmox VE is now a live candidate authoritative source for VM backup configuration because its API is reachable. PBS itself remains UNKNOWN.

The platform must not infer PBS absence from 8007 timeout. Prefer PVE's own configured storage/job evidence because PVE can integrate PBS as storage even when direct PBS reachability from `mgmt-automation` is restricted.

Configured PVE storage of type `pbs` would prove a PVE-to-PBS configuration, not successful backups. A configured PVE backup job would prove declared schedule, not successful execution/retention/restore verification.

## Exact next step — existing Proxmox credential metadata + bounded authenticated GET preflight

Use the existing local Proxmox env file only for a bounded discovery preflight. This existing token is discovery-only unless a later accepted check proves it is an appropriate least-privilege observer identity.

Preflight requirements:

1. inspect file owner/mode and variable names/presence only;
2. do not read or display Terraform state/tfvars;
3. internally map configured endpoint to BM1/BM2/OTHER without printing the raw URL;
4. authenticate only for GET requests;
5. first verify PVE version/identity;
6. if authorized, retrieve only safe projections of configured PVE storage types/IDs and cluster backup jobs;
7. specifically determine whether storage type `pbs` is configured;
8. never print raw storage config, usernames, passwords, token ID/secret, fingerprints, encryption-key references, or full connection strings;
9. stop on 401/403 rather than escalating privileges;
10. never run backup, restore, snapshot, prune, verify, garbage collection, or schedule mutation.

If the existing token appears broad/admin-like or unsuitable as an observation identity, stop after discovery and design a dedicated least-privilege observer identity separately.

## Trust invariants

- observation credentials remain separate from future control credentials;
- infrastructure interaction remains read-only;
- collector failure is explicit;
- stale is not current;
- unknown is not absent;
- network timeout is not absence unless the observation path is known complete;
- inference is not fact;
- declared and observed state remain separate;
- specialized systems remain authoritative;
- no passwords, tokens, private keys, raw Kubernetes Secret values, sensitive Terraform state, or complete sensitive connection strings enter evidence/AI context;
- current generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
