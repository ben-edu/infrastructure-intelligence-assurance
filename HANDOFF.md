# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read:

```text
docs/PROJECT_CONTINUITY.md
```

## Resume protocol

1. Read Project Sources.
2. Read `docs/PROJECT_CONTINUITY.md`.
3. Read `HANDOFF.md` from `main`.
4. Check open PRs and active project branches. If an active branch has a newer `HANDOFF.md`, prefer it for in-flight state.
5. Read only reports/ADRs relevant to the active slice.
6. Prefer repository state and fresh evidence over chat reconstruction.
7. Continue the `Exact next step` unless new evidence invalidates it.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #66: 24b7b14924c6f2217666a4b18766bc3b4cd81d9d
active branch: agent/m6-ansible-playbook-role-coverage
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6: ACTIVE
mutation_allowed: false
management host: mgmt-automation
bounded infrastructure repository: /home/ben/projects/afpa-infra-rebuild
```

Closed/unmerged PRs that are not accepted checkpoints:

```text
#65 — closed unmerged; superseded by #66
#67 — accidental temporary PR; closed unmerged
```

## Milestone 5 boundary

Accepted closure report:

```text
docs/reports/2026-08-23-m5-read-only-discovery-closure.md
```

Do not create additional M5 probes merely to force preserved unknowns closed. Controlled restore/integrity work remains deferred until explicitly authorized.

## Accepted Milestone 6 — Terraform

Reports:

```text
docs/reports/2026-08-29-m6-terraform-declared-state-inventory.md
docs/reports/2026-08-29-m6-terraform-root-module-declared-coverage.md
docs/reports/2026-08-29-m6-terraform-execution-declaration-discovery.md
```

Accepted bounded state:

```text
Git-tracked .tf files scanned: 15/15
root candidates: 2
module directories: 1
provider types: proxmox=2
resource types: proxmox_vm_qemu=2
bm1 direct proxmox_vm_qemu blocks: 1
bm2 direct proxmox_vm_qemu blocks: 1
resolved local module for both roots: terraform/modules/proxmox_vm
resource blocks in that local module: 0
Terraform execution-declaration files in bounded workflow/script source: 0
```

Preserve:

```text
Terraform state-backed coverage: UNKNOWN
live resource coverage: UNKNOWN
execution outcome: UNKNOWN
plan/apply result: UNKNOWN
drift: UNKNOWN
destructive-change status: UNKNOWN
```

The first Terraform execution scan had a rejected gate-only false positive. The corrected implementation requires a Terraform phase token before a file enters Terraform execution evidence. Do not reuse the rejected result.

## Accepted Milestone 6 — Ansible declared inventory

Report:

```text
docs/reports/2026-08-29-m6-ansible-declared-state-inventory.md
```

Accepted validation:

```text
focused tests: 3 passed in 0.09s
full suite before PR #66 merge: 360 passed in 3.52s
discovery_rc: 0
source_status: COMPLETE
tracked_files_returned: 400
ansible_scope_files: 57
files_read: 41
excluded_sensitive_ansible_data_files: 8
```

Accepted structure:

```text
inventory files: 5
playbooks: 10
role directories: 7
inventory group declarations: 6
inventory host declarations: 8
managed_host_coverage_status: DECLARED_CONFIGURATION_ONLY
```

The 8 host declarations are not 8 verified/reachable managed hosts.

## Active Milestone 6 — Ansible playbook-to-role declared coverage

Implementation:

```text
scripts/discovery/m6_ansible_playbook_role_coverage.py
tests/test_ansible_playbook_role_coverage.py
```

Acceptance report already recorded on this branch:

```text
docs/reports/2026-08-29-m6-ansible-playbook-role-declared-coverage.md
```

Focused/live validation:

```text
focused tests: 4 passed in 0.10s
discovery_rc: 0
source_status: COMPLETE
tracked_files_returned: 400
playbook_files_scanned: 10
read_or_decode_skips: 0
oversize_skips: 0
```

Accepted direct declared relationships:

```text
baseline.yml -> ansible/roles/baseline
common.yml -> ansible/roles/common
harbor-service.yml -> ansible/roles/harbor_service
jenkins-service.yml -> ansible/roles/jenkins_service
platform-audit.yml -> ansible/roles/platform_audit
services-stack.yml -> ansible/roles/harbor_service + ansible/roles/jenkins_service
ssh-hardening.yml -> ansible/roles/ssh_hardening
ssh-users.yml -> ansible/roles/ssh_users
```

Direct role reference not observed in bounded playbook structure:

```text
ansible/playbooks/ping.yml
ansible/playbooks/vault-check.yml
```

Summary:

```text
declared_role_directories_total: 7
referenced_role_directories_total: 7
unreferenced_in_direct_playbook_scope_total: 0
playbooks_with_resolved_local_role: 8
playbooks_with_no_role_reference: 2
playbooks_with_unknown_role_reference: 0
resolved_role_reference_signals: 9
unresolved_role_reference_signals: 0
unparsed_role_structures: 0
declared_role_coverage_status: STRUCTURAL_CONFIGURATION_ONLY
live_managed_host_coverage_status: UNKNOWN
execution_outcome_status: UNKNOWN
idempotence_status: UNKNOWN
configuration_drift_status: UNKNOWN
```

`NONE_OBSERVED` here is bounded direct-reference absence only. It does not prove the playbook cannot reach roles indirectly through dependencies, nested includes, dynamic expressions, or other entry points.

## Merge gate — PENDING

Because this slice adds reusable discovery implementation and tests, run the repository-wide suite before PR/merge.

## Exact next step

On `mgmt-automation` run only:

```bash
cd ~/projects/infrastructure-intelligence-assurance
python3 -m pytest -q
```

Do not wrap it in strict interactive shell mode.

If the full suite passes:

1. record the exact pass count in this handoff/report/PR;
2. create or inspect the PR for `agent/m6-ansible-playbook-role-coverage`;
3. ensure only intended files changed and no placeholders/debug files exist;
4. squash-merge;
5. record the new accepted `main` SHA in the next branch handoff;
6. start **Ansible execution-declaration discovery**.

Next-slice goal after merge:

```text
Determine whether safe Git-tracked workflow/script files explicitly declare ansible-playbook or another tightly bounded Ansible execution entry point.
```

That future slice is declaration evidence only. It must not infer execution history or success.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- declared playbook/role relationship is not execution evidence;
- source artifacts and derived assurance remain separate;
- Terraform state and real tfvars do not enter evidence/AI context;
- Ansible Vault and credential material do not enter evidence/AI context;
- host identifiers and sensitive inventory values are not projected;
- play names, host target patterns, role/task argument values, and handler contents are not projected;
- `NONE_OBSERVED_IN_BOUNDED_SOURCE` is not universal absence;
- `FAILED_TO_OBSERVE` is not negative evidence;
- no drift, execution success, idempotence, compliance, or destructive-change result is inferred without authoritative evidence;
- unknowns are not forced closed;
- no secrets, credentials, private keys, raw sensitive configuration, or sensitive connection strings enter evidence/AI context;
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
