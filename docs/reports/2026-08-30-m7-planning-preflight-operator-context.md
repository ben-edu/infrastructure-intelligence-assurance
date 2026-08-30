# Milestone 7 — Planning Preflight Operator Context

Date: 2026-08-30
Status: PREPARED / FOCUSED VALIDATION PENDING
Mode: repository-only integration over existing evidence; no live infrastructure query or runtime deployment

## Goal

Enrich the already-accepted task-scoped Kubernetes deployment planning preflight with the accepted cross-domain operator-attention artifact so current observability, backup-assurance, and incident-candidate context can influence pre-change verification and the safest next action.

This slice does not create a second pre-change architecture. It wraps the accepted `planning_preflight.py` contract and preserves its existing evidence/conflict/unknown/readiness/candidate-plan/post-change semantics.

## Accepted baseline

Accepted main checkpoint:

```text
292b8da942f2445d7bdb061f5c778b6861b6cd6f
```

Accepted installed operator scope:

```text
KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
```

Existing planning contract:

```text
src/infra_assurance/planning_preflight.py
docs/decisions/0004-task-scoped-planning-preflight.md
```

The base preflight remains non-executable and keeps:

```text
mutation_allowed: False
```

## Prepared integration

New module:

```text
src/infra_assurance/planning_preflight_operator.py
```

The adapter:

- calls the existing `build_deployment_preflight` implementation;
- requires matching cluster identity;
- requires the accepted Kubernetes+backup+incident operator scope;
- fails closed if either input violates `mutation_allowed=false`;
- keeps incident candidates distinct from confirmed incidents and root causes;
- keeps `SUPPRESSED` distinct from `RESOLVED`;
- keeps backup UNKNOWN distinct from UNPROTECTED;
- projects only target-namespace or platform incident candidates into task context;
- ignores unrelated namespace incident candidates for task-scoped change risk;
- adds relevant target-namespace operator attention, recent changes, and unknowns;
- adds pre-change live verification for overlapping ACTIVE incident candidates and target-scope unknowns;
- adds post-change regeneration of operator attention;
- for stateful requests, requires authoritative backup/recovery evidence after the future change before describing the new state as protected or recoverable;
- adds one deterministic `safest_next_action` without executing it.

## Safest-next-action precedence

The prepared deterministic precedence is:

```text
1. unknown/stale/failed/mismatched base evidence
2. observed current-state conflict
3. ACTIVE incident candidate overlapping platform or target namespace
4. relevant target-namespace operator attention
5. existing required pre-change live verification
6. review the non-executable candidate plan
```

Every returned action retains:

```text
mutation_allowed: False
```

## Probe

Prepared safe no-write probe:

```text
scripts/discovery/m7_planning_preflight_operator_probe.py
```

It reads only:

```text
/var/lib/infra-assurance/evidence/kubernetes.json
/var/lib/infra-assurance/evidence/context.json
/var/lib/infra-assurance/evidence/topology.json
/var/lib/infra-assurance/evidence/operator-attention.json
examples/requests/hypothetical-app-deployment.json
```

The probe performs no live infrastructure query and writes no source/generated artifact.

It prints only compact allowlisted planning/operator context, verification codes/checks, safest-next-action metadata, trust booleans, and truncation state.

## Intended branch scope

```text
HANDOFF.md
docs/reports/2026-08-30-m7-planning-preflight-operator-context.md
scripts/discovery/m7_planning_preflight_operator_probe.py
src/infra_assurance/planning_preflight_operator.py
tests/test_planning_preflight_operator.py
```

No systemd, timer, RBAC, kubeconfig, filesystem-permission, datastore, runtime deployment, remediation, or AI-provider change is included.

## Exact next gate

Run focused tests without `sudo`:

```bash
python3 -m pytest -q tests/test_planning_preflight_operator.py
```

If focused validation passes, run the protected-artifact probe with privilege scoped only to reading existing evidence artifacts. Do not deploy this module in this slice.
