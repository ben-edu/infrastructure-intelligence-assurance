# Milestone 8 — Start Here

This document is the explicit handoff from completed Milestone 7 to Milestone 8.

## Prerequisites

Before starting M8:

1. Read Project Sources.
2. Read `docs/PROJECT_CONTINUITY.md`.
3. Read `HANDOFF.md` from current `main`.
4. Read `docs/reports/2026-08-30-m7-closure.md`.
5. Check for open project pull requests.
6. Do not reconstruct M7 from chat history.

## Accepted M7 outcome

Milestone 7 is complete within the accepted read-only operational-intelligence scope.

The installed operator runtime produces:

```text
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
mutation_allowed: False
runtime identity: infra-assurance
```

The platform has accepted paths for:

- current operator attention;
- recent change and drift context;
- explicit unknown/stale/failed evidence;
- backup/recovery assurance gaps without false protection claims;
- incident-candidate grouping without incident/root-cause promotion;
- task-scoped pre-change verification;
- post-change verification requirements;
- deterministic safest-next-action selection without execution.

Preserve these trust rules:

```text
DECLARED != OBSERVED
NONE_OBSERVED_IN_BOUNDED_SOURCE != universal absence
FAILED_TO_OBSERVE != negative evidence
UNKNOWN != false
backup UNKNOWN != UNPROTECTED
restore verification UNKNOWN != recovery test overdue
incident candidate != confirmed incident
incident candidate != root cause
SUPPRESSED != RESOLVED
recommendation != approval
mutation_allowed=false unless separately reviewed and explicitly authorized
```

## Do not reopen accepted M5/M6 UNKNOWNs without stronger evidence

Preserve:

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Preserve backup/recovery unknowns unless authoritative evidence becomes available:

```text
physical failure-domain independence
retention effectiveness
accepted RPO/RTO evaluation
restore verification
integrity verification
application/database-consistent backup evidence
```

Do not add weak probes merely to replace these UNKNOWNs with stronger labels.

## First M8 slice

Create a small read-only baseline branch:

```text
agent/m8-runtime-hardening-baseline
```

Goal:

```text
Establish an evidence-backed reliability and least-privilege baseline for the existing infra-assurance collector runtime before changing any hardening control.
```

Inspect repository declarations and current installed state for:

- `infra-assurance-kubernetes.service` and its timer;
- runtime `User` / `Group`;
- systemd sandbox directives such as `NoNewPrivileges`, `ProtectHome`, `ProtectSystem`, and explicit writable paths;
- artifact directory owner/group/mode boundaries;
- installed code path and write boundaries;
- timer cadence and potential overlap behavior;
- service timeout, restart, and failure propagation semantics;
- whether failures are externally visible or only discoverable by manual inspection;
- atomic-write expectations for generated evidence;
- platform evidence/history backup status, reported as OBSERVED/UNKNOWN rather than assumed.

## First M8 acceptance output

The first slice should produce a compact report that separates:

```text
DECLARED
OBSERVED
UNKNOWN
FAILED_TO_OBSERVE
INFERENCE
REQUIRES_CHANGE
```

It should identify the single smallest justified hardening change after the baseline.

Do not implement that change in the baseline slice unless it is repository-only and non-mutating. Any management-host unit, permission, scheduling, backup, RBAC, or infrastructure mutation requires a separate reviewed change and explicit authorization.

## Suggested initial repository scope

Keep the first slice small. Prefer:

```text
HANDOFF.md
docs/reports/<date>-m8-runtime-hardening-baseline.md
scripts/discovery/m8_runtime_hardening_baseline_probe.py
tests/test_m8_runtime_hardening_baseline.py
```

Add other files only if evidence shows they are necessary.

## Exact first action in a new tab

After reading the prerequisite documents, verify current `main`, verify there is no unresolved M7 PR, then create `agent/m8-runtime-hardening-baseline` from current accepted `main` and inspect the existing systemd/runtime declarations before writing any probe or proposing a mutation.
