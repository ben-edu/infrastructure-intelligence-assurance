# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #73: ad652d64d6206b0e4ff33ea511f0499447d8c45f
active branch: agent/m6-terraform-runtime-artifact-source
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6: ACTIVE
mutation_allowed: false
management host: mgmt-automation
bounded infrastructure repository: /home/ben/projects/afpa-infra-rebuild
```

## Accepted Milestone 6 — Terraform prior evidence

Reports:

```text
docs/reports/2026-08-29-m6-terraform-declared-state-inventory.md
docs/reports/2026-08-29-m6-terraform-root-module-declared-coverage.md
docs/reports/2026-08-29-m6-terraform-execution-declaration-discovery.md
```

Accepted bounded Terraform structure:

```text
root candidates: terraform/environments/bm1, terraform/environments/bm2
module directory: terraform/modules/proxmox_vm
backend blocks observed in Git-tracked .tf: 0
provider type: proxmox
resource type: proxmox_vm_qemu
execution declaration files in bounded workflow/script source: 0
managed_resource_coverage_status: DECLARED_CONFIGURATION_ONLY
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

No Terraform state or real tfvars content has entered evidence/AI context.

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

Latest accepted full suite before PR #73:

```text
387 passed in 1.76s
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

## Merge-ready Milestone 6 — Terraform runtime-artifact source discovery

Implementation:

```text
scripts/discovery/m6_terraform_runtime_artifact_source_discovery.py
tests/test_terraform_runtime_artifact_source_discovery.py
```

Report:

```text
docs/reports/2026-08-29-m6-terraform-runtime-artifact-source-discovery.md
```

Accepted validation and live evidence:

```text
focused tests: 4 passed in 0.06s
discovery_rc: 0
source_mode: BOUNDED_TERRAFORM_ROOT_FILESYSTEM_METADATA_ONLY
source_status: COMPLETE
root_directories_expected: 2
root_directories_observed: 2
metadata_failures: 0
symlink_entries_skipped: 0
```

Per-root accepted metadata:

```text
bm1: working_directory=OBSERVED, state_artifact=OBSERVED, state_backup_artifact=OBSERVED, workspace_state_directory=NONE_OBSERVED, workspace_directories=0, backend_metadata_candidate=NONE_OBSERVED, workspace_selection_metadata_candidate=NONE_OBSERVED, saved_plan_candidates=0
bm2: working_directory=OBSERVED, state_artifact=OBSERVED, state_backup_artifact=OBSERVED, workspace_state_directory=NONE_OBSERVED, workspace_directories=0, backend_metadata_candidate=NONE_OBSERVED, workspace_selection_metadata_candidate=NONE_OBSERVED, saved_plan_candidates=0
```

Aggregate accepted metadata:

```text
working_directories_observed: 2
top_level_state_artifacts_observed: 2
top_level_state_backup_artifacts_observed: 2
workspace_state_directories_observed: 0
workspace_directories_observed: 0
backend_metadata_candidates_observed: 0
workspace_selection_metadata_candidates_observed: 0
saved_plan_artifact_candidates_observed: 0
runtime_artifact_source_status: RUNTIME_ARTIFACT_METADATA_OBSERVED
```

Repository-wide gate:

```text
391 passed in 5.58s
```

Interpretation boundary:

```text
runtime artifact metadata != state-backed coverage
state artifact existence != current/authoritative/complete state
state backup artifact existence != recovery validation
saved plan metadata != plan outcome
working directory metadata != successful init/apply
filesystem absence != absence of remote state or external CI execution
```

Preserve:

```text
state_backed_coverage_status: UNKNOWN
live_resource_coverage_status: UNKNOWN
plan_result_status: UNKNOWN
apply_result_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
state_backed_coverage_claims: 0
drift_claims: 0
destructive_change_claims: 0
```

## Trust boundary

```text
mutation_allowed: False
terraform_cli_invoked: False
terraform_state_contents_inspected: False
terraform_plan_contents_inspected: False
terraform_tfvars_contents_inspected: False
provider_api_invoked: False
```

Only filesystem metadata for the two accepted Terraform roots and generic runtime-artifact names was inspected. State/state-backup/backend/workspace/plan/tfvars contents, resource addresses, workspace names, provider values, endpoints, credentials, raw commands, and sensitive connection strings were not opened or projected.

## Merge gate

```text
focused tests: PASS — 4 passed in 0.06s
live discovery: PASS — discovery_rc=0
full repository suite: PASS — 391 passed in 5.58s
```

## Exact next step

1. Inspect changed-file scope and ensure no temporary/debug/placeholder files exist.
2. Create/inspect a non-draft PR and squash-merge when clean.
3. Carry the new accepted `main` SHA into a new branch.
4. Start a tightly bounded **Terraform local-state safe structural aggregation** slice.
5. That slice may parse `terraform.tfstate` only process-locally on `mgmt-automation` and project aggregate non-sensitive structure only.

Permitted future state projection should be limited to:

```text
per-root parse/schema status
aggregate managed-resource block count
aggregate data-resource block count
aggregate instance count
aggregate resource-type categories/counts
```

Explicitly prohibit projection of:

```text
state values or raw JSON
resource addresses or resource names
instance keys/indexes
outputs or output values
serial/lineage identifiers
provider configuration strings/aliases
endpoints, credentials, sensitive attributes
private connection data
```

A successful structural state aggregation still does not establish live resource coverage, current state, plan/apply success, drift, or destructive-change status. Those remain `UNKNOWN` until separately verified.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- runtime artifact metadata is not state-backed coverage;
- bounded absence is not universal absence;
- `FAILED_TO_OBSERVE`/`INCOMPLETE` is not negative evidence;
- raw Terraform state/real tfvars and Ansible variable/Vault/credential material do not enter evidence/AI context;
- only explicitly safe aggregate state structure may enter evidence after a dedicated accepted collector projects it;
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
