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

Preserve:

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/success/idempotence/configuration drift: UNKNOWN
```

Accepted bounded Terraform governance evidence includes:

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

This first M7 slice is intentionally Kubernetes-existing-evidence only. It does not yet integrate M5 backup-assurance or M6 Terraform/Ansible evidence into one cross-domain inbox.

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

Derived sections:

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

The projection fails closed if required source artifacts cannot be read or do not resolve to exactly one matching cluster.

### Trust boundary

```text
mutation_allowed: false
scope: KUBERNETES_EXISTING_EVIDENCE_ONLY
live infrastructure query: none
source artifact write: none
new datastore: none
```

Only allowlisted metadata is projected. Do not project raw Kubernetes evidence values, raw diagnostics, Secret values, credentials, Terraform state, or sensitive connection strings.

Unknown/stale/failed evidence remains explicit; absence in the operator projection is not universal absence.

## Validation status

Focused tests under normal user context:

```text
5 passed in 0.05s
```

This focused result is accepted and does not need to be rerun for the current retry.

## Live attempt 1 — FAILED_TO_OBSERVE

Interactive user `ben` executed the probe from the repository.

```text
source_status: FAILED_TO_OBSERVE
failure_category: PermissionError
discovery_rc=2
```

Accepted interpretation:

```text
- NOT zero-attention evidence;
- NOT source-artifact absence evidence;
- the interactive user could not read at least one protected evidence artifact;
- no operator-attention conclusion is allowed.
```

## Live attempt 2 — FAILED_TO_OBSERVE before source loading

The probe was retried under the dedicated `infra-assurance` service identity:

```text
sudo -u infra-assurance env PYTHONPATH="$PWD/src" python3 "$PWD/scripts/discovery/m7_operator_attention_summary_probe.py"
```

Observed result:

```text
python3: can't open file '/home/ben/projects/infrastructure-intelligence-assurance/scripts/discovery/m7_operator_attention_summary_probe.py': [Errno 13] Permission denied
discovery_rc=2
```

Accepted interpretation:

```text
- NOT zero-attention evidence;
- NOT source-artifact absence evidence;
- this attempt failed before the probe code could execute;
- `infra-assurance` cannot traverse/read the repository source tree under `/home/ben`;
- do not weaken `/home/ben` or repository permissions;
- do not copy/install temporary code merely to make this validation pass.
```

The service-identity attempt is therefore an execution-packaging failure, not an evidence-source failure.

No accepted M7 report or PR may be created from either failed attempt.

## Exact next step

Use one narrowly scoped read-only privileged execution for validation only. This is justified because:

```text
- the repository code lives under a user-private path;
- the evidence artifacts are protected;
- the probe implementation has already been reviewed/tested to perform only reads of exactly the three bounded artifacts;
- the probe performs no live infrastructure query and no write;
- changing file permissions or copying/installing temporary code would create unnecessary state changes.
```

On `mgmt-automation`, first pull the handoff update:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git pull --ff-only origin agent/m7-operator-attention-summary-contract
```

Then run only the live probe with `sudo`:

```bash
sudo env \
  PYTHONPATH="$PWD/src" \
  python3 "$PWD/scripts/discovery/m7_operator_attention_summary_probe.py"
```

Then capture the return code in the normal interactive shell:

```bash
echo "discovery_rc=$?"
```

Do not use strict interactive shell mode.

Do not rerun the focused tests under sudo. Do not change artifact/repository permissions. Do not add ACLs. Do not create temporary copies of the code.

This root execution is a one-time validation packaging workaround only; it is not the intended long-term M7 runtime model. If the contract is later integrated into the installed five-minute runtime, it must run from the normal installed package/runtime path under the existing `infra-assurance` identity.

Acceptance rules for the privileged retry:

- all three bounded artifacts must load successfully;
- all three artifacts must resolve to one matching cluster;
- no live infrastructure query or mutation may occur;
- only allowlisted summary/metadata may be projected;
- source failures must remain `FAILED_TO_OBSERVE`, never zero-attention evidence;
- live output is valid only within `KUBERNETES_EXISTING_EVIDENCE_ONLY` scope;
- successful root execution does not expand future runtime privileges.

If the retry succeeds, create an accepted report, run the full repository suite because reusable implementation/tests changed, inspect exact five-file scope after report creation (`HANDOFF.md`, report, implementation, probe, tests), then PR/squash-merge.

If it still fails, preserve `FAILED_TO_OBSERVE` and fix only the specific packaging/source assumption revealed by the failure.

## Next M7 direction after this slice

Do not jump directly to a dashboard.

After this contract is accepted, choose the smaller of:

1. integrate the projection into the existing five-minute artifact generation path; or
2. add one additional cross-domain evidence adapter for already accepted M5/M6 assurance signals.

Choose only a step that materially reduces operator cognitive load.

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
