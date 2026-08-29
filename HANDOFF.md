# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #81: 27dad7917299b90688fd418b70bbec585c94ea7b
active branch: agent/m7-backup-assurance-operator-integration
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
full suite at runtime integration: 412 passed in 2.00s
cluster: k3s-main
scope: KUBERNETES_EXISTING_EVIDENCE_ONLY
workloads_total: 68
workloads_with_attention: 3
attention_now_total: 2
recent_changes_total: 0
unknowns_total: 0
required_live_verification_total: 0
```

Accepted current Kubernetes attention items:

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

## Accepted compact backup-assurance adapter

Accepted report:

```text
docs/reports/2026-08-29-m7-backup-assurance-operator-adapter.md
```

Accepted validation:

```text
focused tests: 6 passed in 0.05s
live read-only probe: source_status=COMPLETE / discovery_rc=0
full suite: 418 passed in 1.96s
```

Accepted compact backup summary:

```text
assets_total: 37
protection_unknown: 37
restore_verification_unknown: 37
unprotected_claims: 0
authoritative_backup_sources_integrated: 0
attention_total: 3
required_verification_categories_total: 8
```

Trust semantics that must remain true:

```text
UNKNOWN protection != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
unprotected claims require authoritative backup evidence
```

## Active slice — integrate compact backup assurance into operator attention

Goal:

```text
Combine the accepted Kubernetes operator-attention projection with the accepted compact backup-assurance adapter into one bounded cross-domain operator summary, without changing the existing runtime yet.
```

Prepared implementation:

```text
src/infra_assurance/operator_attention_backup.py
tests/test_operator_attention_backup.py
scripts/discovery/m7_backup_assurance_operator_integration_probe.py
```

Cross-domain scope:

```text
KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
```

Expected semantics:

```text
- preserve the existing Kubernetes attention items;
- add only compact aggregate backup attention items;
- add the eight authoritative backup/recovery verification categories;
- expose backup aggregate counts without per-asset backup details;
- fail closed on cluster mismatch;
- preserve exact total counts even when displayed sections are truncated;
- preserve UNKNOWN != UNPROTECTED;
- preserve restore verification UNKNOWN != recovery test overdue.
```

The active branch does NOT change:

```text
systemd
installed runtime under /opt
collector timer/service
infrastructure
permissions
datastores
```

No management-host or infrastructure mutation is authorized or required for this contract slice.

## Exact next gate

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m7-backup-assurance-operator-integration

python3 -m pytest -q \
  tests/test_operator_attention_backup.py

sudo env \
  PYTHONPATH="$PWD/src" \
  python3 "$PWD/scripts/discovery/m7_backup_assurance_operator_integration_probe.py"

echo "discovery_rc=$?"
```

Do not use strict interactive shell mode.

The one-time `sudo` probe is validation-only because the repo remains under `/home/ben` while evidence artifacts are protected. It reads only existing derived artifacts and performs no infrastructure query or write.

Acceptance rules:

```text
focused tests: PASS
probe source_status: COMPLETE
discovery_rc=0
source_artifacts_loaded=4
cluster_id=k3s-main
scope=KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
backup_unprotected_claims=0
unknown_is_not_unprotected=True
recovery_test_overdue_claimed=False
```

If accepted, create the report, run the full repository suite, inspect exact scope, PR/squash-merge, and only then decide whether runtime integration is warranted.

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
