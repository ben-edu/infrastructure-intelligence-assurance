# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, also read:

```text
docs/PROJECT_CONTINUITY.md
```

## Resume protocol

1. Read Project Sources.
2. Read `docs/PROJECT_CONTINUITY.md`.
3. Read `HANDOFF.md` from `main`.
4. Check open PRs/active project branches; if one contains a newer `HANDOFF.md`, prefer it for in-flight execution state.
5. Read only the report/ADR/milestone document referenced by the active slice.
6. Prefer repository and fresh live evidence over chat reconstruction.
7. Continue the `Exact next step` unless new evidence requires a change.

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
bounded infrastructure repository: /home/ben/projects/afpa-infra-rebuild
```

## Milestone 5 boundary

Accepted closure report:

```text
docs/reports/2026-08-23-m5-read-only-discovery-closure.md
```

Do not create additional M5 probes merely to force preserved unknowns closed. Controlled restore/integrity work remains deferred until explicitly authorized.

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
state_backed_coverage_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
```

## Accepted Milestone 6 — Terraform root/module declared coverage

Report:

```text
docs/reports/2026-08-29-m6-terraform-root-module-declared-coverage.md
```

Accepted structure:

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

Do not infer runtime VM count, Terraform state membership, provider reachability, or live existence from these declarations.

## Accepted Milestone 6 — Terraform execution declaration discovery

Report:

```text
docs/reports/2026-08-29-m6-terraform-execution-declaration-discovery.md
```

Accepted corrected result:

```text
focused tests: 4 passed in 0.09s
source_status: COMPLETE
tracked_files_returned: 400
candidate_files_selected: 160
candidate_files_scanned: 160
terraform_execution_signal_files: 0
files_with_gate_signal: 0
init/validate/plan/apply/destroy/refresh/import: NONE_OBSERVED_IN_BOUNDED_SOURCE
execution_outcome_status: UNKNOWN
plan_result_status: UNKNOWN
apply_result_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
```

Important rejected evidence history: the first live run included a gate-only false positive from a non-Terraform file. The implementation was corrected to require an explicit Terraform phase token before a file enters Terraform execution evidence. Do not reuse the rejected gate-only result.

## Accepted Milestone 6 — Ansible declared-state inventory

Report:

```text
docs/reports/2026-08-29-m6-ansible-declared-state-inventory.md
```

Focused/live validation completed:

```text
focused tests: 3 passed in 0.09s
discovery_rc: 0
source_mode: GIT_TRACKED_SAFE_ANSIBLE_SOURCE_ONLY
source_status: COMPLETE
tracked_files_returned: 400
ansible_scope_files: 57
files_read: 41
excluded_sensitive_ansible_data_files: 8
read_or_decode_skips: 0
oversize_skips: 0
```

Inventory candidates:

```text
ansible/inventories/lab/hosts.yml
  group_declaration_count: 6
  host_declaration_count: 8

ansible/roles/baseline/tests/inventory
ansible/roles/harbor_service/tests/inventory
ansible/roles/jenkins_service/tests/inventory
ansible/roles/platform_audit/tests/inventory
  group_declaration_count: 0
  host_declaration_count: 0
```

Playbook candidates:

```text
ansible/playbooks/baseline.yml
ansible/playbooks/common.yml
ansible/playbooks/harbor-service.yml
ansible/playbooks/jenkins-service.yml
ansible/playbooks/ping.yml
ansible/playbooks/platform-audit.yml
ansible/playbooks/services-stack.yml
ansible/playbooks/ssh-hardening.yml
ansible/playbooks/ssh-users.yml
ansible/playbooks/vault-check.yml
```

Role directories:

```text
ansible/roles/baseline
ansible/roles/common
ansible/roles/harbor_service
ansible/roles/jenkins_service
ansible/roles/platform_audit
ansible/roles/ssh_hardening
ansible/roles/ssh_users
```

Summary semantics:

```text
inventory_files_total: 5
playbook_files_total: 10
role_directories_total: 7
inventory_group_declarations: 6
inventory_host_declarations: 8
managed_host_coverage_status: DECLARED_CONFIGURATION_ONLY
live_managed_host_coverage_status: UNKNOWN
execution_outcome_status: UNKNOWN
configuration_drift_status: UNKNOWN
execution_success_claims: 0
drift_claims: 0
```

The 8 host declarations are not 8 verified/reachable managed hosts. Role-directory presence does not prove role invocation by any playbook.

## Exact next step

The Ansible slice is not merge-ready until the repository-wide test suite passes after the script, tests, report, continuity document, handoff, and README changes.

On `mgmt-automation` run:

```bash
cd ~/projects/infrastructure-intelligence-assurance
python3 -m pytest -q
```

Do not run strict shell mode around this command.

If the full suite passes:

1. treat the Ansible declared-state slice as merge-ready;
2. inspect the PR changed-file scope and mergeability;
3. squash-merge the PR;
4. record the new accepted `main` SHA in the next branch handoff;
5. start **Ansible playbook-to-role declared coverage** as the next smallest read-only slice.

Planned next-slice goal after merge:

```text
For each accepted playbook candidate, determine whether safe Git-tracked playbook structure directly references one of the accepted local role directories.
```

Allowed future projection:

```text
playbook file identifier
safe local role-directory identifier
direct role-reference count
relationship status: RESOLVED_LOCAL_ROLE / NONE_OBSERVED / UNKNOWN
aggregate referenced/unreferenced role counts
```

Do not project play names, host target patterns, hostnames/IPs, inventory variable values, group_vars/host_vars/vars contents, role/task argument values, handler contents, Vault data, credentials, private keys, tokens, or connection strings. Do not execute Ansible or SSH.

## Continuity rule

At every accepted slice before merge:

1. create/update the accepted report when reusable evidence changed;
2. update `HANDOFF.md` with accepted SHA context, evidence, preserved unknowns, trust boundary, and exact next step;
3. update roadmap/current-state/README only when milestone status, architecture, or user-facing project status materially changes;
4. ensure no temporary/debug/placeholder files remain;
5. inspect PR scope/mergeability and squash-merge when clean;
6. carry the new accepted `main` SHA into the next branch handoff.

This rule is mandatory to make a new chat tab able to continue without prior chat history.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- declared execution workflow is not observed execution outcome;
- source artifacts and derived assurance remain separate;
- Terraform state and real tfvars do not enter evidence/AI context;
- Ansible Vault and credential material do not enter evidence/AI context;
- host identifiers and sensitive inventory values are not projected;
- `NONE_OBSERVED_IN_BOUNDED_SOURCE` is not universal absence;
- `FAILED_TO_OBSERVE` is not negative evidence;
- no drift, success, protection, compliance, or destructive-change result is inferred without authoritative evidence;
- unknowns are not forced closed;
- no secrets, credentials, private keys, raw sensitive configuration, or sensitive connection strings enter evidence/AI context;
- generated operational artifacts keep `mutation_allowed=false`.
