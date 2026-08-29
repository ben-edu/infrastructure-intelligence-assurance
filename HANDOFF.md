# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #80: 11a6b69ecc55c6f356153fa4f5689c717f9cf754
active branch: agent/m7-backup-assurance-operator-adapter
Milestone 7: ACTIVE
management host: mgmt-automation
broader infrastructure mutation authorized: false
```

## Accepted M7 operator-attention runtime baseline

Accepted reports:

```text
docs/reports/2026-08-29-m7-operator-attention-summary-contract.md
docs/reports/2026-08-29-m7-operator-attention-runtime-integration.md
```

Accepted runtime state:

```text
operator-attention runtime identity: infra-assurance
operator-attention JSON/Markdown: generated in existing collector cycle
focused tests: 7 passed in 0.21s
full suite: 412 passed in 2.00s
cluster: k3s-main
scope: KUBERNETES_EXISTING_EVIDENCE_ONLY
workloads_total: 68
workloads_with_attention: 3
attention_now_total: 2
recent_changes_total: 0
unknowns_total: 0
required_live_verification_total: 0
```

Accepted attention items:

```text
Service/monitoring/loki-headless
  SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES / AMBIGUOUS

Ingress/validation/nginx-validation
  DECLARED_OBSERVED_DRIFT / DRIFT
```

Preserve rejected/incomplete attempts:

```text
interactive-user operator-attention probe: FAILED_TO_OBSERVE / PermissionError
service-identity probe from /home/ben source tree: FAILED_TO_OBSERVE before code execution
```

Do not reuse either as negative evidence.

## Active slice — compact backup-assurance operator adapter

Roadmap gap addressed:

```text
What is unprotected?
Which recovery test is overdue?
What is unknown about protection/recovery?
```

Current authoritative runtime artifact already exists:

```text
/var/lib/infra-assurance/evidence/backup-assurance.json
```

Important current trust semantics from the accepted backup-assurance foundation:

```text
protection status is UNKNOWN when authoritative backup evidence is not integrated
UNKNOWN != UNPROTECTED
unprotected claims require sufficient authoritative backup evidence
restore verification UNKNOWN != restore test overdue
```

Current foundation summary schema includes:

```text
assets_total
assets_stale
assets_freshness_unknown
protection_unknown
restore_verification_unknown
unprotected_claims
authoritative_backup_sources_integrated
```

Prepared implementation:

```text
src/infra_assurance/backup_operator_adapter.py
tests/test_backup_operator_adapter.py
scripts/discovery/m7_backup_assurance_operator_adapter_probe.py
```

The adapter intentionally projects only compact aggregate counts, compact attention codes, and deduplicated authoritative verification categories. It discards per-asset details and raw unknown text.

Expected operator semantics:

```text
BACKUP_PROTECTION_UNKNOWN -> aggregate UNKNOWN only
RESTORE_VERIFICATION_UNKNOWN -> aggregate UNKNOWN only
AUTHORITATIVE_BACKUP_SOURCE_NOT_INTEGRATED -> explicit evidence gap
UNPROTECTED_CLAIMS_OBSERVED -> only when source summary explicitly reports >0 authoritative claims
recovery_test_overdue_claimed -> always false in this slice
```

No runtime integration, service change, datastore, live infrastructure query, or management-host mutation is part of this contract slice.

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m7-backup-assurance-operator-adapter

python3 -m pytest -q \
  tests/test_backup_operator_adapter.py

sudo env \
  PYTHONPATH="$PWD/src" \
  python3 "$PWD/scripts/discovery/m7_backup_assurance_operator_adapter_probe.py"

echo "discovery_rc=$?"
```

Do not use strict interactive shell mode.

The one-time `sudo` probe is validation-only because the repository is under `/home/ben` while the evidence artifact is protected. It performs only a bounded read of `backup-assurance.json`; it is not a runtime design.

Acceptance rules:

- focused tests pass;
- probe returns `source_status: COMPLETE` and `discovery_rc=0`;
- raw backup-assurance artifact is not printed;
- per-asset details are not projected;
- UNKNOWN is not rewritten as UNPROTECTED;
- no recovery-test-overdue claim is produced without authoritative timing evidence;
- source failure remains FAILED_TO_OBSERVE, never zero-risk evidence.

If accepted, create the report, run the full repository suite, inspect exact branch scope, PR/squash-merge, then decide whether to integrate this compact adapter into the operator-attention runtime.

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
- generated operational artifacts keep `mutation_allowed=false`.
