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
accepted main after PR #63: 85301c6fa9725fc3439cbb13bd2c9325f5cfe458
active branch: agent/m6-terraform-execution-declaration-discovery
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

Controlled restore/integrity work remains deferred until explicitly authorized.

## Accepted Milestone 6 slice — Terraform declared-state inventory

Report:

```text
docs/reports/2026-08-29-m6-terraform-declared-state-inventory.md
```

Accepted state:

```text
Git-tracked .tf files: 15/15 scanned
root candidates: 2
module directories: 1
provider types: proxmox=2
resource types: proxmox_vm_qemu=2
backend blocks: 0
live_resource_coverage_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
```

## Accepted Milestone 6 slice — Terraform root/module declared coverage

Report:

```text
docs/reports/2026-08-29-m6-terraform-root-module-declared-coverage.md
```

Accepted structural result:

```text
terraform/environments/bm1
  direct declared proxmox_vm_qemu blocks: 1
  resolved local module: terraform/modules/proxmox_vm

terraform/environments/bm2
  direct declared proxmox_vm_qemu blocks: 1
  resolved local module: terraform/modules/proxmox_vm

terraform/modules/proxmox_vm
  declared resource blocks: 0
```

The two local module relationships are declared structure only. The two accepted resource blocks are declared directly in the two root candidates. Terraform state membership, runtime instance count, provider reachability, live resource existence, drift, and destructive-change status remain UNKNOWN.

## Active Milestone 6 slice — Terraform execution declaration discovery

Implementation:

```text
scripts/discovery/m6_terraform_execution_declaration_discovery.py
tests/test_terraform_execution_declaration_discovery.py
```

Goal: determine whether Git-tracked safe workflow/script text declares Terraform execution phases without executing Terraform or reading runtime secrets/state.

Candidate source classes are bounded to known CI/build files and safe script/workflow suffixes. Sensitive paths, `.tfvars`, Terraform state, `.terraform`, credentials, secrets, private-key material, and token-bearing path classes are excluded.

Safe projections:

```text
safe relative file identifier
Terraform phase categories only:
  init
  validate
  plan
  apply
  destroy
  refresh
  import
bounded gate keyword signal: true/false
phase file counts
phase token counts
```

Never print or persist:

```text
raw command lines
command arguments
environment values
credentials/tokens/passwords
endpoints/connection strings
Terraform plan/apply output
Terraform state
real tfvars
```

Semantics:

```text
phase token observed in Git-tracked workflow/script = DECLARATION_SIGNAL_OBSERVED
phase token absent from bounded source = NONE_OBSERVED_IN_BOUNDED_SOURCE
execution outcome = UNKNOWN
plan result = UNKNOWN
apply result = UNKNOWN
drift = UNKNOWN
destructive-change status = UNKNOWN
```

A gate keyword is a lexical declaration signal only. It does not prove that the gate protects a specific apply step unless future stronger structural evidence establishes that relationship.

No Terraform, Jenkins, GitHub Actions, or provider API is invoked by this discovery.

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m6-terraform-execution-declaration-discovery

python3 -m pytest -q \
  tests/test_terraform_execution_declaration_discovery.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_terraform_execution_declaration_discovery.py

echo "discovery_rc=$?"
```

Accept only bounded declaration signals. Do not infer execution success, drift, or destructive-change outcomes.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- declared execution workflow is not observed execution outcome;
- source artifacts and derived assurance remain separate;
- Terraform state and real tfvars do not enter evidence/AI context;
- raw commands and sensitive runtime values are not projected;
- no drift or destructive-change result is inferred without appropriate evidence;
- unknowns are not forced closed without authoritative evidence;
- no secrets, credentials, private keys, raw sensitive configuration, or sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
