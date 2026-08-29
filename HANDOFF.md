# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, trust principles, and operating rules.

## Resume protocol

1. Read Project Sources.
2. Read `HANDOFF.md` from `main`.
3. Check open PRs in `ben-edu/infrastructure-intelligence-assurance`.
4. If an active project PR has a newer `HANDOFF.md`, prefer that branch version for execution state.
5. Read only the ADR, milestone doc, and report relevant to the active slice.
6. Prefer repository and live evidence over chat reconstruction.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #62: a92f18cd59e50818a5290a0a354eea7a07d47129
active branch: agent/m6-terraform-root-module-coverage
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6: ACTIVE
mutation_allowed: false
management host: mgmt-automation
```

## Milestone 5 boundary

Accepted closure report:

```text
docs/reports/2026-08-23-m5-read-only-discovery-closure.md
```

Do not create additional Milestone 5 probes merely to force preserved unknowns closed. Controlled restore/integrity work remains deferred until explicitly authorized.

## Accepted Milestone 6 slice — Terraform declared-state inventory

Report:

```text
docs/reports/2026-08-29-m6-terraform-declared-state-inventory.md
```

Accepted bounded result:

```text
focused tests: 4 passed in 0.42s
source_mode: GIT_TRACKED_TF_ONLY
source_status: COMPLETE
tracked_tf_files_returned: 15
tracked_tf_files_scanned: 15
terraform_directories_total: 3
root_candidates_heuristic: 2
module_directories_heuristic: 1
backend_blocks: 0
provider_blocks: 2
resource_blocks: 2
module_blocks: 2
provider_types: proxmox=2
resource_types: proxmox_vm_qemu=2
managed_resource_coverage_status: DECLARED_CONFIGURATION_ONLY
live_resource_coverage_status: UNKNOWN
drift_claims: 0
destructive_change_claims: 0
```

Directory inventory:

```text
terraform/environments/bm1 -> ROOT_CANDIDATE
terraform/environments/bm2 -> ROOT_CANDIDATE
terraform/modules/proxmox_vm -> MODULE_DIRECTORY
```

Configuration-derived resources remain DECLARED state only. Backend absence is bounded source absence only and does not establish absence of state/backend elsewhere.

## Accepted Milestone 6 slice — Terraform root/module declared coverage

Report:

```text
docs/reports/2026-08-29-m6-terraform-root-module-declared-coverage.md
```

Accepted tests:

```text
root/module discovery: 4 passed in 0.09s
resource-location probe: 2 passed in 0.07s
```

Accepted root/module relationships:

```text
terraform/environments/bm1
  module_blocks: 1
  resolved local module: terraform/modules/proxmox_vm
  resource types in resolved module: NONE_OBSERVED
  direct root resource types: proxmox_vm_qemu=1

terraform/environments/bm2
  module_blocks: 1
  resolved local module: terraform/modules/proxmox_vm
  resource types in resolved module: NONE_OBSERVED
  direct root resource types: proxmox_vm_qemu=1

terraform/modules/proxmox_vm
  declared resource types: NONE_OBSERVED
```

Summary:

```text
root_candidates_total: 2
module_blocks_total: 2
relationships_resolved: 2
roots_with_resolved_local_module: 2
roots_with_declared_resource_path_through_module: 0
direct_root_resource_blocks: 2
module_declared_resource_blocks: 0
live_resource_coverage_status: UNKNOWN
state_backed_coverage_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
```

The local module relationship is real declared structure, but the accepted `proxmox_vm_qemu` blocks are declared directly in `bm1` and `bm2`, not inside `terraform/modules/proxmox_vm`.

Do not infer runtime VM count from the two resource blocks. Meta-arguments, variable-driven expansion, state membership, live existence, and provider reachability remain outside the accepted evidence.

## Exact next step

Start the smallest useful Terraform execution-governance slice: **Git-tracked plan/apply declaration discovery**.

Goal: determine whether the bounded infrastructure repository declares Terraform execution workflows/scripts and whether they distinguish plan from apply, without executing Terraform and without reading secrets or runtime values.

Safe questions:

```text
Are Git-tracked CI/workflow/script files present that explicitly reference Terraform plan/apply/init/validate?
Which execution phases are declared by safe filename/structural command-token evidence?
Is apply declaration present, absent in bounded scope, or unknown?
Is any approval/gate signal safely observable from workflow structure?
```

Safety constraints:

- scan Git-tracked text only;
- exclude env/secret/credential/private-key/certificate/tfvars/state paths;
- do not print raw command lines or arguments;
- do not print environment values, credentials, endpoints, or connection strings;
- project only file identifier, execution token category, and bounded gate/approval metadata when structurally explicit;
- do not invoke Terraform, Jenkins, GitHub Actions, or provider APIs;
- do not infer successful plan/apply execution from declared workflow text;
- preserve drift and destructive-change results as UNKNOWN.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- declared execution workflow is not observed execution outcome;
- source artifacts and derived assurance remain separate;
- Terraform state and real tfvars do not enter evidence/AI context;
- provider/backend/module sensitive values are not projected;
- external module sources are not followed;
- no drift or destructive-change result is inferred without appropriate evidence;
- unknowns are not forced closed without authoritative evidence;
- no secrets, credentials, private keys, raw sensitive configuration, or sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
