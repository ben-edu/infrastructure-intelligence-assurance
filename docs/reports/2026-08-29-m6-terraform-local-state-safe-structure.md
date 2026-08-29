# Milestone 6 — Terraform Local-State Safe Structural Aggregation

Date: 2026-08-29
Status: ACCEPTED
Mode: read-only / process-local state parsing / aggregate projection only

## Scope

This report records a tightly bounded local Terraform state structural aggregation for the two previously accepted Terraform roots.

Bounded state sources:

```text
terraform/environments/bm1/terraform.tfstate
terraform/environments/bm2/terraform.tfstate
```

The state files were parsed only inside the local process on `mgmt-automation`. Only explicitly allowlisted aggregate structure was projected.

## Validation

Focused tests:

```text
4 passed in 0.05s
```

Repository-wide regression gate:

```text
395 passed in 1.74s
```

Accepted live discovery:

```text
discovery_rc=0
source_mode: LOCAL_TERRAFORM_STATE_PROCESS_LOCAL_SAFE_STRUCTURE_ONLY
source_status: COMPLETE
roots_expected: 2
roots_parsed_complete: 2
```

Per-root safe structure:

```text
root=bm1 parse_status=COMPLETE managed_resource_blocks=1 data_resource_blocks=0 managed_instances=2 data_instances=0
root=bm2 parse_status=COMPLETE managed_resource_blocks=1 data_resource_blocks=0 managed_instances=4 data_instances=0
```

Aggregate safe structure:

```text
managed_resource_blocks: 2
data_resource_blocks: 0
other_resource_blocks: 0
managed_instances: 6
data_instances: 0
other_instances: 0
managed_resource_type_counts: proxmox_vm_qemu=2
state_structure_status: STRUCTURAL_AGGREGATE_OBSERVED
```

## Accepted interpretation

Both observed local Terraform state files parsed successfully within the bounded collector and expose safe aggregate structure.

The aggregate local state contains two managed resource blocks and six managed instances. The only projected managed resource-type category is `proxmox_vm_qemu`, with two resource blocks across the two roots.

These are structural state aggregates only. They do not establish that the local state is current, authoritative, complete, aligned with declared configuration, or aligned with live infrastructure.

The difference between resource-block count and instance count is normal structural state evidence and must not be interpreted as drift or coverage without a separate relationship check.

## Coverage / outcome boundary

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

A successfully parsed local state structure is local state evidence only. It is not proof of state freshness, authoritative ownership, live resource existence, declared-to-state coverage, plan/apply success, drift, or destructive-change status.

## Trust boundary

The collector reports:

```text
mutation_allowed: False
terraform_cli_invoked: False
provider_api_invoked: False
raw_state_projected: False
state_values_projected: False
resource_addresses_projected: False
resource_names_projected: False
instance_keys_projected: False
outputs_projected: False
serial_or_lineage_projected: False
provider_configuration_projected: False
```

Terraform state was parsed only process-locally to compute allowlisted aggregate structure.

Raw state JSON, attribute values, resource names or addresses, instance keys/indexes, outputs or output values, serial/lineage identifiers, provider configuration strings/aliases, endpoints, credentials, sensitive attributes, and private connection data were not printed or persisted.

Sensitive-looking resource-type categories are redacted before projection.

No Terraform CLI, provider API, SSH connection, repository mutation, or infrastructure mutation was performed.

## Next smallest useful step

Perform a separate bounded **Terraform declared-to-local-state structural coverage** slice.

That relationship may compare only aggregate non-sensitive declared resource-type block counts against aggregate local-state managed resource-type block counts per accepted root. It must not expose resource names, addresses, instance identities, state values, provider configuration, tfvars, endpoints, credentials, or raw state.

A structural type/count relationship may establish limited declared-to-state structural coverage only. It still must not be promoted to live resource coverage, state freshness, plan/apply success, drift, or destructive-change evidence.
