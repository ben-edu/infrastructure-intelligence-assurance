# Milestone 7 — Incident Operator Installed-Runtime Integration

Date: 2026-08-30
Status: PREPARED / FOCUSED VALIDATION PENDING
Mode: repository wiring for the existing five-minute collector; no deployment performed

## Goal

Install the accepted Kubernetes+backup+incident operator contract into the existing `infra-assurance-kubernetes.service` runtime without adding a service, timer, identity, datastore, Kubernetes RBAC, kubeconfig, or filesystem permission.

## Accepted baseline

Accepted main checkpoint:

```text
98cb3702faf6e23a15791ff32c36c7a7bd594c98
```

Accepted integration contract scope:

```text
KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

Accepted live no-write contract summary:

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

## Prepared runtime order

The existing collector order is preserved, with one final post-step added:

```text
incident_runtime
...
prometheus_rule_context_integration
< backup_assurance_foundation
< operator_attention_backup
< operator_attention_incident
```

`operator_attention_incident` consumes the same-run accepted Kubernetes+backup `operator-attention.json` plus the already-generated same-run `incident-candidates.json`, then atomically replaces `operator-attention.json/.md` with the accepted final scope.

## Runtime identity and sandbox

Unchanged:

```text
User=infra-assurance
Group=infra-assurance
PYTHONPATH=/opt/infra-assurance/src
NoNewPrivileges=true
ProtectHome=true
existing ReadWritePaths only
```

## Bounded deployment helper

`scripts/deploy-operator-attention-runtime.sh` is prepared to install only the accepted operator projection modules required by the existing unit:

```text
operator_attention.py
backup_operator_adapter.py
operator_attention_backup.py
incident_operator_adapter.py
operator_attention_incident.py
```

The helper also installs the existing systemd unit, runs `systemctl daemon-reload`, starts the existing service once, and verifies that the generated operator artifact has scope:

```text
KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

Dry-run remains the default. `--apply` must not be used without fresh explicit authorization.

The helper does not run `bootstrap-observer.sh`, change Kubernetes RBAC/kubeconfig, change Git source configuration, add services/timers, or broaden filesystem permissions.

## Prepared tests

```text
tests/test_operator_attention_incident_runtime_integration.py
```

The tests verify:

- same-run dependency ordering;
- preservation of the existing observability-before-backup invariant;
- backup-before-existing-operator-before-incident-operator ordering;
- unchanged `infra-assurance` identity and sandbox;
- bounded helper module set and final scope;
- reuse of existing artifact paths without a new service/timer.

## Mutation boundary

No runtime deployment or infrastructure mutation has been performed in this slice. Repository preparation does not imply deployment authorization.

## Next gate

Run focused repository tests. If they pass, run only the deployment helper in dry-run mode. Review the exact bounded plan before requesting any fresh deployment authorization.
