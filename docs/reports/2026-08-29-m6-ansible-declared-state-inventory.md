# Milestone 6 — Ansible Declared-State Inventory

Date: 2026-08-29
Status: ACCEPTED
Infrastructure mutation: not allowed

## Goal

Establish a bounded, safe inventory of Git-tracked Ansible declared configuration in the known infrastructure repository without invoking Ansible, connecting to managed hosts, reading runtime facts, or exposing host identifiers and sensitive variables.

## Source boundary

```text
repository_alias: afpa-infra-rebuild
source_path: /home/ben/projects/afpa-infra-rebuild
source_mode: GIT_TRACKED_SAFE_ANSIBLE_SOURCE_ONLY
mutation_allowed: false
```

Excluded from projection and/or reading in this slice:

```text
group_vars contents
host_vars contents
vars contents
Ansible Vault contents
vault passwords
hostnames and IP addresses
inventory variable values
ansible_password / become_password
private keys
credentials and tokens
connection strings
runtime facts
```

No `ansible`, `ansible-playbook`, SSH, or managed-host connection was executed.

## Validation

Focused tests:

```text
3 passed in 0.09s
```

Live bounded discovery return code:

```text
discovery_rc=0
```

## Accepted source result

```text
source_status: COMPLETE
tracked_files_returned: 400
ansible_scope_files: 57
files_read: 41
excluded_sensitive_ansible_data_files: 8
read_or_decode_skips: 0
oversize_skips: 0
```

## Inventory candidates

Five inventory candidates were identified structurally.

Operational inventory declaration:

```text
ansible/inventories/lab/hosts.yml
group_declaration_count: 6
host_declaration_count: 8
```

Role-test inventory candidates:

```text
ansible/roles/baseline/tests/inventory
ansible/roles/harbor_service/tests/inventory
ansible/roles/jenkins_service/tests/inventory
ansible/roles/platform_audit/tests/inventory
```

Each role-test inventory candidate had:

```text
group_declaration_count: 0
host_declaration_count: 0
```

No hostnames, addresses, inventory variable names/values, or connection details were projected.

## Playbook candidates

Ten Git-tracked playbook candidates were observed:

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

Playbook presence is declared configuration only. It does not establish that a playbook has executed successfully or recently.

## Role directories

Seven role directories were observed:

```text
ansible/roles/baseline
ansible/roles/common
ansible/roles/harbor_service
ansible/roles/jenkins_service
ansible/roles/platform_audit
ansible/roles/ssh_hardening
ansible/roles/ssh_users
```

Role-directory presence does not establish that a role is invoked by an accepted playbook.

## Summary

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

## Interpretation boundary

The eight host declarations are bounded configuration declarations, not eight verified reachable or currently managed hosts.

The six group declarations are inventory structure, not ownership, environment, or availability conclusions unless separately validated.

Inventory, playbook, and role presence does not establish execution history, successful configuration application, idempotence, runtime facts, or drift.

## Trust boundary

Only bounded Git-tracked Ansible source structure was inspected. Sensitive Ansible data locations were excluded. No secrets, host identifiers, credentials, private keys, Vault contents, raw connection details, runtime facts, or managed-host data entered evidence.

No repository or infrastructure mutation was performed.

## Next useful slice

Build a bounded **Ansible playbook-to-role declared relationship** from safe Git-tracked playbook structure only.

The next slice may project:

```text
playbook file identifier
safe role-directory identifier
direct role-reference count
relationship status: RESOLVED / NONE_OBSERVED / UNKNOWN
```

It must not project play names, host targets, variables, task arguments, handler contents, host identifiers, Vault data, or credentials. It must not execute Ansible or SSH.
