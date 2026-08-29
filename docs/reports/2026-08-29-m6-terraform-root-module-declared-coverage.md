# Milestone 6 — Terraform Root-to-Module Declared Coverage

Date: 2026-08-29
Status: ACCEPTED
Mode: read-only declared-state discovery

## Scope

This slice inspected only Git-tracked `.tf` files in the bounded `afpa-infra-rebuild` repository. It resolved relative local Terraform module relationships in memory and separately located declared resource types by Terraform directory.

Terraform state, real tfvars, provider live APIs, and the Terraform CLI were not used.

## Accepted tests

Root-to-module discovery:

```text
4 passed in 0.09s
```

Declared resource location probe:

```text
2 passed in 0.07s
```

## Accepted root-to-module discovery

```text
source_status: COMPLETE
tracked_tf_files_returned: 15
tracked_tf_files_scanned: 15
excluded_or_unsafe_paths: 0
read_or_decode_skips: 0
oversize_skips: 0

root=terraform/environments/bm1
module_blocks=1
resolved_local_module_relationships=1
resolved_module_directories=terraform/modules/proxmox_vm
reachable_resource_types=NONE_OBSERVED
structural_declared_resource_path_status=RESOLVED_LOCAL_MODULE_WITHOUT_DECLARED_RESOURCE

root=terraform/environments/bm2
module_blocks=1
resolved_local_module_relationships=1
resolved_module_directories=terraform/modules/proxmox_vm
reachable_resource_types=NONE_OBSERVED
structural_declared_resource_path_status=RESOLVED_LOCAL_MODULE_WITHOUT_DECLARED_RESOURCE

root_candidates_total: 2
module_blocks_total: 2
relationships_resolved: 2
roots_with_resolved_local_module: 2
roots_with_declared_resource_path: 0
module_sources_nonlocal: 0
module_sources_not_literal: 0
module_sources_outside_or_unsafe: 0
module_sources_target_not_in_scope: 0
live_resource_coverage_status: UNKNOWN
state_backed_coverage_status: UNKNOWN
drift_claims: 0
destructive_change_claims: 0
discovery_rc: 0
```

## Accepted declared resource location probe

```text
source_status: COMPLETE
tracked_tf_files_returned: 15
tracked_tf_files_scanned: 15
read_or_decode_skips: 0
oversize_skips: 0

directory=terraform/environments/bm1 classification=ROOT_CANDIDATE tf_files=6 declared_resource_types=proxmox_vm_qemu=1
directory=terraform/environments/bm2 classification=ROOT_CANDIDATE tf_files=6 declared_resource_types=proxmox_vm_qemu=1
directory=terraform/modules/proxmox_vm classification=MODULE_DIRECTORY tf_files=3 declared_resource_types=NONE_OBSERVED

terraform_directories_total: 3
directories_with_declared_resources: 2
declared_resource_blocks_total: 2
live_resource_coverage_status: UNKNOWN
state_backed_coverage_status: UNKNOWN
drift_claims: 0
destructive_change_claims: 0
discovery_rc: 0
```

## Accepted interpretation

The two root candidates each resolve one relative local module relationship to `terraform/modules/proxmox_vm`. The resolved module directory contains no declared resource blocks in the bounded Git-tracked source.

The two `proxmox_vm_qemu` resource blocks observed in the earlier inventory are instead declared directly in the root directories:

```text
terraform/environments/bm1 -> direct declared proxmox_vm_qemu block: 1
terraform/environments/bm2 -> direct declared proxmox_vm_qemu block: 1
terraform/modules/proxmox_vm -> declared resource blocks: 0
```

Therefore the structural relationship is:

```text
bm1 -> direct resource declaration + resolved local module relationship
bm2 -> direct resource declaration + resolved local module relationship
local module -> no declared resource block observed
```

This is declared configuration structure only. It does not establish Terraform state membership, runtime instance count, live VM existence, provider reachability, managed-resource coverage, drift, or destructive-change status.

## Trust boundary

Only Git-tracked `.tf` files were read. Relative local module source values were used in memory only for bounded path resolution and were not printed or persisted.

Raw HCL lines, module block names, module source values, resource instance names, variable values, provider/backend values, and sensitive connection strings were not printed.

Terraform state/state backups, real tfvars, `.env` files, secrets, credentials, private keys, certificates, and provider tokens/passwords were not read or printed.

Terraform CLI and provider live APIs were not invoked. No infrastructure or repository mutation was performed by the discovery.
