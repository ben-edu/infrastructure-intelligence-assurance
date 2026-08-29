# Milestone 6 — Ansible-to-Jenkins Relationship Source Discovery

Date: 2026-08-29

## Scope

This report records a bounded read-only discovery for an explicit declared relationship between Jenkins context and an accepted Ansible execution entry point.

The purpose was to determine whether previously accepted Jenkins runtime metadata could be related to Ansible execution using a safe authoritative declared source without reading Jenkins console logs, job configuration bodies, build parameters, raw command bodies, credentials, or sensitive inventory/host data.

## Relationship acceptance rule

A positive relationship signal requires both in the same safe Git-tracked text file:

```text
explicit Jenkins context
AND
one accepted Ansible execution entry point:
  ansible-playbook
  ansible-runner run
  ansible-navigator run
```

Generic words such as `jenkins` or `ansible` alone are not relationship evidence.

## Validation

Focused tests after the streaming retry fix:

```text
6 passed in 0.14s
```

Successful live retry:

```text
discovery_rc=0
source_mode: GIT_TRACKED_SAFE_JENKINS_ANSIBLE_RELATIONSHIP_TEXT_ONLY
source_status: COMPLETE
tracked_files_returned: 400
candidate_files_selected: 158
candidate_files_scanned: 158
excluded_or_unsafe_paths: 242
read_or_decode_skips: 0
oversize_skips: 0
jenkins_context_files: 11
ansible_entrypoint_signal_files: 0
explicit_relationship_signal_files: 0
relationship_source_status: NONE_OBSERVED_IN_BOUNDED_SOURCE
```

Repository-wide regression gate:

```text
387 passed in 1.76s
```

## First live attempt — rejected for bounded absence

The first attempt returned:

```text
source_status: INCOMPLETE
candidate_files_selected: 158
candidate_files_scanned: 157
read_or_decode_skips: 0
oversize_skips: 1
explicit_relationship_signal_files: 0
relationship_source_status: SOURCE_INCOMPLETE
discovery_rc: 2
```

That result was `FAILED_TO_OBSERVE / INCOMPLETE` for bounded absence. Its zero relationship count must not be reused as accepted negative evidence because one selected safe candidate was skipped by the former size ceiling.

The retry replaced the old `512 KiB` whole-file ceiling with bounded streaming and an `8 MiB` hard ceiling. Safe files above the old ceiling can be scanned without retaining or projecting raw content; files above the hard ceiling still fail closed.

## Accepted bounded result

The complete retry observed:

```text
Jenkins-context files: 11
accepted Ansible-entrypoint signal files: 0
explicit Jenkins+Ansible relationship signal files: 0
relationship source status: NONE_OBSERVED_IN_BOUNDED_SOURCE
```

Interpretation:

- No explicit declared Jenkins-to-Ansible relationship was observed in the complete bounded safe Git-tracked source.
- This is bounded declared-source absence only.
- It does not prove Jenkins cannot invoke Ansible through generated configuration, plugins, external repositories, manually created jobs, or operator actions outside this source.
- Previously observed Jenkins build `SUCCESS` metadata therefore cannot be promoted to Ansible execution-success evidence.

## Evidence-path closure

Do not widen the Jenkins-to-Ansible outcome path merely to eliminate the remaining unknown.

Within the accepted read-only evidence boundary, no safe authoritative relationship source was found that can relate the accepted Jenkins job/build metadata to Ansible execution.

Preserve:

```text
Ansible execution_outcome_status: UNKNOWN
Ansible execution_success_status: UNKNOWN
idempotence_status: UNKNOWN
configuration_drift_status: UNKNOWN
successful_execution_claims: 0
idempotence_claims: 0
drift_claims: 0
```

A future source may reopen this question only if it provides stronger authoritative relationship evidence without violating the trust boundary.

## Trust boundary

The discovery:

```text
mutation_allowed: False
jenkins_api_invoked: False
jenkins_console_logs_inspected: False
jenkins_job_config_bodies_inspected: False
jenkins_build_parameters_inspected: False
ansible_cli_invoked: False
ssh_connections_performed: False
```

Only safe Git-tracked workflow/script-like text was inspected. Sensitive path classes, `.env`, Ansible variable directories, Terraform state/tfvars, credentials, tokens, private keys, and Vault material were excluded.

Safe candidate files were streamed with a hard byte ceiling. Raw source content was not retained as evidence and was not printed.

Raw source lines, Jenkins job names, build numbers, commands, arguments, inventory values, host targets, credentials, endpoints, console logs, job configuration bodies, build parameters, and Vault material were not printed or persisted.

## Next smallest useful step

This slice passed focused, live, and repository-wide validation and is merge-ready after PR scope/mergeability inspection.

After merge, do not add another Jenkins-to-Ansible relationship probe without new evidence. Return to the remaining Milestone 6 gaps and select the smallest read-only slice that can add independent authoritative evidence, while preserving the closed Jenkins relationship path and all remaining `UNKNOWN` states.
