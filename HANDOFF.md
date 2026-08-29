# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #75: 3fddcee38aa033d2ce97d2848e6c6e72aee18707
active branch: agent/m6-terraform-declared-state-coverage
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6: ACTIVE
mutation_allowed: false
management host: mgmt-automation
bounded infrastructure repository: /home/ben/projects/afpa-infra-rebuild
```

## Accepted Milestone 6 — Terraform evidence

Reports:

```text
docs/reports/2026-08-29-m6-terraform-declared-state-inventory.md
docs/reports/2026-08-29-m6-terraform-root-module-declared-coverage.md
docs/reports/2026-08-29-m6-terraform-execution-declaration-discovery.md
docs/reports/2026-08-29-m6-terraform-runtime-artifact-source-discovery.md
docs/reports/2026-08-29-m6-terraform-local-state-safe-structure.md
docs/reports/2026-08-29-m6-terraform-declared-to-local-state-structural-coverage.md
```

Accepted bounded Terraform evidence before this slice:

```text
root candidates: terraform/environments/bm1, terraform/environments/bm2
module directory: terraform/modules/proxmox_vm
provider type: proxmox
declared resource type: proxmox_vm_qemu
local state artifacts observed: 2/2 roots
local states parsed complete: 2/2 roots
local-state managed resource blocks: 2
local-state managed instances: 6
local-state managed resource type counts: proxmox_vm_qemu=2
latest accepted full suite before this slice: 395 passed in 1.74s
```

Preserve:

```text
Terraform state-backed coverage: UNKNOWN
Terraform live resource coverage: UNKNOWN
Terraform plan result: UNKNOWN
Terraform apply result: UNKNOWN
Terraform drift: UNKNOWN
Terraform destructive-change status: UNKNOWN
```

## Accepted Milestone 6 — Ansible/Jenkins path

Jenkins-to-Ansible relationship path is closed within the current evidence boundary:

```text
relationship_source_status: NONE_OBSERVED_IN_BOUNDED_SOURCE
Ansible execution outcome/success/idempotence/drift: UNKNOWN
```

Do not add more Jenkins-to-Ansible relationship probes without materially stronger safe evidence.

Rejected observations that must not be reused:

```text
Jenkins API first connection attempt: NOT_ATTEMPTED / FAILED_TO_OBSERVE
Ansible-to-Jenkins first relationship scan: SOURCE_INCOMPLETE due one skipped candidate
```

## Active Milestone 6 — Terraform declared-to-local-state structural coverage

Implementation:

```text
scripts/discovery/m6_terraform_declared_state_structural_coverage.py
tests/test_terraform_declared_state_structural_coverage.py
```

Report:

```text
docs/reports/2026-08-29-m6-terraform-declared-to-local-state-structural-coverage.md
```

Accepted focused/live validation:

```text
focused tests: 4 passed in 0.06s
discovery_rc: 0
source_mode: DECLARED_GIT_TF_TO_LOCAL_STATE_SAFE_TYPE_COUNT_RELATIONSHIP
source_status: COMPLETE
declared_source_status: COMPLETE
state_source_status: COMPLETE
roots_expected: 2
roots_compared_complete: 2
```

Accepted per-root relationship:

```text
bm1: comparison_status=DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH, declared_resource_blocks=1, state_managed_resource_blocks=1, declared_resource_type_counts=proxmox_vm_qemu=1, state_managed_resource_type_counts=proxmox_vm_qemu=1, matched_resource_type_block_count=1
bm2: comparison_status=DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH, declared_resource_blocks=1, state_managed_resource_blocks=1, declared_resource_type_counts=proxmox_vm_qemu=1, state_managed_resource_type_counts=proxmox_vm_qemu=1, matched_resource_type_block_count=1
```

Aggregate accepted relationship:

```text
declared_resource_blocks: 2
state_managed_resource_blocks: 2
matched_resource_type_block_count: 2
declared_to_local_state_structural_coverage_status: DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH
```

Interpretation boundary:

```text
structural match = limited declared-to-local-state structural relationship evidence only
structural match != current or authoritative state
structural match != state freshness
structural match != state-backed coverage
structural match != live resource existence/coverage
structural match != plan/apply outcome
structural match != drift
structural match != destructive-change evidence
structural mismatch, if later observed, != drift without separate authoritative verification
```

Managed state instance counts are intentionally not compared with declared resource-block counts.

Preserve:

```text
state_backed_coverage_status: UNKNOWN
live_resource_coverage_status: UNKNOWN
plan_result_status: UNKNOWN
apply_result_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
drift_claims: 0
destructive_change_claims: 0
```

## Trust boundary

```text
mutation_allowed: False
terraform_cli_invoked: False
provider_api_invoked: False
raw_hcl_projected: False
raw_state_projected: False
resource_names_or_addresses_projected: False
instance_identity_projected: False
state_values_projected: False
tfvars_inspected: False
```

Only aggregate declared resource-type block counts and aggregate local-state managed resource-type block counts entered evidence.

Raw HCL/state, resource names/addresses, instance keys/identities, state values, outputs, serial/lineage, provider configuration, real tfvars, endpoints, credentials, and sensitive connection strings did not enter evidence output.

No Terraform CLI, provider API, SSH connection, repository mutation, or infrastructure mutation was performed.

## Merge gate — PENDING FULL SUITE

Focused tests and live relationship discovery passed. Because reusable implementation/tests changed, run the full repository suite before PR/merge.

## Exact next step

On `mgmt-automation` run only:

```bash
cd ~/projects/infrastructure-intelligence-assurance
python3 -m pytest -q
```

Do not use strict interactive shell mode.

If the full suite passes:

1. record the exact pass count in this handoff/report/PR;
2. inspect changed-file scope and ensure no temporary/debug/placeholder files exist;
3. create/inspect a non-draft PR and squash-merge when clean;
4. carry the new accepted `main` SHA into the next branch handoff;
5. reassess remaining Milestone 6 gaps before adding another probe;
6. do not promote this structural match to state freshness, authoritative ownership, live coverage, plan/apply, drift, or destructive-change evidence.

Prefer a next slice only if it adds materially stronger independent read-only evidence. Do not add weak probes merely to force remaining unknowns closed.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed/live state;
- runtime artifact metadata is not state-backed coverage;
- local state structure is not live resource evidence;
- declared-to-local-state structural match is not live/state freshness evidence;
- bounded absence is not universal absence;
- `FAILED_TO_OBSERVE`/`INCOMPLETE` is not negative evidence;
- raw Terraform state/real tfvars and Ansible variable/Vault/credential material do not enter evidence/AI context;
- only explicitly safe aggregate structure/relationship data may enter evidence;
- no drift, execution success, idempotence, compliance, or destructive-change result is inferred without authoritative evidence;
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
7. carry the new accepted `main` SHA into the next branch handoff.
