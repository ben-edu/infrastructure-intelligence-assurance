# Milestone 6 — Terraform Read-Only Plan Evidence

Date: 2026-08-29
Status: ACCEPTED PENDING FULL-SUITE GATE
Mode: read-only Terraform plan / provider observation / aggregate projection only

## Scope

This report records bounded read-only Terraform plan evidence for the two previously accepted Terraform roots:

```text
terraform/environments/bm1
terraform/environments/bm2
```

Two plan modes were executed per root:

```text
configuration_vs_state: terraform plan -refresh=false
refresh_only: terraform plan -refresh-only
```

Both modes used:

```text
-input=false
-lock=false
-detailed-exitcode
-json
```

No saved plan was written and no Terraform apply/import/state mutation command was invoked.

## Validation

Focused tests after the parser correction:

```text
6 passed in 0.07s
```

Accepted retry:

```text
discovery_rc=0
source_mode: TERRAFORM_READONLY_CONFIGURATION_AND_REFRESH_ONLY_PLAN_JSON
source_status: COMPLETE
roots_expected: 2
roots_configuration_plan_complete: 2
roots_refresh_only_plan_complete: 2
```

Per-root accepted evidence:

```text
root=bm1 configuration_plan=COMPLETE_NO_CHANGES configuration_exit_code=0 configuration_actions=NONE_OBSERVED refresh_only_plan=COMPLETE_CHANGES_OBSERVED refresh_only_exit_code=2 refresh_only_actions=update=2 destructive_change_status=NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN state_tracked_drift_signal_status=STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED
root=bm2 configuration_plan=COMPLETE_NO_CHANGES configuration_exit_code=0 configuration_actions=NONE_OBSERVED refresh_only_plan=COMPLETE_CHANGES_OBSERVED refresh_only_exit_code=2 refresh_only_actions=update=4 destructive_change_status=NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN state_tracked_drift_signal_status=STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED
```

Aggregate accepted evidence:

```text
configuration_action_counts: NONE_OBSERVED
refresh_only_action_counts: update=6
configuration_plan_status: COMPLETE
state_tracked_refresh_drift_status: STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED
destructive_change_status: NONE_OBSERVED_IN_COMPLETE_CONFIGURATION_PLAN
```

A repository-wide test suite remains required before merge because this slice adds reusable discovery implementation and tests.

## Accepted interpretation

The configuration-vs-state plan completed with no changes for both accepted roots. Within this bounded scope, no configuration-driven create/update/delete/replace proposal was observed, and no destructive proposal was observed.

The refresh-only plan completed with Terraform detailed exit code 2 for both roots and emitted `resource_drift` update actions. The accepted aggregate is six state-tracked refresh drift update signals:

```text
bm1: update=2
bm2: update=4
aggregate: update=6
```

This is materially stronger than prior structural evidence because the refresh-only plan is allowed to perform provider reads and therefore compares state-tracked resources with live provider observations.

The finding is nevertheless bounded:

```text
STATE_TRACKED_DRIFT_CHANGE_SIGNAL_OBSERVED
```

It is not a universal infrastructure drift claim and does not identify which resources or attributes changed.

The first live attempt before the parser correction remains relevant only for its successful rc=2 change signal. Its `refresh_only_actions=NONE_OBSERVED` value is rejected and must not be reused, because that parser handled `planned_change` but not Terraform `resource_drift` events.

## Coverage / outcome boundary

Preserve:

```text
apply_result_status: UNKNOWN
live_resource_coverage_status: UNKNOWN
state_backed_coverage_status: UNKNOWN
```

This slice does not prove that every live resource is Terraform-managed, that local state is fully authoritative, or that any proposed change has been or should be applied.

A no-change `configuration_vs_state` plan is not a live drift check because refresh is disabled.

## Trust boundary

The collector reports:

```text
mutation_allowed: False
terraform_apply_invoked: False
terraform_state_locking_allowed: False
saved_plan_written: False
raw_plan_output_projected: False
raw_diagnostics_projected: False
resource_addresses_projected: False
resource_names_projected: False
state_values_projected: False
tfvars_values_projected: False
provider_read_observation_allowed: True
```

Terraform stdout/stderr remained process-local and were not printed or persisted. Only explicitly allowlisted aggregate action categories and statuses were projected.

Configuration plan action counts are derived only from Terraform `planned_change` events. Refresh-only drift action counts are derived only from Terraform `resource_drift` events. Resource identity is discarded before projection.

Raw Terraform plan JSON, diagnostics, resource addresses/names, instance identities, state/tfvars values, provider configuration values, endpoints, credentials, and sensitive connection strings were not projected.

No Terraform apply/import/state mutation command, SSH connection, repository mutation, or infrastructure mutation was performed. Provider reads during refresh-only planning were observation-only.

## Next smallest useful step

After the full repository suite passes and this slice is merged, reassess Milestone 6 rather than automatically adding another probe.

The accepted evidence now materially covers bounded Terraform plan metadata, destructive-proposal detection, and state-tracked refresh drift signal. Remaining stronger gaps include apply outcome, full live-resource coverage/state authority, and Ansible live execution/drift evidence. Those should remain UNKNOWN unless a materially stronger safe source or future authorized action justifies another slice.
