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
incident operator runtime deployment authorized: true
incident operator runtime deployment performed: true
```

## Accepted contract baseline

The accepted Kubernetes+backup+incident integration contract is already on `main`.

```text
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
cluster_id: k3s-main
attention_now_total: 7
required_live_verification_total: 14
incident_candidates_total: 4
incident_active_candidates: 4
incident_source_status: PARTIAL
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

Accepted contract validation before runtime deployment:

```text
corrective focused tests: 6 passed in 0.06s
contract full suite: 441 passed in 2.39s
```

## Active slice — incident operator installed-runtime integration

Report:

```text
docs/reports/2026-08-30-m7-incident-operator-runtime-integration.md
```

Exact intended branch scope:

```text
HANDOFF.md
docs/reports/2026-08-30-m7-incident-operator-runtime-integration.md
scripts/deploy-operator-attention-runtime.sh
systemd/infra-assurance-kubernetes.service
tests/test_operator_attention_incident_runtime_integration.py
```

Prepared/expected runtime order:

```text
prometheus_rule_context_integration
< backup_assurance_foundation
< operator_attention_backup
< operator_attention_incident
```

Runtime identity/sandbox must remain:

```text
User=infra-assurance
Group=infra-assurance
PYTHONPATH=/opt/infra-assurance/src
NoNewPrivileges=true
ProtectHome=true
existing ReadWritePaths only
```

## Repository validation — ACCEPTED

Focused wiring tests were executed twice:

```text
11 passed in 0.09s
11 passed in 0.10s
```

Accepted interpretation:

```text
existing observability-before-backup invariant preserved: true
backup_assurance_foundation < operator_attention_backup: true
operator_attention_backup < operator_attention_incident: true
service identity/sandbox preserved: true
new service/timer introduced: false
final expected scope encoded in helper: true
```

## Deployment dry-run — ACCEPTED

Dry-run confirmed the bounded mutation set and explicitly excluded bootstrap, Kubernetes RBAC/kubeconfig changes, Git source configuration changes, new service/timer creation, and filesystem permission broadening.

## Authorization — ACCEPTED AND BOUNDED

Fresh explicit user authorization was granted on 2026-08-30.

It covered only:

```text
install the accepted five operator projection modules
install the prepared existing systemd unit
systemctl daemon-reload
start the existing oneshot service once
verify generated operator-attention artifact ownership and exact final scope
```

It did not authorize unrelated infrastructure mutation, remediation, Kubernetes mutation, permission broadening, bootstrap, new services/timers, or new datastores.

## Authorized bounded deployment — EXECUTED / HELPER GATE ACCEPTED

Executed on `mgmt-automation` after pulling the authorization-recording branch head:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
runtime_scope=KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

Accepted interpretation:

```text
bounded apply executed: true
existing oneshot completed successfully: true
operator-attention JSON produced: true
operator-attention Markdown produced: true
runtime identity remained infra-assurance: true
helper observed exact final scope: true
broader infrastructure mutation authorization: false
```

This helper result does not replace the separate installed-content verification gate.

## Exact next gate — READ-ONLY INSTALLED ORDER + ARTIFACT VERIFICATION

Perform a separate bounded read-only verification against:

```text
/etc/systemd/system/infra-assurance-kubernetes.service
/var/lib/infra-assurance/evidence/operator-attention.json
```

Hard conditions:

```text
prometheus_rule_context_integration < backup_assurance_foundation < operator_attention_backup < operator_attention_incident
mutation_allowed: False
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
backup unknown_is_not_unprotected: True
backup recovery_test_overdue_claimed: False
```

Current counts may change with new evidence and must not be treated as hard-coded invariants. Truncation and source completeness must be printed explicitly.

If this gate passes, record exact evidence, then pull the latest branch head and run the full repository suite without `sudo`. Only after that may branch scope/PR/merge gates proceed.

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
- this deployment authorization was bounded to the recorded incident-operator runtime deployment only.
