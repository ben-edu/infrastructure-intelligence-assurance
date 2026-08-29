# Milestone 6 — Terraform Execution Declaration Discovery

Date: 2026-08-29
Status: ACCEPTED
Mode: read-only declared-source discovery

## Scope

This slice inspected bounded Git-tracked workflow/script text from the known infrastructure repository for explicit Terraform execution-phase declaration signals.

It did not execute Terraform, Jenkins, GitHub Actions, or provider APIs and did not inspect Terraform state or real tfvars.

## Accepted tests

```text
4 passed in 0.09s
```

The retry included a regression guard ensuring gate-only files are not promoted into Terraform execution evidence.

## Accepted source result

```text
repository_alias: afpa-infra-rebuild
source_mode: GIT_TRACKED_SAFE_WORKFLOW_SCRIPT_TEXT_ONLY
source_status: COMPLETE
tracked_files_returned: 400
candidate_files_selected: 160
candidate_files_scanned: 160
read_or_decode_skips: 0
oversize_skips: 0
```

Safe execution projection:

```text
terraform_execution_signal_files: NONE_OBSERVED
terraform_signal_files: 0
phase_file_counts: NONE_OBSERVED
phase_signal_counts: NONE_OBSERVED
files_with_gate_signal: 0
```

Accepted phase declaration states:

```text
init: NONE_OBSERVED_IN_BOUNDED_SOURCE
validate: NONE_OBSERVED_IN_BOUNDED_SOURCE
plan: NONE_OBSERVED_IN_BOUNDED_SOURCE
apply: NONE_OBSERVED_IN_BOUNDED_SOURCE
destroy: NONE_OBSERVED_IN_BOUNDED_SOURCE
refresh: NONE_OBSERVED_IN_BOUNDED_SOURCE
import: NONE_OBSERVED_IN_BOUNDED_SOURCE
```

Preserved unknowns:

```text
execution_outcome_status: UNKNOWN
plan_result_status: UNKNOWN
apply_result_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
successful_execution_claims: 0
drift_claims: 0
destructive_change_claims: 0
```

## False-positive correction

The first live run incorrectly included a Python application file because it contained a lexical gate keyword even though no Terraform phase token was present.

The implementation was corrected to fail closed: a file enters Terraform execution evidence only when at least one explicit Terraform phase token is present. Gate metadata is considered only for such Terraform-signal files.

The corrected live run produced zero Terraform execution-signal files.

## Interpretation

`NONE_OBSERVED_IN_BOUNDED_SOURCE` is bounded negative evidence only. It does not establish that Terraform phases are never run elsewhere, manually, from untracked material, or from another automation source.

Declared workflow absence is not execution failure. No execution history, plan output, apply output, drift result, destructive-change result, or provider outcome is inferred.

## Trust boundary

Only bounded Git-tracked workflow/script text was read. Raw command lines, command arguments, environment values, credentials, endpoints, connection strings, Terraform state, state backups, real tfvars, secrets, private keys, certificates, and provider tokens/passwords were not printed or persisted.

No infrastructure or repository mutation was performed by the discovery.

## Next bounded step

Start the Ansible declared-state inventory portion of Milestone 6. Inventory/playbook/role structure should be derived from Git-tracked safe source only. Do not execute Ansible, connect to managed hosts, read vault secrets, or infer observed configuration from declarations.
