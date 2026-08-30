# Milestone 7 — Incident Operator Installed-Runtime Integration

Date: 2026-08-30
Status: INSTALLED RUNTIME VERIFIED / FINAL FULL-SUITE PENDING
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

## Runtime wiring

Required and now observed installed order:

```text
prometheus_rule_context_integration
< backup_assurance_foundation
< operator_attention_backup
< operator_attention_incident
```

The final incident post-step consumes the same-run Kubernetes+backup `operator-attention.json` plus the same-run `incident-candidates.json`, then atomically writes the final projection back to the existing `operator-attention.json/.md` paths.

Runtime identity and sandbox remain unchanged:

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

Dry-run stated the exact bounded mutation plan and explicitly excluded bootstrap, Kubernetes RBAC/kubeconfig changes, Git source configuration changes, new service/timer creation, and filesystem permission broadening.

## Authorization — ACCEPTED AND BOUNDED

Fresh explicit user authorization was granted on 2026-08-30 for this bounded deployment only.

```text
broader infrastructure mutation authorized: false
incident operator runtime deployment authorized: true
```

Authorization covered only installing the accepted five operator projection modules and prepared existing unit, running `daemon-reload`, starting the existing oneshot once, and verifying generated artifact ownership/scope. It did not authorize remediation, Kubernetes mutation, permission broadening, new services/timers/datastores, bootstrap, or unrelated infrastructure mutation.

## Authorized bounded deployment — EXECUTED / HELPER GATE ACCEPTED

Observed helper output:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
runtime_scope=KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

## Installed order and artifact verification — ACCEPTED

A separate read-only verification inspected the installed unit and protected generated JSON artifact.

Observed installed order:

```text
observability_before_backup: True
backup_before_operator_backup: True
operator_backup_before_incident: True
correct_order: True
```

Observed service identity and sandbox:

```text
user_infra_assurance: True
group_infra_assurance: True
no_new_privileges: True
protect_home: True
```

Observed artifact ownership:

```text
owner: infra-assurance
group: infra-assurance
```

Observed contract:

```text
operator_attention_version: 0.1
cluster_id: k3s-main
mutation_allowed: False
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
source_artifacts: inventory.json,context.json,change-context.json,backup-assurance.json,incident-candidates.json
```

Observed current summary:

```text
workloads_total: 68
workloads_with_attention: 3
attention_now_total: 7
recent_changes_total: 0
unknowns_total: 0
required_live_verification_total: 11
backup_assets_total: 37
backup_protection_unknown: 37
backup_restore_verification_unknown: 37
backup_unprotected_claims: 0
incident_candidates_total: 4
incident_active_candidates: 1
incident_suppressed_candidates: 3
incident_unknown_candidates: 0
incident_candidates_with_related_warning_events: 1
incident_candidates_requiring_live_verification: 2
```

Incident trust:

```text
incident_source_status: PARTIAL
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
```

Backup trust:

```text
unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
authoritative_backup_evidence_required_for_unprotected: True
```

Truncation:

```text
attention_now_truncated: False
required_live_verification_truncated: False
incident_candidates_truncated: False
```

## Interpretation

The installed runtime verification passes all hard trust and ordering conditions. The current evidence differs from the earlier pre-deployment no-write snapshot: incident candidates remain four total, but the current observed states are one ACTIVE and three SUPPRESSED, with two candidates currently requiring live verification and an overall verification total of 11.

These count changes are observed evidence changes, not regressions. `SUPPRESSED` is not treated as `RESOLVED`, and the incident source remains `PARTIAL`; therefore the current candidate set is not a universal negative-evidence statement. Counts must not be hard-coded as runtime invariants.

Backup assurance semantics remain unchanged: UNKNOWN protection is not UNPROTECTED, and UNKNOWN restore verification is not a recovery-test-overdue claim.

## Mutation boundary

The authorized mutation was limited to the recorded management-host runtime deployment. No new service/timer, Kubernetes mutation, permission broadening, datastore change, bootstrap, or remediation was authorized or performed by this slice.

## Final remaining gate

Pull the latest branch head and run the full repository regression suite without `sudo`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-incident-operator-runtime-integration
python3 -m pytest -q
```

If the full suite passes:

1. record exact pass count/time;
2. verify exact five-file branch scope against accepted main `98cb3702faf6e23a15791ff32c36c7a7bd594c98`;
3. verify no temporary/debug/placeholder files;
4. create a non-draft PR;
5. verify changed filenames and mergeability;
6. squash-merge and carry the new accepted main SHA forward.

## Trust boundary

No secret, credential, raw Terraform state, or raw Kubernetes Secret value is projected. Incident candidates remain candidates, not confirmed incidents or root-cause conclusions. Suppressed candidates are not treated as resolved. Backup UNKNOWN remains distinct from UNPROTECTED, and restore verification UNKNOWN is not a recovery-overdue claim. No remediation is implied by this runtime integration.
