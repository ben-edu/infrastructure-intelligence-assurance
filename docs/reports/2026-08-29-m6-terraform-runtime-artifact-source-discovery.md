# Milestone 6 — Terraform Runtime-Artifact Source Discovery

Date: 2026-08-29
Status: ACCEPTED / MERGE READY
Mode: read-only / filesystem-metadata-only

## Scope

This report records a bounded filesystem-metadata discovery for local Terraform runtime artifacts in the two previously accepted Terraform root candidates.

Bounded roots:

```text
terraform/environments/bm1
terraform/environments/bm2
```

The discovery does not open or parse Terraform state, state backups, backend metadata, workspace metadata, saved plans, or tfvars. Terraform CLI and provider APIs are not invoked.

## Validation

Focused tests:

```text
4 passed in 0.06s
```

Accepted live discovery:

```text
discovery_rc=0
source_mode: BOUNDED_TERRAFORM_ROOT_FILESYSTEM_METADATA_ONLY
source_status: COMPLETE
root_directories_expected: 2
root_directories_observed: 2
metadata_failures: 0
symlink_entries_skipped: 0
```

Per-root metadata:

```text
root=bm1 root_status=OBSERVED working_directory=OBSERVED state_artifact=OBSERVED state_backup_artifact=OBSERVED workspace_state_directory=NONE_OBSERVED workspace_directories=0 backend_metadata_candidate=NONE_OBSERVED workspace_selection_metadata_candidate=NONE_OBSERVED saved_plan_candidates=0
root=bm2 root_status=OBSERVED working_directory=OBSERVED state_artifact=OBSERVED state_backup_artifact=OBSERVED workspace_state_directory=NONE_OBSERVED workspace_directories=0 backend_metadata_candidate=NONE_OBSERVED workspace_selection_metadata_candidate=NONE_OBSERVED saved_plan_candidates=0
```

Aggregate metadata:

```text
working_directories_observed: 2
top_level_state_artifacts_observed: 2
top_level_state_backup_artifacts_observed: 2
workspace_state_directories_observed: 0
workspace_directories_observed: 0
backend_metadata_candidates_observed: 0
workspace_selection_metadata_candidates_observed: 0
saved_plan_artifact_candidates_observed: 0
runtime_artifact_source_status: RUNTIME_ARTIFACT_METADATA_OBSERVED
```

Repository-wide regression gate:

```text
391 passed in 5.58s
```

## Accepted interpretation

Both accepted Terraform root candidates expose local top-level Terraform state-like artifacts and state-backup artifacts by filesystem metadata. Both also expose a `.terraform` working-directory artifact.

This establishes only that local runtime-artifact metadata exists in the bounded roots. It does not establish that either state file is current, authoritative, complete, safe to use, or representative of live infrastructure.

No local workspace-state directory, workspace-selection metadata candidate, backend-metadata candidate, or saved-plan candidate was observed in the complete bounded metadata scan.

Those absences are bounded local filesystem-metadata absence only. They do not rule out remote state, another checkout, CI artifacts, external execution, or other runtime sources.

## Trust / outcome boundary

Preserve:

```text
state_backed_coverage_status: UNKNOWN
live_resource_coverage_status: UNKNOWN
plan_result_status: UNKNOWN
apply_result_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
state_backed_coverage_claims: 0
drift_claims: 0
destructive_change_claims: 0
```

Filesystem artifact metadata is source-capability evidence only. It must not be promoted to state-backed coverage, current state, plan/apply outcome, drift, or destructive-change evidence.

## Trust boundary

The discovery:

```text
mutation_allowed: False
terraform_cli_invoked: False
terraform_state_contents_inspected: False
terraform_plan_contents_inspected: False
terraform_tfvars_contents_inspected: False
provider_api_invoked: False
```

Only filesystem metadata for the two accepted Terraform root candidates and generic Terraform runtime-artifact names was inspected.

Terraform state, state backups, backend metadata, workspace metadata, saved plans, tfvars, credentials, provider configuration values, resource addresses, workspace names, endpoint values, commands, and sensitive connection strings were not opened, printed, or persisted.

Relevant symlinks or metadata lookup failures fail closed as incomplete observation.

## Next smallest useful step

The observed local state artifacts justify a separate, tightly bounded **Terraform local-state safe structural aggregation** slice.

That future slice may inspect local state process-locally only to project aggregate non-sensitive structure, such as state parse status, aggregate managed/data resource counts, aggregate instance counts, and resource-type categories. It must not project state values, resource addresses, resource names, instance keys, outputs, serial/lineage identifiers, provider configuration values, endpoints, credentials, sensitive attributes, or raw state.

A successful structural aggregation still does not establish live resource coverage, current state, plan/apply success, drift, or destructive-change status. Those remain `UNKNOWN` until separately verified by authoritative evidence.
