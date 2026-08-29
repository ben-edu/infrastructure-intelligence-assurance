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
accepted main after PR #64: df6b85597a17068eb3b38dd3e83cc280af44c222
active branch: agent/m6-ansible-declared-inventory
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

Terraform state membership, runtime instance count, provider reachability, live resource existence, drift, and destructive-change status remain UNKNOWN.

## Accepted Milestone 6 — Terraform execution declaration discovery

Report:

```text
docs/reports/2026-08-29-m6-terraform-execution-declaration-discovery.md
```

Accepted corrected result:

```text
focused tests: 4 passed in 0.09s
source_mode: GIT_TRACKED_SAFE_WORKFLOW_SCRIPT_TEXT_ONLY
source_status: COMPLETE
tracked_files_returned: 400
candidate_files_selected: 160
candidate_files_scanned: 160
terraform_execution_signal_files: NONE_OBSERVED
terraform_signal_files: 0
phase_file_counts: NONE_OBSERVED
phase_signal_counts: NONE_OBSERVED
files_with_gate_signal: 0
```

Phase declarations `init`, `validate`, `plan`, `apply`, `destroy`, `refresh`, and `import` are all `NONE_OBSERVED_IN_BOUNDED_SOURCE`.

Preserve:

```text
execution_outcome_status: UNKNOWN
plan_result_status: UNKNOWN
apply_result_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
```

Gate-only files are excluded from Terraform execution evidence. Bounded signal absence is not proof that Terraform execution never occurs elsewhere or manually.

## Active Milestone 6 slice — Ansible declared-state inventory

Implementation:

```text
scripts/discovery/m6_ansible_declared_inventory.py
tests/test_ansible_declared_inventory.py
```

Bounded source:

```text
/home/ben/projects/afpa-infra-rebuild
Git-tracked safe Ansible source only
```

Goal: create a safe structural inventory of declared Ansible inventory files, playbook candidates, role directories, and bounded host/group declaration counts without exposing host identifiers or sensitive variables.

Safe projections:

```text
inventory file identifier
playbook file identifier
role directory identifier
inventory group declaration count
inventory host declaration count
aggregate inventory/playbook/role counts
```

Do not print or persist:

```text
hostnames
IP addresses
inventory variable values
group_vars / host_vars / vars contents
Ansible Vault contents
vault passwords
ansible_password / become_password
private keys
credentials/tokens
connection strings
```

`group_vars`, `host_vars`, and `vars` contents are not read in this slice. Role-directory presence does not establish role invocation by a playbook.

No Ansible CLI, SSH connection, runtime facts, execution result, idempotence result, or drift result is allowed in this slice.

Expected semantics:

```text
managed_host_coverage_status: DECLARED_CONFIGURATION_ONLY
live_managed_host_coverage_status: UNKNOWN
execution_outcome_status: UNKNOWN
configuration_drift_status: UNKNOWN
```

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m6-ansible-declared-inventory

python3 -m pytest -q \
  tests/test_ansible_declared_inventory.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_ansible_declared_inventory.py

echo "discovery_rc=$?"
```

Accept only declared-source structure and counts. Do not infer host reachability, configuration application, execution success, or drift.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- declared execution workflow is not observed execution outcome;
- source artifacts and derived assurance remain separate;
- Terraform state and real tfvars do not enter evidence/AI context;
- Ansible Vault and credential material do not enter evidence/AI context;
- host identifiers and inventory variable values are not projected;
- no drift result is inferred without appropriate evidence;
- unknowns are not forced closed without authoritative evidence;
- no secrets, credentials, private keys, raw sensitive configuration, or sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
