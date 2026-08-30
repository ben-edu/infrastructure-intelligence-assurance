# Project Handoff

Project Sources remain authoritative. Read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #87: 292b8da942f2445d7bdb061f5c778b6861b6cd6f
active branch: agent/m7-planning-preflight-operator-context
Milestone 7: ACTIVE
management host: mgmt-automation
broader infrastructure mutation authorized: false
```

## Accepted installed operator runtime

The existing five-minute collector produces the accepted cross-domain operator projection under `infra-assurance`.

```text
scope: KUBERNETES_BACKUP_AND_INCIDENT_EXISTING_EVIDENCE_ONLY
mutation_allowed: False
runtime identity: infra-assurance
prometheus_rule_context_integration < backup_assurance_foundation < operator_attention_backup < operator_attention_incident
runtime-integration suite: 445 passed in 2.87s
```

Last accepted installed evidence snapshot before this slice:

```text
cluster_id: k3s-main
attention_now_total: 7
required_live_verification_total: 11
backup_assets_total: 37
backup_protection_unknown: 37
backup_restore_verification_unknown: 37
backup_unprotected_claims: 0
incident_candidates_total: 4
incident_active_candidates: 1
incident_suppressed_candidates: 3
incident_source_status: PARTIAL
```

Counts are observed evidence and may change; they are not hard runtime invariants.

## Existing planning architecture

Do not create a second pre-change pack implementation. Accepted planning artifacts already exist:

```text
docs/decisions/0004-task-scoped-planning-preflight.md
src/infra_assurance/planning_preflight.py
tests/test_planning_preflight.py
schemas/deployment-preflight.schema.json
```

The base preflight already separates facts, conflicts, inferences, unknowns, required live verification, a non-executable candidate plan, and post-change verification. It keeps `mutation_allowed=false`.

## Active slice — planning preflight operator context

Report:

```text
docs/reports/2026-08-30-m7-planning-preflight-operator-context.md
```

Goal:

```text
Enrich the accepted task-scoped deployment preflight with compact current operator attention so observability, backup assurance, incident candidates, and current task-scoped risk affect pre-change verification and the safest next action without duplicating the preflight architecture or authorizing execution.
```

Prepared module:

```text
src/infra_assurance/planning_preflight_operator.py
```

Prepared behavior:

```text
base build_deployment_preflight is preserved
accepted operator scope required
cluster mismatch fails closed
mutation_allowed=false required on both inputs
target-namespace attention/change/unknown context projected
PLATFORM or target-namespace incident candidates are task-relevant
unrelated namespace incident candidates are not promoted into task risk
ACTIVE overlapping candidate -> live verification, not incident/root-cause claim
SUPPRESSED != RESOLVED
backup UNKNOWN != UNPROTECTED
stateful post-change plan requires authoritative backup/recovery evidence before stronger protection claims
one deterministic safest_next_action is emitted, always mutation_allowed=false
```

Safest-next-action precedence:

```text
unknown/stale/failed/mismatched base evidence
> observed current-state conflict
> overlapping ACTIVE incident candidate
> relevant target-scope operator attention
> existing required live verification
> review non-executable candidate plan
```

## Focused validation — ACCEPTED

Executed without `sudo`:

```text
7 passed in 0.08s
7 passed in 0.04s
```

Both focused runs passed. Do not rerun them unless later code changes affect this slice.

Prepared safe probe:

```text
scripts/discovery/m7_planning_preflight_operator_probe.py
```

It reads existing protected evidence plus the repository hypothetical deployment request, performs no live infrastructure query, writes nothing, and prints only allowlisted compact planning/operator fields.

## Exact intended branch scope

```text
HANDOFF.md
docs/reports/2026-08-30-m7-planning-preflight-operator-context.md
scripts/discovery/m7_planning_preflight_operator_probe.py
src/infra_assurance/planning_preflight_operator.py
tests/test_planning_preflight_operator.py
```

No systemd, timer, runtime deployment, Kubernetes RBAC, kubeconfig, datastore, permission, AI-provider, remediation, or infrastructure mutation change is included.

## Exact next gate — SAFE NO-WRITE PROBE

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
git pull --ff-only origin agent/m7-planning-preflight-operator-context
sudo PYTHONPATH="$PWD/src" python3 scripts/discovery/m7_planning_preflight_operator_probe.py
```

The `sudo` scope is only to read protected existing evidence artifacts. The probe performs no live infrastructure query and writes no artifact.

If the probe is accepted, record its exact output and then run the full repository suite without `sudo`:

```bash
python3 -m pytest -q
```

Do not deploy this module in the current slice.

## Preserved M6 boundaries

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not reopen weak M6 probes.

## Trust invariants

- DECLARED != OBSERVED;
- NONE_OBSERVED_IN_BOUNDED_SOURCE != universal absence;
- FAILED_TO_OBSERVE != negative evidence;
- UNKNOWN != false;
- incident candidates are not confirmed incidents or root-cause conclusions;
- suppressed incident candidates are not resolved by implication;
- backup UNKNOWN protection is not UNPROTECTED;
- restore verification UNKNOWN is not a recovery-test-overdue claim;
- derived projections do not replace source evidence;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the planning projection;
- no remediation or infrastructure mutation is implied;
- generated operational semantics keep `mutation_allowed=false`.
