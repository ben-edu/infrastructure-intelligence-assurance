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

## Accepted Milestone 6 — Terraform declared-state inventory

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

## Accepted Milestone 6 — Terraform root/module declared coverage

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

The local module relationships are declared structure only. Terraform state membership, runtime instance count, provider reachability, live resource existence, drift, and destructive-change status remain UNKNOWN.

## Accepted Milestone 6 — Terraform execution declaration discovery

Report:

```text
docs/reports/2026-08-29-m6-terraform-execution-declaration-discovery.md
```

Accepted corrected live result:

```text
focused tests: 4 passed in 0.09s
source_mode: GIT_TRACKED_SAFE_WORKFLOW_SCRIPT_TEXT_ONLY
source_status: COMPLETE
tracked_files_returned: 400
candidate_files_selected: 160
candidate_files_scanned: 160
read_or_decode_skips: 0
oversize_skips: 0
terraform_execution_signal_files: NONE_OBSERVED
terraform_signal_files: 0
phase_file_counts: NONE_OBSERVED
phase_signal_counts: NONE_OBSERVED
files_with_gate_signal: 0
```

Phase declaration status:

```text
init: NONE_OBSERVED_IN_BOUNDED_SOURCE
validate: NONE_OBSERVED_IN_BOUNDED_SOURCE
plan: NONE_OBSERVED_IN_BOUNDED_SOURCE
apply: NONE_OBSERVED_IN_BOUNDED_SOURCE
destroy: NONE_OBSERVED_IN_BOUNDED_SOURCE
refresh: NONE_OBSERVED_IN_BOUNDED_SOURCE
import: NONE_OBSERVED_IN_BOUNDED_SOURCE
```

Preserve:

```text
execution_outcome_status: UNKNOWN
plan_result_status: UNKNOWN
apply_result_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
```

The first live run exposed a gate-only false positive. The implementation was corrected so a file enters Terraform execution evidence only when at least one explicit Terraform phase token exists. Gate metadata is considered only for Terraform-signal files.

`NONE_OBSERVED_IN_BOUNDED_SOURCE` remains bounded negative evidence only; it is not proof that Terraform execution never occurs elsewhere or manually.

## Exact next step

Start the smallest useful Ansible slice: **Git-tracked Ansible declared inventory** for the known infrastructure repository.

Bounded source:

```text
/home/ben/projects/afpa-infra-rebuild
Git-tracked safe Ansible source only
```

First questions:

```text
Which inventory candidates are declared?
Which playbook candidates are declared?
Which role directories are declared?
Which host/group identifiers can be safely counted without exposing addresses or secrets?
What managed-host coverage can be stated from declarations only?
```

Exclude:

```text
Ansible Vault contents
vault passwords
inventory host addresses when sensitive
ansible_password / become_password / private keys
.env
secret/credential/token material
runtime facts
Ansible execution or SSH connections
```

Do not call declared inventory hosts `OBSERVED` managed hosts. Keep configuration declarations separate from execution outcomes and live state.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- declared execution workflow is not observed execution outcome;
- source artifacts and derived assurance remain separate;
- Terraform state and real tfvars do not enter evidence/AI context;
- Ansible Vault and credential material do not enter evidence/AI context;
- raw commands and sensitive runtime values are not projected;
- no drift or destructive-change result is inferred without appropriate evidence;
- unknowns are not forced closed without authoritative evidence;
- no secrets, credentials, private keys, raw sensitive configuration, or sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
