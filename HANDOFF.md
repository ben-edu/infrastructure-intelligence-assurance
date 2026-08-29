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

Accepted bounded Terraform evidence:

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
declared-to-local-state structural relationship: DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH
matched declared/state resource-type blocks: 2/2
latest accepted full suite: 399 passed in 2.11s
```

Per-root accepted relationship:

```text
bm1: declared proxmox_vm_qemu blocks=1, state managed proxmox_vm_qemu blocks=1, comparison=DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH
bm2: declared proxmox_vm_qemu blocks=1, state managed proxmox_vm_qemu blocks=1, comparison=DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH
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

Interpretation boundary:

```text
structural match = limited declared-to-local-state structural relationship only
structural match != state freshness or authoritative state
structural match != live resource existence/coverage
structural match != plan/apply result
structural match != drift
structural match != destructive-change evidence
structural mismatch, if later observed, != drift without authoritative live verification
```

Managed state instance counts are intentionally not compared with declared resource-block counts.

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

## Active Milestone 6 slice — merge ready

Implementation:

```text
scripts/discovery/m6_terraform_declared_state_structural_coverage.py
tests/test_terraform_declared_state_structural_coverage.py
```

Report:

```text
docs/reports/2026-08-29-m6-terraform-declared-to-local-state-structural-coverage.md
```

Validation:

```text
focused tests: 4 passed in 0.06s
live discovery: discovery_rc=0
full repository suite: 399 passed in 2.11s
```

Trust boundary:

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

Only aggregate declared resource-type block counts and aggregate local-state managed resource-type block counts entered evidence. Raw HCL/state, resource or instance identity, state values, provider configuration, real tfvars, endpoints, credentials, and sensitive connection strings did not enter evidence output.

## Exact next step

1. Inspect changed-file scope and ensure no temporary/debug/placeholder files exist.
2. Create/inspect a non-draft PR and squash-merge when clean.
3. Carry the new accepted `main` SHA forward.
4. Reassess Milestone 6 against `03_DELIVERY_ROADMAP.md` and accepted evidence before creating another implementation branch.
5. Prefer a next slice only if it adds materially stronger independent read-only governance evidence.
6. Do not add probes merely to force state/live/plan/apply/drift/destructive or Ansible execution unknowns closed.

Potential remaining M6 gaps to evaluate, not automatically implement:

```text
Terraform: authoritative live/provider observation, plan/apply metadata, drift, destructive-change detection
Ansible: managed-host live coverage, execution outcomes, measurable configuration drift
Milestone-level closure: determine which gaps require future authorized runtime actions or evidence sources not currently available
```

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed/live state;
- local state structure is not live resource evidence;
- declared-to-local-state structural match is not freshness/live/drift evidence;
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
7. carry the new accepted `main` SHA into the next checkpoint.
