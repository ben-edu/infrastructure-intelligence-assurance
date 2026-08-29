# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #74: b8e584689b7b88ea08e2729f7bd481942fee96bf
active branch: agent/m6-terraform-local-state-structure
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
```

Accepted bounded Terraform evidence:

```text
root candidates: terraform/environments/bm1, terraform/environments/bm2
module directory: terraform/modules/proxmox_vm
provider type: proxmox
declared resource type: proxmox_vm_qemu
execution declaration files in bounded workflow/script source: 0
local top-level state artifacts observed by metadata: 2/2 roots
local state-backup artifacts observed by metadata: 2/2 roots
Terraform working directories observed: 2/2 roots
workspace-state directories observed: 0
backend metadata candidates observed: 0
workspace-selection metadata candidates observed: 0
saved plan candidates observed: 0
local states parsed complete: 2/2 roots
local-state managed resource blocks: 2
local-state managed instances: 6
local-state managed resource type counts: proxmox_vm_qemu=2
latest accepted full suite for this branch: 395 passed in 1.74s
```

Per-root local-state safe structure:

```text
bm1: managed_resource_blocks=1, managed_instances=2
bm2: managed_resource_blocks=1, managed_instances=4
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

Local state structure is not current-state, authoritative-state, coverage, or live-resource proof.

## Accepted Milestone 6 — Ansible/Jenkins path

Accepted reports include:

```text
docs/reports/2026-08-29-m6-ansible-declared-state-inventory.md
docs/reports/2026-08-29-m6-ansible-playbook-role-declared-coverage.md
docs/reports/2026-08-29-m6-ansible-execution-declaration-discovery.md
docs/reports/2026-08-29-m6-ansible-execution-outcome-source-discovery.md
docs/reports/2026-08-29-m6-jenkins-ansible-outcome-capability.md
docs/reports/2026-08-29-m6-jenkins-api-metadata-probe.md
docs/reports/2026-08-29-m6-ansible-jenkins-relationship-source-discovery.md
```

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

## Merge-ready Milestone 6 — Terraform local-state safe structural aggregation

Implementation:

```text
scripts/discovery/m6_terraform_local_state_structure.py
tests/test_terraform_local_state_structure.py
```

Validation:

```text
focused tests: 4 passed in 0.05s
live discovery: discovery_rc=0
full repository suite: 395 passed in 1.74s
```

Accepted live state structure:

```text
source_status: COMPLETE
roots_parsed_complete: 2
managed_resource_blocks: 2
managed_instances: 6
managed_resource_type_counts: proxmox_vm_qemu=2
state_structure_status: STRUCTURAL_AGGREGATE_OBSERVED
```

Trust boundary:

```text
raw_state_projected: False
state_values_projected: False
resource_addresses_projected: False
resource_names_projected: False
instance_keys_projected: False
outputs_projected: False
serial_or_lineage_projected: False
provider_configuration_projected: False
terraform_cli_invoked: False
provider_api_invoked: False
mutation_allowed: False
```

No raw Terraform state, state values, resource names/addresses, instance keys, outputs, serial/lineage, provider configuration, endpoints, credentials, or private connection data entered evidence output.

## Exact next step

1. Inspect branch/PR scope and ensure only `HANDOFF.md`, the accepted report, implementation, and tests changed.
2. Create/inspect a non-draft PR and squash-merge when clean.
3. Carry the new accepted `main` SHA into the next branch handoff.
4. Start a bounded **Terraform declared-to-local-state structural coverage** slice.
5. Compare only aggregate non-sensitive declared resource-type block counts against aggregate local-state managed resource-type block counts per accepted root.
6. Do not expose resource names, addresses, instance identities, state values, tfvars, provider configuration, endpoints, credentials, or raw state.

A successful structural relationship may establish only limited declared-to-local-state structural coverage. It must not be promoted to live resource coverage, state freshness, plan/apply success, drift, or destructive-change evidence.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- runtime artifact metadata is not state-backed coverage;
- local state structure is not live resource evidence;
- bounded absence is not universal absence;
- `FAILED_TO_OBSERVE`/`INCOMPLETE` is not negative evidence;
- raw Terraform state/real tfvars and Ansible variable/Vault/credential material do not enter evidence/AI context;
- only explicitly safe aggregate state structure may enter evidence after collector projection;
- no raw commands, arguments, environment values, credentials, host targets, console logs, job configuration bodies, build parameters, or sensitive connection strings enter evidence/AI context;
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
