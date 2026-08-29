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
accepted main after PR #61: 945a16af33c2f6a708dd53181a9a00a5971b58be
active branch: agent/m6-terraform-declared-inventory
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

Focused tests:

```text
4 passed in 0.42s
```

Accepted bounded discovery:

```text
source_mode: GIT_TRACKED_TF_ONLY
source_status: COMPLETE
tracked_tf_files_returned: 15
tracked_tf_files_scanned: 15
excluded_or_unsafe_paths: 0
read_or_decode_skips: 0
oversize_skips: 0
terraform_directories_total: 3
root_candidates_heuristic: 2
module_directories_heuristic: 1
backend_blocks: 0
provider_blocks: 2
resource_blocks: 2
data_blocks: 0
module_blocks: 2
variable_blocks: 19
output_blocks: 5
cloud_blocks: 0
workspaces_blocks: 0
managed_resource_coverage_status: DECLARED_CONFIGURATION_ONLY
live_resource_coverage_status: UNKNOWN
drift_claims: 0
destructive_change_claims: 0
discovery_rc: 0
```

Directory inventory:

```text
terraform/environments/bm1 -> ROOT_CANDIDATE, tf_files=6
terraform/environments/bm2 -> ROOT_CANDIDATE, tf_files=6
terraform/modules/proxmox_vm -> MODULE_DIRECTORY, tf_files=3
```

Safe declaration projection:

```text
backend_types: NONE_OBSERVED
provider_types: proxmox=2
resource_types: proxmox_vm_qemu=2
data_source_types: NONE_OBSERVED
```

Semantics:

```text
Terraform configuration resources: DECLARED state
live managed-resource coverage: UNKNOWN
Terraform state coverage: UNKNOWN
provider reachability: UNKNOWN
drift: UNKNOWN
plan/apply status: UNKNOWN
destructive-change status: UNKNOWN
```

`ROOT_CANDIDATE` and `MODULE_DIRECTORY` remain structural heuristics, not authoritative Terraform stack/workspace identities.

`backend_types: NONE_OBSERVED` is bounded source absence only. It does not prove no backend or state exists elsewhere or via Terraform defaults/runtime configuration.

## Exact next step

Create a bounded **Terraform root-to-module declared-coverage relationship**.

Goal: from Git-tracked `.tf` structure only, determine whether each current root candidate has a safely resolvable local-module path to declared resource types.

Allowed safe projections:

```text
root candidate directory
module block count
local module relationship: RESOLVED / NONE_OBSERVED / UNKNOWN
resolved local module directory identifier
resource types reachable through the resolved local module
structural declared-resource-path status
```

Safety rules:

- do not print module source values;
- do not print module block names;
- do not print resource instance names;
- resolve only relative local module paths that normalize inside the bounded Git-tracked repository;
- do not follow external/registry/git/URL module sources;
- do not read Terraform state or real tfvars;
- do not invoke Terraform CLI or provider APIs;
- do not convert structural declared coverage into live resource coverage.

Expected preserved states:

```text
live_resource_coverage_status: UNKNOWN
state_backed_coverage_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
```

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- source artifacts and derived assurance remain separate;
- Terraform state and real tfvars do not enter evidence/AI context;
- provider/backend/module sensitive values are not projected;
- no drift or destructive-change result is inferred without appropriate evidence;
- unknowns are not forced closed without authoritative evidence;
- no secrets, credentials, private keys, raw sensitive configuration, or sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
