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

Preserve:

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Do not resume weak M6 probing merely to force UNKNOWNs closed.

Accepted bounded Terraform governance evidence includes:

```text
configuration_plan_status: COMPLETE
configuration_action_counts: NONE_OBSERVED
destructive_change_status: NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN
state_tracked_refresh_drift_status: STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED
refresh_only_action_counts: update=6 (bm1=2, bm2=4)
```

This remains bounded state-tracked drift only, not universal infrastructure drift.

Latest accepted full suite before the active M7 slice:

```text
405 passed in 1.79s
```

## Active Milestone 7 — operator attention summary contract

Goal:

```text
Build the smallest read-only operator-facing projection that reduces cognitive load using existing evidence only.
```

Implementation:

```text
src/infra_assurance/operator_attention.py
scripts/discovery/m7_operator_attention_summary_probe.py
tests/test_operator_attention.py
```

Accepted report:

```text
docs/reports/2026-08-29-m7-operator-attention-summary-contract.md
```

Existing source artifacts only:

```text
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/context.json
/var/lib/infra-assurance/evidence/change-context.json
```

No new infrastructure query, collector identity, datastore, or source of truth is introduced.

Projection scope:

```text
KUBERNETES_EXISTING_EVIDENCE_ONLY
```

Derived sections:

```text
attention_now
recent_changes
unknowns
required_live_verification
```

## Validation — ACCEPTED PENDING FULL SUITE

Focused tests:

```text
5 passed in 0.05s
```

### Rejected/incomplete live attempts

Attempt 1 as interactive user `ben`:

```text
source_status: FAILED_TO_OBSERVE
failure_category: PermissionError
discovery_rc=2
```

Do not reuse as zero-attention or source-absence evidence.

Attempt 2 under `infra-assurance` from the repository under `/home/ben`:

```text
python3: can't open file '/home/ben/projects/infrastructure-intelligence-assurance/scripts/discovery/m7_operator_attention_summary_probe.py': [Errno 13] Permission denied
discovery_rc=2
```

This failed before the code executed because the service identity cannot traverse the user-private repository path. Do not weaken permissions or reuse this as evidence-source failure.

### Accepted live attempt

A one-time privileged read-only validation was used because the repository source tree and protected evidence artifacts are under incompatible Unix access boundaries. This is validation packaging only and is not the intended runtime model.

Accepted output:

```text
discovery_rc=0
source_status: COMPLETE
source_artifacts_loaded: 3
cluster_id: k3s-main
scope: KUBERNETES_EXISTING_EVIDENCE_ONLY

workloads_total: 68
workloads_with_attention: 3
attention_now_total: 2
recent_changes_total: 0
unknowns_total: 0
required_live_verification_total: 0
```

Accepted attention projection:

```text
source=topology
code=SERVICE_SELECTOR_MULTIPLE_CONTROLLER_MATCHES
severity=AMBIGUOUS
subject=Service/monitoring/loki-headless

source=drift
code=DECLARED_OBSERVED_DRIFT
severity=DRIFT
subject=Ingress/validation/nginx-validation
```

Truncation:

```text
max_items_per_section: 20
attention_now_truncated: False
recent_changes_truncated: False
unknowns_truncated: False
required_live_verification_truncated: False
```

Interpretation:

```text
- the three bounded source artifacts loaded successfully and target k3s-main;
- the operator-facing projection contains two deduplicated current attention items;
- workloads_with_attention=3 is the inventory-level workload count and is not required to equal attention_now_total=2;
- recent_changes=0, unknowns=0, and required_live_verification=0 are bounded absence only within the currently loaded source artifacts and their freshness/trust boundaries;
- no remediation or mutation is implied by an attention item.
```

## Trust boundary

```text
mutation_allowed: false
live_infrastructure_query_performed: false
source_artifacts_written: false
new_datastore_used: false
raw_source_artifacts_projected: false
secrets_or_credentials_projected: false
```

Only allowlisted summary and compact metadata are projected. Raw Kubernetes evidence values, arbitrary resource values, raw diagnostics, credentials, Secret values, Terraform state, and sensitive connection strings do not enter the projection.

The successful root execution is a one-time validation workaround only. Future runtime integration must use the installed package/runtime path under the existing `infra-assurance` service identity and must not broaden file permissions.

## Merge gate — PENDING FULL SUITE

Reusable implementation and tests changed, so run the repository-wide suite before PR/merge.

Exact next step on `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance
python3 -m pytest -q
```

Do not use strict interactive shell mode.

If the full suite passes:

1. record the exact pass count/time in this handoff and the report;
2. verify branch scope is exactly five files:
   - `HANDOFF.md`
   - `docs/reports/2026-08-29-m7-operator-attention-summary-contract.md`
   - `src/infra_assurance/operator_attention.py`
   - `scripts/discovery/m7_operator_attention_summary_probe.py`
   - `tests/test_operator_attention.py`
3. ensure no temporary/debug/placeholder files exist;
4. create/inspect a non-draft PR;
5. verify changed filenames and mergeability;
6. squash-merge and carry the new accepted `main` SHA into the next checkpoint.

## Next smallest useful M7 step after merge

Prefer integration of this accepted contract into the existing five-minute artifact generation path before adding a dashboard or broad cross-domain inbox.

Target derived artifacts:

```text
/var/lib/infra-assurance/evidence/operator-attention.json
/var/lib/infra-assurance/evidence/operator-attention.md
```

The integration must:

```text
run from the installed package/runtime path under infra-assurance
reuse existing generated evidence only
remain read-only against infrastructure
preserve failed/stale/unknown source semantics
avoid a new datastore or source of truth
avoid broad dashboard construction
```

Only after this integration is accepted should the project decide whether a small cross-domain adapter for accepted M5/M6 assurance signals is the next useful step.

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
