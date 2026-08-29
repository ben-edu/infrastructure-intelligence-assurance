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
latest accepted full suite: 395 passed in 1.74s
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

Goal:

```text
Compare only aggregate non-sensitive declared resource-type block counts against aggregate local-state managed resource-type block counts per accepted Terraform root.
```

Relationship sources:

```text
declared side: safe Git-tracked Terraform resource-type counts by root directory
state side: process-local safe Terraform state resource-type block counts by root
```

Comparison rule:

```text
per root, compare resource-type -> resource-block-count maps
managed state instance count is NOT compared with declared resource-block count
```

Permitted projection:

```text
per-root declared resource block count
per-root local-state managed resource block count
per-root declared resource-type counts
per-root local-state managed resource-type counts
per-root structural match/mismatch status
aggregate matched resource-type block count
aggregate declared-to-local-state structural coverage status
```

Explicitly prohibited:

```text
raw HCL or raw Terraform state
resource names or addresses
instance keys/indexes or identities
state attribute values
outputs or output values
serial/lineage identifiers
provider configuration strings/aliases
real tfvars
endpoints, credentials, sensitive connection strings
```

Interpretation boundary:

```text
structural match != current or authoritative state
structural match != state freshness
structural match != live resource coverage
structural mismatch != drift
structural relationship != plan/apply result
structural relationship != destructive-change evidence
```

Preserve regardless of result:

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

Fail closed if either declared or local-state structural source is incomplete or an expected root cannot be safely related.

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m6-terraform-declared-state-coverage

python3 -m pytest -q \
  tests/test_terraform_declared_state_structural_coverage.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_terraform_declared_state_structural_coverage.py

echo "discovery_rc=$?"
```

Acceptance rules:

- focused tests must pass;
- both declared and state structural sources must be complete;
- both accepted roots must compare completely;
- only aggregate type/count relationships may be projected;
- no resource/instance identity or raw configuration/state may enter evidence output;
- mismatch must not be promoted to drift;
- match must not be promoted to live/state freshness or authoritative-state claims;
- no Terraform CLI/provider API/SSH/infrastructure mutation is allowed.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- runtime artifact metadata is not state-backed coverage;
- local state structure is not live resource evidence;
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
