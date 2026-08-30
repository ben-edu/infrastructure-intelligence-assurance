# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #86: 98cb3702faf6e23a15791ff32c36c7a7bd594c98
active branch: agent/m7-incident-operator-runtime-integration
Milestone 7: ACTIVE
management host: mgmt-automation
broader infrastructure mutation authorized: false
incident operator runtime deployment authorized: false
```

## Accepted installed runtime baseline

Current installed runtime is still the previously accepted Kubernetes+backup operator projection:

```text
runtime identity: infra-assurance
scope: KUBERNETES_AND_BACKUP_EXISTING_EVIDENCE_ONLY
prometheus_rule_context_integration < backup_assurance_foundation < operator_attention_backup
```

No incident operator runtime deployment has occurred yet.

## Accepted incident integration contract

Accepted report:

```text
docs/reports/2026-08-30-m7-incident-operator-integration-contract.md
```

Accepted contract/live validation:

```text
corrective focused tests: 6 passed in 0.06s
live no-write integration probe: source_status=COMPLETE
cluster_id: k3s-main
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
attention_now_total: 7
required_live_verification_total: 14
incident_candidates_total: 4
incident_active_candidates: 4
incident_source_status: PARTIAL
full repository suite: 441 passed in 2.39s
```

Trust semantics remain:

```text
mutation_allowed: False
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
UNKNOWN backup protection != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
```

## Active slice — incident operator installed-runtime integration

Report:

```text
docs/reports/2026-08-30-m7-incident-operator-runtime-integration.md
```

Goal:

```text
Run the accepted Kubernetes+backup+incident operator projection in the existing five-minute collector under infra-assurance, without introducing a new service, timer, identity, datastore, RBAC, kubeconfig, or filesystem permission.
```

Exact intended branch scope:

```text
HANDOFF.md
docs/reports/2026-08-30-m7-incident-operator-runtime-integration.md
scripts/deploy-operator-attention-runtime.sh
systemd/infra-assurance-kubernetes.service
tests/test_operator_attention_incident_runtime_integration.py
```

Prepared runtime order:

```text
incident_runtime
...
prometheus_rule_context_integration
< backup_assurance_foundation
< operator_attention_backup
< operator_attention_incident
```

The final incident operator post-step reads the same-run `operator-attention.json` and `incident-candidates.json`, then atomically writes the final operator artifact back to the existing `operator-attention.json/.md` paths.

Runtime identity/sandbox remain:

```text
User=infra-assurance
Group=infra-assurance
PYTHONPATH=/opt/infra-assurance/src
NoNewPrivileges=true
ProtectHome=true
existing ReadWritePaths only
```

Prepared bounded deployment helper installs only:

```text
operator_attention.py
backup_operator_adapter.py
operator_attention_backup.py
incident_operator_adapter.py
operator_attention_incident.py
systemd/infra-assurance-kubernetes.service
```

It verifies final scope:

```text
KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

Dry-run is the default. No `--apply` execution is authorized yet.

The helper does not run `bootstrap-observer.sh`, change Kubernetes RBAC/kubeconfig, change Git source configuration, add a service/timer, or broaden filesystem permissions.

## Exact next gate — FOCUSED REPOSITORY TESTS

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git fetch origin
git switch --track origin/agent/m7-incident-operator-runtime-integration
python3 -m pytest -q \
  tests/test_backup_assurance_foundation_wiring.py \
  tests/test_operator_attention_cross_domain_runtime_integration.py \
  tests/test_operator_attention_incident_runtime_integration.py
```

If the local branch already exists, switch to it and pull `--ff-only` instead of recreating it.

Do not use strict interactive shell mode.

If focused tests pass, run only:

```bash
sudo bash scripts/deploy-operator-attention-runtime.sh
```

That is dry-run only. Do not use `--apply` until the dry-run is reviewed and fresh explicit authorization is obtained.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- incident candidates are not confirmed incidents or root-cause conclusions;
- suppressed candidates are not treated as resolved;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation is implied;
- generated operational semantics keep `mutation_allowed=false`;
- any installed-runtime mutation requires fresh explicit authorization.
