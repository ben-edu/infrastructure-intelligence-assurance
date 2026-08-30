# Milestone 7 — Incident Operator Installed-Runtime Integration

Date: 2026-08-30
Status: BOUNDED DEPLOYMENT EXECUTED / HELPER GATE ACCEPTED / INSTALLED CONTENT VERIFICATION PENDING
Mode: existing five-minute collector runtime integration

## Goal

Run the accepted Kubernetes+backup+incident operator contract in the existing `infra-assurance-kubernetes.service` runtime without adding a service, timer, identity, datastore, Kubernetes RBAC, kubeconfig, or filesystem permission.

## Accepted baseline

Accepted main checkpoint before this slice:

```text
98cb3702faf6e23a15791ff32c36c7a7bd594c98
```

Accepted final scope:

```text
KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

Accepted pre-deployment live contract summary:

```text
cluster_id: k3s-main
attention_now_total: 7
required_live_verification_total: 14
incident_candidates_total: 4
incident_active_candidates: 4
incident_source_status: PARTIAL
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
```

## Runtime wiring

Prepared order:

```text
prometheus_rule_context_integration
< backup_assurance_foundation
< operator_attention_backup
< operator_attention_incident
```

The final incident post-step consumes the same-run Kubernetes+backup `operator-attention.json` plus the same-run `incident-candidates.json`, then atomically writes the final projection back to the existing `operator-attention.json/.md` paths.

Runtime identity and sandbox are intended to remain unchanged:

```text
User=infra-assurance
Group=infra-assurance
PYTHONPATH=/opt/infra-assurance/src
NoNewPrivileges=true
ProtectHome=true
existing ReadWritePaths only
```

## Focused repository validation — ACCEPTED

Executed twice on `mgmt-automation`:

```text
11 passed in 0.09s
11 passed in 0.10s
```

The focused gate covered the established observability-before-backup invariant, backup-before-operator ordering, final incident post-step ordering, unchanged service identity/sandbox, bounded helper module set, reuse of existing artifact paths, and absence of a new service/timer.

## Deployment helper dry-run — ACCEPTED

Dry-run stated the exact bounded mutation plan:

```text
install accepted operator projection modules under /opt/infra-assurance/src/infra_assurance/
install the existing systemd unit definition
systemctl daemon-reload
start the existing infra-assurance-kubernetes.service once
verify operator-attention.json and operator-attention.md with the final accepted scope
```

Explicit exclusions remained:

```text
bootstrap-observer.sh
Kubernetes RBAC changes
kubeconfig changes
Git source configuration changes
new service/timer creation
filesystem permission broadening
```

## Authorization — ACCEPTED

Fresh explicit user authorization was granted on 2026-08-30 for this bounded deployment only.

```text
broader infrastructure mutation authorized: false
incident operator runtime deployment authorized: true
```

The authorization covered installing the accepted five operator projection modules and prepared existing unit, running `daemon-reload`, starting the existing oneshot once, and verifying generated artifact ownership/scope. It did not authorize remediation, Kubernetes mutation, permission broadening, new services/timers/datastores, bootstrap, or unrelated infrastructure mutation.

## Authorized bounded deployment — EXECUTED / HELPER GATE ACCEPTED

Executed on `mgmt-automation` after pulling the authorization-recording branch head.

Observed helper output:

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
existing oneshot result: success
JSON artifact observed: true
Markdown artifact observed: true
runtime identity reported by helper: infra-assurance
exact final scope reported by helper: true
broader mutation authorization: false
```

The helper gate is necessary but is not the final installed-content acceptance gate.

## Remaining verification gate

Perform a separate read-only check of the installed unit and protected generated JSON artifact.

Required ordering:

```text
prometheus_rule_context_integration
< backup_assurance_foundation
< operator_attention_backup
< operator_attention_incident
```

Required trust conditions:

```text
mutation_allowed: False
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
backup unknown_is_not_unprotected: True
backup recovery_test_overdue_claimed: False
```

Current counts are evidence values, not hard invariants. Print exact counts, incident source status, source artifacts, and truncation state. Any missing module/order key or parse failure must remain a failed verification rather than being interpreted as zero/absence.

## After installed-content acceptance

1. Record exact read-only verification output.
2. Pull the latest branch head.
3. Run the full repository suite without `sudo`.
4. Verify exact five-file branch scope versus accepted main.
5. Create a non-draft PR, verify changed filenames and mergeability, and squash-merge only if all gates remain green.

## Trust boundary

No secret, credential, raw Terraform state, or raw Kubernetes Secret value is projected. Incident candidates remain candidates, not confirmed incidents or root-cause conclusions. Backup UNKNOWN remains distinct from UNPROTECTED, and restore verification UNKNOWN is not a recovery-overdue claim. No remediation is implied by this runtime integration.
