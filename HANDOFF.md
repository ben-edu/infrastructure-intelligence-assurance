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

## Active Milestone 6 slice — Terraform root-to-module declared coverage

Implementation:

```text
scripts/discovery/m6_terraform_root_module_coverage.py
tests/test_terraform_root_module_coverage.py
```

Goal: determine whether each current Terraform root candidate has a safely resolvable local-module path to declared resource types, using Git-tracked `.tf` structure only.

Allowed safe projections:

```text
root directory identifier
module block count
resolved local-module relationship count
resolved local module directory identifier
reachable resource types and declaration counts
structural declared-resource-path status
```

Local module source values may be read in memory only for path resolution. They must never be printed or persisted. Only relative paths that normalize inside the bounded repository and point to a directory containing Git-tracked `.tf` files may be classified as `RESOLVED_LOCAL_MODULE`.

External/registry/git/URL module sources must not be followed. Resource instance names and module block names must not be projected.

Expected preserved states:

```text
live_resource_coverage_status: UNKNOWN
state_backed_coverage_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
```

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m6-terraform-root-module-coverage

python3 -m pytest -q \
  tests/test_terraform_root_module_coverage.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_terraform_root_module_coverage.py

echo "discovery_rc=$?"
```

Accept only structural declared-state relationships. Do not infer Terraform state membership, live resource existence, provider reachability, drift, or destructive-change status.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- source artifacts and derived assurance remain separate;
- Terraform state and real tfvars do not enter evidence/AI context;
- provider/backend/module sensitive values are not projected;
- external module sources are not followed;
- no drift or destructive-change result is inferred without appropriate evidence;
- unknowns are not forced closed without authoritative evidence;
- no secrets, credentials, private keys, raw sensitive configuration, or sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
