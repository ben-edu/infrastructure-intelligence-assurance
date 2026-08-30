# Milestone 7 — Incident Operator Installed-Runtime Integration

Date: 2026-08-30
Status: FOCUSED VALIDATION ACCEPTED / DRY-RUN ACCEPTED / DEPLOYMENT PENDING AUTHORIZATION
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

The helper does not run `bootstrap-observer.sh`, change Kubernetes RBAC/kubeconfig, change Git source configuration, add services/timers, or broaden filesystem permissions.

## Focused repository validation — ACCEPTED

Executed twice on `mgmt-automation`:

```text
11 passed in 0.09s
11 passed in 0.10s
```

The focused gate covered:

- preservation of the established observability-before-backup ordering invariant;
- `backup_assurance_foundation < operator_attention_backup < operator_attention_incident`;
- unchanged `infra-assurance` service identity and sandbox;
- bounded deployment helper module set;
- final expected scope `KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY`;
- reuse of the existing artifact paths without adding a service or timer.

## Deployment helper dry-run — ACCEPTED

Executed without `--apply`.

The dry-run stated the exact bounded mutation plan:

```text
- install accepted operator-attention modules under /opt/infra-assurance/src/infra_assurance/
- install the existing systemd unit definition
- run systemctl daemon-reload
- start the existing infra-assurance-kubernetes.service once
- verify operator-attention.json and operator-attention.md with the accepted Kubernetes+backup+incident scope
```

It also explicitly excludes:

```text
bootstrap-observer.sh
Kubernetes RBAC changes
kubeconfig changes
Git source configuration changes
new service/timer creation
filesystem permission broadening
```

Dry-run only: no systemd, installed runtime, service execution, or infrastructure mutation occurred.

## Authorization state

```text
broader infrastructure mutation authorized: false
incident operator runtime deployment authorized: false
```

A fresh explicit authorization is required before any `--apply` execution. Prior runtime deployment authorization does not cover this changed unit/module set.

## Mutation boundary

The proposed bounded deployment, if explicitly authorized, is limited to installing the accepted operator projection modules and corrected existing unit, running `daemon-reload`, starting the existing oneshot service once, and verifying the generated artifact scope/ownership.

It does not authorize remediation, Kubernetes changes, permission broadening, new services/timers, new datastores, or unrelated infrastructure mutation.

## Next gate

Obtain fresh explicit authorization for the bounded incident-operator runtime deployment. Do not run `scripts/deploy-operator-attention-runtime.sh --apply` before that authorization is recorded.
