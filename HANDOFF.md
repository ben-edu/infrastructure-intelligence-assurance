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

Accepted main after PR #86 includes the Kubernetes+backup+incident integration contract.

Accepted validation:

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

## Focused repository validation — ACCEPTED

Executed twice:

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

## Deployment helper dry-run — ACCEPTED

Executed without `--apply`.

Accepted dry-run scope:

```text
install accepted operator-attention modules
install existing systemd unit definition
systemctl daemon-reload
start existing infra-assurance-kubernetes.service once
verify operator-attention.json/.md with Kubernetes+backup+incident scope
```

Explicitly excluded:

```text
bootstrap-observer.sh
Kubernetes RBAC changes
kubeconfig changes
Git source configuration changes
new service/timer creation
filesystem permission broadening
```

Dry-run performed no installed-runtime, systemd, service, or infrastructure mutation.

## Authorization boundary — CURRENT GATE

```text
broader infrastructure mutation authorized: false
incident operator runtime deployment authorized: false
```

Fresh explicit authorization is required because the installed module set and unit content differ from the previously authorized runtime deployment.

If authorization is granted, it covers only:

```text
install the accepted five operator projection modules
install the prepared existing systemd unit
systemctl daemon-reload
start the existing oneshot service once
verify generated operator-attention artifact ownership and exact final scope
```

It does NOT authorize Kubernetes RBAC/kubeconfig changes, permission broadening, new services/timers/datastores, remediation, bootstrap, or unrelated infrastructure mutation.

## Exact next gate

Obtain fresh explicit authorization for the bounded incident-operator runtime deployment. Do not run `scripts/deploy-operator-attention-runtime.sh --apply` until authorization is explicitly given and recorded.

After an authorized deployment succeeds, verify installed ordering and safe allowlisted artifact content, then run the full repository suite before PR/merge.

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
