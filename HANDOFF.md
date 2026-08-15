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

Current local PostgreSQL `15/main` is online, but no instantiated `pg_basebackup` schedule, enabled timer instance, or bounded active archive/backup configuration was observed. PostgreSQL is not selected as the next authoritative backup source from this host.

### Network/firewall semantics

BM1 uses UFW source-IP restrictions. Similar restrictions may exist on VMs or services.

Never convert timeout/unreachable network evidence into `ABSENT` unless the observation path is known complete. Use `FAILED_TO_REACH / UNKNOWN` where firewall/source restrictions may explain non-reachability.

### Current Proxmox discovery

Both PVE API endpoints are reachable from `mgmt-automation` on TCP/8006 and return HTTP 401 without credentials.

BM1 TLS certificate observed expired on `2025-08-04`; reachability was tested with insecure TLS verification, so BM1 certificate trust is not healthy/verified.

BM2 bounded authenticated GET discovery using an existing local token observed:

```text
PVE version: 9.1.9
release: 9.1
node: delfan
node status: online
storage ID: local
storage type: dir
storage content capability: iso,snippets,backup,vztmpl,images,rootdir
storage disabled: false
retention projection: keep-all=1
configured PBS storage IDs: none
cluster backup jobs: 0
```

Interpretation:

- BM2 PVE is a current authoritative source candidate for VM/storage/backup configuration;
- `content=backup` is storage capability/configuration, not proof of a backup artifact;
- `keep-all=1` is retention configuration, not proof that a recovery point exists;
- zero cluster backup jobs means no scheduled cluster backup job was observed in the returned scope;
- manual/external backup artifacts remain separately observable/unknown until storage content is queried;
- successful backup, integrity verification, restore testing, RPO and RTO remain separate evidence dimensions.

Operator explicitly confirms there is **no PBS today**.

### Mandatory future PBS compatibility

Even though PBS does not exist now, the architecture must support adding Proxmox Backup Server later without redesigning the core Backup and Recovery Assurance contract.

Keep the assurance model source-neutral. PVE local backups and future PBS evidence must use explicit source/provenance identities while satisfying the same common evidence dimensions:

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

Do not make core asset/protection schema depend on a PBS-specific datastore/snapshot ID. Future PBS-native identifiers belong in source-specific evidence/provenance context.

### Existing credential security status

Existing discovery credential file:

```text
/home/ben/projects/afpa-infra-rebuild/mcp/proxmox/proxmox.env
owner: ben
group: ben
mode: 0644
Git tracked: no
Git ignored: yes
configured endpoint: BM2
TLS verification: false
```

The token successfully performs bounded GET discovery, but it is **DISCOVERY_ONLY** until effective privileges are verified. Successful authentication does not prove least privilege.

The `0644` token file is not acceptable as the final platform runtime credential location without a separate hardening decision.

Sensitive Terraform tfvars/state must not be read to recover credentials.

## Exact next step — BM2 token scope + backup-content metadata preflight

Before implementing a PVE collector:

1. verify the existing BM2 token's effective read privilege scope using bounded safe API metadata if available;
2. never print token ID/secret or unrelated ACL identities;
3. use only HTTP GET requests;
4. query BM2 `local` storage backup-content metadata to determine whether recovery-point artifacts exist;
5. project only safe fields needed for artifact identity/type/time/size/VMID where the API supports them;
6. do not infer scheduled protection because cluster backup jobs are zero;
7. do not infer restore verification from backup artifact presence;
8. determine whether a new dedicated least-privilege Proxmox observer token is required before runtime integration;
9. BM1 remains separate and must get its own verified observation path; do not project BM2 state onto BM1.

No backup, restore, snapshot, prune, verify, garbage collection, schedule mutation, credential creation, or Terraform state read is allowed during discovery.

## Trust invariants

- observation credentials remain separate from future control credentials;
- infrastructure interaction remains read-only;
- collector failure is explicit;
- stale is not current;
- unknown is not absent;
- network timeout is not absence unless observation scope/path is complete;
- inference is not fact;
- declared and observed state remain separate;
- specialized systems remain authoritative;
- no passwords, tokens, private keys, raw Kubernetes Secret values, sensitive Terraform state, or complete sensitive connection strings enter evidence/AI context;
- current generated operational artifacts keep `mutation_allowed=false`.

## Maintenance rule

Keep this file compact. Update it only for accepted/merged slices, active PR changes, material live-gate outcomes, important blockers/risks, exact next-step changes, or runtime identity changes needed for continuation. Do not append transcripts or raw command logs.
