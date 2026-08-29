# Milestone 6 — Terraform Declared-to-Local-State Structural Coverage

Date: 2026-08-29
Status: ACCEPTED
Mode: read-only / aggregate declared-to-local-state relationship

## Scope

This report records a bounded relationship between Git-tracked Terraform declared resource-type block counts and process-local safe local-state managed resource-type block counts for the two accepted Terraform roots.

Bounded roots:

```text
terraform/environments/bm1
terraform/environments/bm2
```

Only aggregate resource-type block counts are compared. Managed state instance counts are intentionally not compared with declared resource-block counts.

## Validation

Focused tests:

```text
4 passed in 0.06s
```

Repository-wide regression gate:

```text
399 passed in 2.11s
```

Accepted live discovery:

```text
discovery_rc=0
source_mode: DECLARED_GIT_TF_TO_LOCAL_STATE_SAFE_TYPE_COUNT_RELATIONSHIP
source_status: COMPLETE
declared_source_status: COMPLETE
state_source_status: COMPLETE
roots_expected: 2
roots_compared_complete: 2
```

Per-root relationship:

```text
root=bm1 comparison_status=DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH declared_resource_blocks=1 state_managed_resource_blocks=1 declared_resource_type_counts=proxmox_vm_qemu=1 state_managed_resource_type_counts=proxmox_vm_qemu=1 matched_resource_type_block_count=1
root=bm2 comparison_status=DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH declared_resource_blocks=1 state_managed_resource_blocks=1 declared_resource_type_counts=proxmox_vm_qemu=1 state_managed_resource_type_counts=proxmox_vm_qemu=1 matched_resource_type_block_count=1
```

Aggregate relationship:

```text
declared_resource_blocks: 2
state_managed_resource_blocks: 2
matched_resource_type_block_count: 2
declared_to_local_state_structural_coverage_status: DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH
```

## Accepted interpretation

For both accepted Terraform roots, the declared resource-type block-count map matches the local-state managed resource-type block-count map. Across both roots, two declared `proxmox_vm_qemu` resource blocks structurally match two local-state managed `proxmox_vm_qemu` resource blocks.

This establishes limited declared-to-local-state structural relationship evidence only.

It does not establish state freshness, authoritative ownership, state completeness, instance identity, live resource existence, provider reachability, plan/apply outcome, drift, or destructive-change status.

A future structural mismatch, if observed, would not by itself be a drift finding. Drift requires separate authoritative runtime/live verification.

## Coverage / outcome boundary

Preserve:

```text
state_backed_coverage_status: UNKNOWN
live_resource_coverage_status: UNKNOWN
plan_result_status: UNKNOWN
apply_result_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
drift_claims: 0
destructive_change_claims: 0
```

The structural match status must not be promoted to any of those stronger claims.

## Trust boundary

The collector reports:

```text
mutation_allowed: False
terraform_cli_invoked: False
provider_api_invoked: False
raw_hcl_projected: False
raw_state_projected: False
resource_names_or_addresses_projected: False
instance_identity_projected: False
state_values_projected: False
tfvars_inspected: False
```

Only aggregate declared resource-type block counts and aggregate local-state managed resource-type block counts were projected.

Raw HCL/state, resource names or addresses, instance keys/identities, state values, outputs, serial/lineage identifiers, provider configuration, real tfvars, endpoints, credentials, and sensitive connection strings were not printed or persisted.

No Terraform CLI, provider API, SSH connection, repository mutation, or infrastructure mutation was performed.

## Next smallest useful step

Reassess the remaining Milestone 6 gaps before adding another probe.

Do not use this structural match to justify a drift or live-resource claim. A next slice should be selected only if it can add materially stronger read-only evidence, such as a safe authoritative live/provider observation or another independently valuable governance signal, without exposing sensitive Terraform state or credentials.
