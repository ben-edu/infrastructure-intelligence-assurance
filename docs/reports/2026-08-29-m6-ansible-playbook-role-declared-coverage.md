# Milestone 6 — Ansible Playbook-to-Role Declared Coverage

Date: 2026-08-29

## Scope

This report records the accepted read-only declared-state relationship between the previously accepted Ansible playbook candidates and local role directories in the bounded infrastructure repository.

Source repository:

```text
/home/ben/projects/afpa-infra-rebuild
```

Source mode:

```text
GIT_TRACKED_SAFE_ANSIBLE_PLAYBOOK_STRUCTURE_ONLY
```

No Ansible CLI, SSH connection, managed-host query, runtime fact collection, Vault-content inspection, or infrastructure mutation was performed.

## Validation

Focused test result:

```text
4 passed in 0.10s
```

Repository-wide regression result:

```text
364 passed in 1.51s
```

Discovery result:

```text
discovery_rc=0
source_status=COMPLETE
tracked_files_returned=400
playbook_files_scanned=10
read_or_decode_skips=0
oversize_skips=0
```

The focused, live, and repository-wide gates all passed.

## Accepted declared relationships

```text
ansible/playbooks/baseline.yml
  -> ansible/roles/baseline

ansible/playbooks/common.yml
  -> ansible/roles/common

ansible/playbooks/harbor-service.yml
  -> ansible/roles/harbor_service

ansible/playbooks/jenkins-service.yml
  -> ansible/roles/jenkins_service

ansible/playbooks/platform-audit.yml
  -> ansible/roles/platform_audit

ansible/playbooks/services-stack.yml
  -> ansible/roles/harbor_service
  -> ansible/roles/jenkins_service

ansible/playbooks/ssh-hardening.yml
  -> ansible/roles/ssh_hardening

ansible/playbooks/ssh-users.yml
  -> ansible/roles/ssh_users
```

No supported direct role-reference structure was observed in:

```text
ansible/playbooks/ping.yml
ansible/playbooks/vault-check.yml
```

This bounded absence does not prove those playbooks cannot reach roles indirectly through dependencies, nested includes, dynamic expressions, or other mechanisms outside this slice.

## Summary

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
execution_success_claims: 0
drift_claims: 0
```

All seven accepted local role directories have at least one supported direct playbook reference in this bounded source.

## Interpretation boundary

A resolved local role relationship is declared Git-tracked structure only. It does not establish that the playbook ran, that the role executed, that any host was reachable, that configuration changed, or that the run was idempotent.

`NONE_OBSERVED` for a playbook means only that no supported direct role-reference structure was observed in that playbook.

A role directory not referenced in this direct scope would not automatically be unused because role dependencies, nested includes, dynamic expressions, or other entry points may exist outside the modeled source.

## Trust boundary

The discovery did not project or persist:

```text
play names
hosts or target patterns
hostnames or IP addresses
inventory values
group_vars / host_vars / vars contents
role/task argument values
handler contents
Vault contents
credentials, private keys, tokens, or connection strings
```

Only simple safe role tokens required for local role-directory resolution were retained in memory. Unresolved role token values were not printed.

No repository or infrastructure mutation was performed by the discovery.

## Preserved unknowns

```text
live managed-host coverage: UNKNOWN
Ansible execution outcome: UNKNOWN
idempotence: UNKNOWN
configuration drift: UNKNOWN
```

These unknowns must not be promoted from declared playbook structure.

## Next smallest useful slice

Perform bounded **Ansible execution-declaration discovery**.

Goal: determine whether safe Git-tracked workflow/script files explicitly declare `ansible-playbook` or tightly bounded Ansible execution entry points, without executing Ansible and without printing raw commands or arguments.

This is declaration evidence only. It must not be treated as execution history or success evidence.
