# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #84: abd8fe56832f1868e09e1cd26afbbc40046d9965
active branch: agent/m7-incident-operator-adapter
Milestone 7: ACTIVE
management host: mgmt-automation
broader infrastructure mutation authorized: false
```

## Accepted cross-domain runtime baseline

Accepted report:

```text
docs/reports/2026-08-30-m7-cross-domain-runtime-integration.md
```

Installed runtime state:

```text
runtime identity: infra-assurance
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
prometheus_rule_context_integration < backup_assurance_foundation < operator_attention_backup
final suite: 429 passed in 2.15s
```

Current accepted operator evidence:

```text
cluster_id: k3s-main
attention_now_total: 5
required_live_verification_total: 8
backup_assets_total: 37
backup_protection_unknown: 37
backup_restore_verification_unknown: 37
backup_unprotected_claims: 0
```

Preserve:

```text
UNKNOWN protection != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
```

## Active slice — incident operator adapter

Report:

```text
docs/reports/2026-08-30-m7-incident-operator-adapter.md
```

Goal:

```text
Project existing incident-candidates.json into compact operator-facing evidence for grouped current signals without promoting candidates to confirmed incidents or root-cause conclusions.
```

Prepared files:

```text
HANDOFF.md
docs/reports/2026-08-30-m7-incident-operator-adapter.md
scripts/discovery/m7_incident_operator_adapter_probe.py
src/infra_assurance/incident_operator_adapter.py
tests/test_incident_operator_adapter.py
```

Source artifact:

```text
/var/lib/infra-assurance/evidence/incident-candidates.json
```

This source already exists in the current five-minute collector and is derived from current alert attention, Kubernetes event correlation, inventory, and change context.

Adapter scope:

```text
INCIDENT_CANDIDATES_EXISTING_EVIDENCE_ONLY
```

Projected fields are limited to aggregate candidate counts, compact candidate scope/state/count metadata, aggregate attention, deduplicated live-verification categories, truncation state, and trust semantics.

Raw alert labels/details, raw Event details, related workload details, field-level change/drift details, rationales, and logs are discarded.

Trust contract:

```text
mutation_allowed: False
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
```

A non-COMPLETE source domain must remain explicit as incomplete evidence. Candidate absence under incomplete source coverage is not negative evidence.

## Mutation boundary

This slice is repository-only plus a later read-only evidence probe.

It does NOT change:

```text
systemd
installed /opt runtime
collector service/timer
Kubernetes RBAC/kubeconfig
filesystem permissions
datastores
infrastructure
```

No deployment authorization is requested or implied.

## Exact next gate — FOCUSED TESTS

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git fetch origin
git switch --track origin/agent/m7-incident-operator-adapter
python3 -m pytest -q tests/test_incident_operator_adapter.py
```

If already on another local branch with this name, switch to it and pull `--ff-only` instead of recreating it.

Do not use strict interactive shell mode.

If focused tests pass, run the safe no-write probe against the protected current incident-candidates artifact. A failed observation must remain FAILED_TO_OBSERVE and must not be converted into zero candidate counts.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- infrastructure observation remains read-only except separately authorized bounded management-host deployments already accepted;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- incident candidates are not confirmed incidents;
- incident candidates are not root-cause conclusions;
- suppressed alerts/candidates are not treated as resolved conditions;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied;
- generated operational semantics keep `mutation_allowed=false`.
