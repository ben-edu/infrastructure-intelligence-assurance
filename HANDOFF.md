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
installed runtime verification accepted: true
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

Accepted main baseline before this slice:

```text
98cb3702faf6e23a15791ff32c36c7a7bd594c98
```

## Accepted repository preparation

Focused wiring tests executed twice:

```text
11 passed in 0.09s
11 passed in 0.10s
```

Dry-run accepted. It covered only the bounded module/unit installation, `daemon-reload`, one execution of the existing oneshot service, and final artifact scope verification. It explicitly excluded bootstrap, Kubernetes RBAC/kubeconfig changes, Git source configuration changes, new services/timers, datastore changes, permission broadening, and remediation.

## Authorization — ACCEPTED AND BOUNDED

Fresh explicit user authorization was granted on 2026-08-30 for the bounded incident-operator runtime deployment only.

```text
broader infrastructure mutation authorized: false
incident operator runtime deployment authorized: true
```

## Authorized bounded deployment — ACCEPTED

Observed helper result:

```text
deployment_status=COMPLETE
service_result=success
operator_attention_json=OBSERVED
operator_attention_markdown=OBSERVED
runtime_identity=infra-assurance
runtime_scope=KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

## Installed order and artifact verification — ACCEPTED

Installed order:

```text
prometheus_rule_context_integration
< backup_assurance_foundation
< operator_attention_backup
< operator_attention_incident
```

Observed booleans:

```text
observability_before_backup: True
backup_before_operator_backup: True
operator_backup_before_incident: True
correct_order: True
```

Runtime identity/sandbox:

```text
user_infra_assurance: True
group_infra_assurance: True
no_new_privileges: True
protect_home: True
artifact owner: infra-assurance
artifact group: infra-assurance
```

Current installed contract:

```text
operator_attention_version: 0.1
cluster_id: k3s-main
mutation_allowed: False
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
source_artifacts: inventory.json,context.json,change-context.json,backup-assurance.json,incident-candidates.json
```

Current observed summary:

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

Current incident source/trust:

```text
incident_source_status: PARTIAL
candidate_is_confirmed_incident: False
candidate_is_root_cause: False
suppressed_means_resolved: False
live_verification_required_before_action: True
```

Current backup trust:

```text
unknown_is_not_unprotected: True
recovery_test_overdue_claimed: False
authoritative_backup_evidence_required_for_unprotected: True
```

Current truncation:

```text
attention_now_truncated: False
required_live_verification_truncated: False
incident_candidates_truncated: False
```

Interpretation:

```text
installed order accepted: true
installed runtime identity/sandbox accepted: true
final scope accepted: true
incident candidates confirmed incidents: false
root cause established: false
suppressed candidates treated as resolved: false
incident source completeness: PARTIAL
backup UNKNOWN treated as UNPROTECTED: false
```

The current counts differ from the earlier no-write contract snapshot: four candidates remain, but now one is ACTIVE and three are SUPPRESSED. This is an observed evidence change, not a regression. `SUPPRESSED != RESOLVED`. Counts are not hard runtime invariants.

## Exact next gate — FINAL FULL REPOSITORY SUITE

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-incident-operator-runtime-integration
python3 -m pytest -q
```

Do not use `sudo` for the repository suite and do not use strict interactive shell mode.

If the suite passes:

1. record exact pass count/time in this file and the active report;
2. compare branch against accepted main `98cb3702faf6e23a15791ff32c36c7a7bd594c98`;
3. require exactly the five intended files listed above;
4. verify no temporary/debug/placeholder files;
5. create a non-draft PR;
6. verify changed filenames and mergeability;
7. squash-merge and carry the new accepted main SHA forward.

If the suite fails, do not create a PR; preserve existing tests and trust contracts and investigate the smallest real regression.

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
- backup UNKNOWN protection is not UNPROTECTED;
- restore verification UNKNOWN is not a recovery-test-overdue claim;
- no remediation is implied;
- generated operational semantics keep `mutation_allowed=false`;
- the recorded deployment authorization was bounded to this incident-operator runtime deployment only.
