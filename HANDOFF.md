# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #76: 88c4458b59a9e24d92cd6d7671be15d6525d7120
active branch: agent/m6-terraform-readonly-plan-evidence
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6: ACTIVE
mutation_allowed: false
management host: mgmt-automation
bounded infrastructure repository: /home/ben/projects/afpa-infra-rebuild
```

## Accepted Milestone 6 baseline

Terraform accepted reports through PR #76:

```text
docs/reports/2026-08-29-m6-terraform-declared-state-inventory.md
docs/reports/2026-08-29-m6-terraform-root-module-declared-coverage.md
docs/reports/2026-08-29-m6-terraform-execution-declaration-discovery.md
docs/reports/2026-08-29-m6-terraform-runtime-artifact-source-discovery.md
docs/reports/2026-08-29-m6-terraform-local-state-safe-structure.md
docs/reports/2026-08-29-m6-terraform-declared-to-local-state-structural-coverage.md
```

Accepted Terraform baseline:

```text
roots: terraform/environments/bm1, terraform/environments/bm2
provider type: proxmox
declared resource type: proxmox_vm_qemu
local states parsed complete: 2/2 roots
local-state managed resource blocks: 2
local-state managed instances: 6
declared-to-local-state structural relationship: DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH
matched declared/state resource-type blocks: 2/2
latest accepted full suite: 399 passed in 2.11s
```

Preserve from prior slices:

```text
state_backed_coverage_status: UNKNOWN
live_resource_coverage_status: UNKNOWN
apply_result_status: UNKNOWN
```

Ansible/Jenkins path remains closed within current evidence boundary:

```text
relationship_source_status: NONE_OBSERVED_IN_BOUNDED_SOURCE
Ansible execution outcome/success/idempotence/drift: UNKNOWN
```

Do not add more Jenkins-to-Ansible probes without materially stronger safe evidence.

Rejected/failed observations not to reuse as negative evidence:

```text
Jenkins API first connection attempt: NOT_ATTEMPTED / FAILED_TO_OBSERVE
Ansible-to-Jenkins first relationship scan: SOURCE_INCOMPLETE due one skipped candidate
GitHub connector lookup of ben-edu/afpa-infra-rebuild returned 404 during gap reassessment; local /home/ben/projects/afpa-infra-rebuild remains the accepted bounded source
```

## Active slice — Terraform read-only plan evidence

Implementation:

```text
scripts/discovery/m6_terraform_readonly_plan_evidence.py
tests/test_terraform_readonly_plan_evidence.py
```

Two modes per root:

```text
configuration_vs_state: terraform plan -refresh=false
refresh_only: terraform plan -refresh-only
```

Common safety behavior:

```text
-input=false
-lock=false
-detailed-exitcode
-json
no -out
no apply/import/state mutation command
stdout/stderr captured process-locally only
provider reads allowed only for refresh-only observation
```

Raw plan/diagnostics, resource identities, state/tfvars/provider values, endpoints, credentials, and sensitive connection strings must never be projected.

## First live attempt — accepted signal, action classification incomplete

Focused tests before parser fix:

```text
5 passed in 0.06s
```

Live probe:

```text
discovery_rc=0
source_status=COMPLETE
roots_configuration_plan_complete=2
roots_refresh_only_plan_complete=2

bm1:
  configuration_plan=COMPLETE_NO_CHANGES
  configuration_exit_code=0
  configuration_actions=NONE_OBSERVED
  refresh_only_plan=COMPLETE_CHANGES_UNCLASSIFIED
  refresh_only_exit_code=2
  refresh_only_actions=NONE_OBSERVED
  destructive_change_status=NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN
  state_tracked_drift_signal_status=STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED

bm2:
  configuration_plan=COMPLETE_NO_CHANGES
  configuration_exit_code=0
  configuration_actions=NONE_OBSERVED
  refresh_only_plan=COMPLETE_CHANGES_UNCLASSIFIED
  refresh_only_exit_code=2
  refresh_only_actions=NONE_OBSERVED
  destructive_change_status=NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN
  state_tracked_drift_signal_status=STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED
```

Accepted interpretation of that first attempt:

```text
- configuration_vs_state has no changes in both roots;
- destructive proposal status is NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN for both roots;
- refresh-only returned Terraform detailed exit code 2 for both roots, so a successful non-empty refresh-only diff / bounded state-tracked drift change signal is observed;
- refresh_only_actions=NONE_OBSERVED from this first attempt MUST NOT be reused as evidence of no drift actions because the parser did not yet classify Terraform resource_drift events;
- apply/live-coverage/state-backed-coverage remain UNKNOWN.
```

Terraform machine-readable UI defines `resource_drift` as the event type for detected external changes; `planned_change` is a separate event type. Terraform `-detailed-exitcode` defines 2 as successful plan with changes. The collector was therefore corrected before merge to classify `resource_drift` action categories separately from `planned_change` categories.

## Parser correction prepared on active branch

The corrected parser:

```text
configuration_vs_state action counts <- planned_change events only
refresh_only action counts <- resource_drift events only
resource identities discarded before projection
recognized resource_drift actions aggregate only (normally update/delete)
rc=2 with no recognized applicable events remains COMPLETE_CHANGES_UNCLASSIFIED
```

Tests now include a guard that resource_drift update/delete events are aggregated while resource addresses are not retained/projected.

## Exact next step

On `mgmt-automation` retry after pulling the parser correction:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git pull --ff-only origin agent/m6-terraform-readonly-plan-evidence

python3 -m pytest -q \
  tests/test_terraform_readonly_plan_evidence.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_terraform_readonly_plan_evidence.py

echo "discovery_rc=$?"
```

Expected focused test count after the correction: 6 tests. Accept only actual runtime output.

Acceptance rules for retry:

- both modes must complete for both roots;
- no apply/import/state mutation/saved plan/state locking;
- raw Terraform output and sensitive values/identity remain process-local and unprojected;
- configuration plan no-change may support bounded absence of configuration-driven destructive proposals;
- refresh-only rc=2 supports a bounded state-tracked drift change signal;
- resource_drift action counts may classify only aggregate drift actions, not identities or changed attributes;
- apply result, full live-resource coverage, and state-backed coverage remain UNKNOWN;
- no universal infrastructure drift claim.

If retry succeeds, create an accepted report, update this handoff, run the full repository suite, inspect exact four-file scope, then PR/squash-merge. Reassess M6 after that instead of automatically adding another probe.

## Trust invariants

- infrastructure interaction remains read-only;
- declared/local state is not live truth;
- provider reads are observation-only;
- bounded state-tracked drift is not universal drift;
- `FAILED_TO_OBSERVE`/`INCOMPLETE` is not negative evidence;
- raw Terraform state/plan/real tfvars and Ansible Vault/credential material do not enter evidence/AI context;
- only explicitly safe aggregate structure/status data may enter evidence;
- no apply success or universal coverage claim is inferred without authoritative evidence;
- unknowns are not forced closed;
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
