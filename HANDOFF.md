# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #78: 779d60956730b915c8d929fbbb2841699a5caf1b
active branch: agent/m7-operator-attention-summary-contract
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6 overall: NOT COMPLETE
Milestone 6 current read-only governance phase: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES AND SAFE OBSERVATION PATHS
Milestone 7: ACTIVE
mutation_allowed: false
management host: mgmt-automation
```

## Accepted Milestone 6 closure

Closure report:

```text
docs/reports/2026-08-29-m6-read-only-governance-closure.md
```

Decision:

```text
Milestone 6 overall: NOT COMPLETE
current read-only governance phase: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES AND SAFE OBSERVATION PATHS
remaining stronger gaps: EXPLICITLY PRESERVED
mutation/stronger-access work: DEFERRED
```

Important preserved gaps:

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not resume weak M6 probing merely to force UNKNOWNs closed.

Accepted bounded Terraform drift evidence remains:

```text
configuration_plan_status: COMPLETE
configuration_action_counts: NONE_OBSERVED
destructive_change_status: NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN
state_tracked_refresh_drift_status: STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED
refresh_only_action_counts: update=6 (bm1=2, bm2=4)
```

This is bounded state-tracked drift only, not universal infrastructure drift.

Latest accepted full suite before M7:

```text
405 passed in 1.79s
```

## Active Milestone 7 — operator attention summary contract

Goal:

```text
Build the smallest read-only operator-facing projection that reduces cognitive load using existing evidence only.
```

This first M7 slice is intentionally Kubernetes-existing-evidence only. It does not yet integrate M5 backup-assurance reports or M6 Terraform/Ansible report evidence into one cross-domain inbox.

Implementation:

```text
src/infra_assurance/operator_attention.py
scripts/discovery/m7_operator_attention_summary_probe.py
tests/test_operator_attention.py
```

Existing source artifacts only:

```text
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/context.json
/var/lib/infra-assurance/evidence/change-context.json
```

No new infrastructure query, collector identity, datastore, or source of truth is introduced.

### Projection contract

The derived summary contains four sections:

```text
attention_now
recent_changes
unknowns
required_live_verification
```

Top-level summary counts:

```text
workloads_total
workloads_with_attention
attention_now_total
recent_changes_total
unknowns_total
required_live_verification_total
```

The projection is fail-closed when source artifacts do not resolve to exactly one matching cluster.

### Trust boundary

```text
mutation_allowed: false
scope: KUBERNETES_EXISTING_EVIDENCE_ONLY
live infrastructure query: none
source artifact write: none
new datastore: none
```

Only allowlisted metadata is projected from existing derived artifacts.

Do not introduce:

```text
raw Kubernetes evidence values
raw diagnostics
Secret values
credentials
Terraform state
sensitive connection strings
```

Unknown/stale/failed evidence remains explicit; absence in the operator projection is not universal absence.

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m7-operator-attention-summary-contract

python3 -m pytest -q \
  tests/test_operator_attention.py

PYTHONPATH=src python3 \
  scripts/discovery/m7_operator_attention_summary_probe.py

echo "discovery_rc=$?"
```

Do not use strict interactive shell mode.

Acceptance rules:

- focused tests must pass;
- all three existing artifacts must load successfully;
- all three artifacts must resolve to one matching cluster;
- no live infrastructure query or mutation may occur;
- only allowlisted summary/metadata may be projected;
- source failures must be `FAILED_TO_OBSERVE`, not zero-attention evidence;
- live output must be interpreted only within `KUBERNETES_EXISTING_EVIDENCE_ONLY` scope.

If accepted, create a report, run the full repository suite because reusable implementation/tests changed, inspect exact four-file scope, then PR/squash-merge.

## Next M7 direction after this slice

Do not jump directly to a dashboard.

After this contract is accepted, the next decision should be whether to:

1. integrate the projection into the existing five-minute artifact generation path; or
2. add one additional cross-domain evidence adapter for already accepted M5/M6 assurance signals.

Choose only the smaller step that materially reduces operator cognitive load.

## Trust invariants

- infrastructure interaction remains read-only;
- derived operator projections do not replace source evidence;
- stale/failed/unknown evidence remains explicit;
- bounded absence is not universal absence;
- no secret, credential, raw Terraform state, or raw Kubernetes Secret value enters the projection;
- no remediation or mutation is implied by an attention item;
- generated operational artifacts keep `mutation_allowed=false`.

## Continuity rule

At every accepted slice before merge:

1. create/update the accepted report when reusable evidence changed;
2. update `HANDOFF.md` with accepted SHA context, evidence, preserved unknowns, trust boundary, merge gate, and exact next step;
3. update roadmap/current-state/README only when milestone status, architecture, or user-facing project status materially changes;
4. ensure no temporary/debug/placeholder files remain;
5. run focused tests and a full repository suite when reusable implementation/contracts change materially;
6. inspect PR scope and mergeability and squash-merge when clean;
7. carry the new accepted `main` SHA into the next checkpoint.
