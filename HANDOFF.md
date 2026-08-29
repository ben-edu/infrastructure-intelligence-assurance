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
latest accepted full suite before active slice: 399 passed in 2.11s
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
Terraform read-only plan first attempt refresh_only_actions=NONE_OBSERVED: REJECTED AS ACTION-ABSENCE EVIDENCE because the parser did not yet classify resource_drift events; its successful rc=2 change signal remains accepted
```

## Active slice — Terraform read-only plan evidence

Implementation:

```text
scripts/discovery/m6_terraform_readonly_plan_evidence.py
tests/test_terraform_readonly_plan_evidence.py
```

Report:

```text
docs/reports/2026-08-29-m6-terraform-readonly-plan-evidence.md
```

Two modes per root:

```text
configuration_vs_state: terraform plan -refresh=false
refresh_only: terraform plan -refresh-only
```

Safety behavior:

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

Raw plan/diagnostics, resource identities, state/tfvars/provider values, endpoints, credentials, and sensitive connection strings are not projected.

## Accepted validation and live evidence

Focused tests after parser correction:

```text
6 passed in 0.07s
```

Accepted live retry:

```text
discovery_rc=0
source_mode: TERRAFORM_READONLY_CONFIGURATION_AND_REFRESH_ONLY_PLAN_JSON
source_status: COMPLETE
roots_expected: 2
roots_configuration_plan_complete: 2
roots_refresh_only_plan_complete: 2
```

Per-root accepted evidence:

```text
bm1:
  configuration_plan=COMPLETE_NO_CHANGES
  configuration_exit_code=0
  configuration_actions=NONE_OBSERVED
  refresh_only_plan=COMPLETE_CHANGES_OBSERVED
  refresh_only_exit_code=2
  refresh_only_actions=update=2
  destructive_change_status=NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN
  state_tracked_drift_signal_status=STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED

bm2:
  configuration_plan=COMPLETE_NO_CHANGES
  configuration_exit_code=0
  configuration_actions=NONE_OBSERVED
  refresh_only_plan=COMPLETE_CHANGES_OBSERVED
  refresh_only_exit_code=2
  refresh_only_actions=update=4
  destructive_change_status=NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN
  state_tracked_drift_signal_status=STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED
```

Aggregate accepted evidence:

```text
configuration_action_counts: NONE_OBSERVED
refresh_only_action_counts: update=6
configuration_plan_status: COMPLETE
state_tracked_refresh_drift_status: STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED
destructive_change_status: NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN
```

Repository-wide regression gate:

```text
405 passed in 1.79s
```

Accepted interpretation:

```text
- configuration_vs_state has no changes for both roots;
- no configuration-driven destructive proposal was observed in the complete bounded configuration plans;
- refresh-only provider observation reported state-tracked drift update signals in both roots;
- aggregate refresh-only drift actions: update=6 (bm1=2, bm2=4);
- this is bounded state-tracked drift evidence only, not universal infrastructure drift;
- resource/attribute identity is intentionally unknown/unprojected;
- apply result, full live-resource coverage, and state-backed coverage remain UNKNOWN.
```

Terraform machine-readable UI event separation is respected:

```text
configuration action counts <- planned_change events only
refresh-only drift action counts <- resource_drift events only
```

Resource identities are discarded before projection.

## Trust boundary

```text
mutation_allowed: False
terraform_apply_invoked: False
terraform_state_locking_allowed: False
saved_plan_written: False
raw_plan_output_projected: False
raw_diagnostics_projected: False
resource_addresses_projected: False
resource_names_projected: False
state_values_projected: False
tfvars_values_projected: False
provider_read_observation_allowed: True
```

Terraform stdout/stderr remained process-local. No raw plan JSON, diagnostics, resource identity, state/tfvars/provider values, endpoints, credentials, or sensitive connection strings entered evidence.

No Terraform apply/import/state mutation command, SSH connection, repository mutation, or infrastructure mutation was performed. Provider reads during refresh-only planning were observation-only.

## Merge gate — READY

Focused tests, accepted live retry, and full repository suite all passed.

Before merge:

1. inspect branch/PR scope and confirm exactly `HANDOFF.md`, report, implementation, and tests;
2. ensure no temporary/debug/placeholder files exist;
3. create a non-draft PR;
4. verify changed filenames and mergeability;
5. squash-merge;
6. carry the new accepted `main` SHA into the next checkpoint.

## Post-merge reassessment rule

Do not automatically add another probe.

Remaining stronger M6 gaps after this slice:

```text
Terraform apply outcome: UNKNOWN
Terraform full live-resource coverage/state authority: UNKNOWN
Ansible live managed-host coverage: UNKNOWN
Ansible execution outcome/idempotence/drift: UNKNOWN
```

The accepted evidence already provides:

```text
Terraform declared-state inventory and root/module coverage
Terraform execution declaration discovery
Terraform local runtime-artifact metadata
Terraform local-state aggregate structure
Terraform declared-to-local-state structural relationship
Terraform bounded configuration plan metadata
Terraform destructive-proposal detection
Terraform bounded state-tracked refresh drift signal
Ansible declared inventory/playbook/role coverage
Ansible execution declaration/source discovery
bounded Jenkins/Ansible relationship closure
```

After merge, reassess Milestone 6 against `03_DELIVERY_ROADMAP.md` and the accepted reports. Prefer milestone closure with explicit preserved UNKNOWNs if the remaining gaps require mutation, unavailable authoritative sources, or materially stronger access. Do not add weak probes merely to force UNKNOWNs closed.

## Trust invariants

- infrastructure interaction remains read-only;
- declared/local state is not universal live truth;
- provider reads are observation-only;
- bounded state-tracked drift is not universal drift;
- complete configuration no-change is not a provider/live drift check;
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
