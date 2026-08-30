# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #82: 0649699dfcd09828fce6937fcc27ec870daf057a
active branch: agent/m7-cross-domain-runtime-contract
Milestone 7: ACTIVE
management host: mgmt-automation
broader infrastructure mutation authorized: false
```

## Accepted M7 runtime baseline

The installed five-minute collector currently produces Kubernetes-only operator-attention JSON/Markdown under `infra-assurance`.

Accepted reports:

```text
docs/reports/2026-08-29-m7-operator-attention-summary-contract.md
docs/reports/2026-08-29-m7-operator-attention-runtime-integration.md
```

Current installed runtime scope remains:

```text
KUBERNETES_EXISTING_EVIDENCE_ONLY
```

Accepted Kubernetes attention baseline:

```text
attention_now_total: 2
Service/monitoring/loki-headless -> SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES / AMBIGUOUS
Ingress/validation/nginx-validation -> DECLARED_OBSERVED_DRIFT / DRIFT
```

Preserve rejected/incomplete attempts:

```text
interactive-user operator-attention probe: FAILED_TO_OBSERVE / PermissionError
service-identity probe from /home/ben source tree: FAILED_TO_OBSERVE before code execution
```

Do not reuse either as negative evidence.

## Accepted backup-assurance operator evidence

Accepted reports:

```text
docs/reports/2026-08-29-m7-backup-assurance-operator-adapter.md
docs/reports/2026-08-30-m7-backup-assurance-operator-integration.md
```

Accepted cross-domain contract validation:

```text
focused tests: 6 passed in 0.06s
live read-only probe: source_status=COMPLETE / discovery_rc=0
full suite: 424 passed in 2.13s
source_artifacts_loaded: 4
cluster_id: k3s-main
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
attention_now_total: 5
required_live_verification_total: 8
backup_assets_total: 37
backup_protection_unknown: 37
backup_restore_verification_unknown: 37
backup_unprotected_claims: 0
```

Trust semantics that must remain true:

```text
UNKNOWN protection != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
unprotected claims require authoritative backup evidence
```

## Active slice — cross-domain runtime contract

Goal:

```text
Make the already-accepted cross-domain operator projection executable as a file-writing runtime command, without changing the installed collector or systemd yet.
```

Prepared changes:

```text
src/infra_assurance/operator_attention_backup.py
tests/test_operator_attention_backup_runtime.py
HANDOFF.md
```

The cross-domain module provides a CLI contract:

```text
python3 -m infra_assurance.operator_attention_backup
  --inventory <inventory.json>
  --context <context.json>
  --change-context <change-context.json>
  --backup-assurance <backup-assurance.json>
  --out <operator-attention.json>
  --summary-out <operator-attention.md>
```

The writer:

```text
- reads only the four accepted derived artifacts;
- uses the accepted cross-domain builder;
- writes JSON and Markdown atomically using existing io_utils;
- performs no live infrastructure query;
- projects no per-asset backup details;
- preserves mutation_allowed=false;
- preserves UNKNOWN != UNPROTECTED;
- preserves restore verification UNKNOWN != recovery test overdue.
```

The Markdown renderer adds only aggregate backup-assurance counts and explicitly describes the trust boundary as Kubernetes plus backup-assurance evidence.

This branch does NOT change:

```text
systemd
/opt installed runtime
collector service/timer
infrastructure
permissions
datastores
```

## Repository validation — ACCEPTED

Focused tests executed on `mgmt-automation`:

```text
8 passed in 0.46s
```

Accepted interpretation:

```text
- existing cross-domain builder tests remain green;
- file-writing runtime CLI tests pass;
- JSON and Markdown writer behavior is covered;
- non-positive max-items fails closed;
- no runtime/systemd/infrastructure mutation occurred.
```

## Exact next gate — LIVE READ-ONLY NO-DEPLOY CHECK

Run a bounded one-time privileged Python projection from repository code against the four protected existing artifacts. This check performs no file write, no live infrastructure query, no systemd action, and no `/opt` change.

Expected sources:

```text
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/context.json
/var/lib/infra-assurance/evidence/change-context.json
/var/lib/infra-assurance/evidence/backup-assurance.json
```

Acceptance rules:

```text
source_status: COMPLETE
source_artifacts_loaded: 4
cluster_id: k3s-main
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
mutation_allowed: False
attention_now_total: 5
required_live_verification_total: 8
backup_unprotected_claims: 0
unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
no raw source or per-asset backup detail printed
```

The one-time `sudo` execution is validation-only because repository code is under `/home/ben` while artifacts are protected. It is not the target runtime privilege model.

If accepted:

1. create/update the runtime-contract report;
2. run the full repository suite;
3. verify exact branch scope and no temporary/debug files;
4. PR/squash-merge;
5. only then consider a separate explicitly authorized runtime/systemd deployment slice.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- existing infrastructure observation remains read-only;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- UNKNOWN protection is never treated as UNPROTECTED;
- restore verification UNKNOWN is never treated as overdue restore testing;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied by an attention item;
- generated operational semantics keep `mutation_allowed=false`.
