# Milestone 6 — Terraform Declared-State Inventory

Date: 2026-08-29
Status: ACCEPTED
Mode: read-only / configuration-only

## Scope

This slice created a bounded structural inventory of Git-tracked Terraform configuration in the known infrastructure repository.

Bounded source:

```text
repository alias: afpa-infra-rebuild
source path: /home/ben/projects/afpa-infra-rebuild
source mode: GIT_TRACKED_TF_ONLY
```

The discovery did not inspect Terraform state or real tfvars, did not invoke the Terraform CLI, and did not perform provider live verification.

## Accepted focused tests

```text
4 passed in 0.42s
```

## Accepted live discovery

```text
source_status: COMPLETE
tracked_tf_files_returned: 15
tracked_tf_files_scanned: 15
excluded_or_unsafe_paths: 0
read_or_decode_skips: 0
oversize_skips: 0
```

Terraform directory inventory:

```text
terraform/environments/bm1  ROOT_CANDIDATE   tf_files=6
terraform/environments/bm2  ROOT_CANDIDATE   tf_files=6
terraform/modules/proxmox_vm MODULE_DIRECTORY tf_files=3
```

Safe declaration projection:

```text
backend_types: NONE_OBSERVED
provider_types: proxmox=2
resource_types: proxmox_vm_qemu=2
data_source_types: NONE_OBSERVED
```

Structural counts:

```text
terraform_directories_total: 3
root_candidates_heuristic: 2
module_directories_heuristic: 1
backend_blocks: 0
provider_blocks: 2
resource_blocks: 2
data_blocks: 0
module_blocks: 2
variable_blocks: 19
output_blocks: 5
cloud_blocks: 0
workspaces_blocks: 0
managed_resource_coverage_status: DECLARED_CONFIGURATION_ONLY
live_resource_coverage_status: UNKNOWN
drift_claims: 0
destructive_change_claims: 0
discovery_rc: 0
```

## Accepted interpretation

The current Git-tracked Terraform configuration exposes two structural root candidates (`bm1` and `bm2`) and one module-directory candidate (`proxmox_vm`). These classifications are heuristics based on repository structure and are not authoritative Terraform stack or workspace identities.

The configuration declares the `proxmox` provider and the `proxmox_vm_qemu` resource type. This is declared-state evidence only. It does not establish that corresponding live resources exist, that Terraform currently manages them, that provider connectivity works, or that state is current.

No backend block was observed in the bounded Git-tracked `.tf` source. This means only that no backend declaration was observed in this source. It does not establish that no backend or state exists elsewhere or through Terraform defaults/runtime configuration.

No drift, destructive-change, plan, apply, or live managed-resource coverage claim is permitted from this slice.

## Trust boundary

Only Git-tracked `.tf` files were read.

The discovery did not print raw HCL lines, resource instance names, variable names/defaults, output names/values, provider configuration values, backend values, or module source values.

Terraform state/state backups, real tfvars, `.env` files, credentials, secrets, private keys, certificates, provider tokens/passwords, and sensitive connection strings were not read or printed.

The Terraform CLI was not invoked. No `init`, `plan`, `show`, `state`, `import`, `apply`, `destroy`, `refresh`, or provider live call was performed.

No repository or infrastructure mutation was performed.

## Next bounded step

Create a safe Terraform root-to-module declared-coverage relationship.

The next slice should determine, from Git-tracked `.tf` structure only:

```text
which root candidates contain module blocks
which local module-directory candidates are referenced by root candidates
which declared resource types are implemented by the referenced local module
whether each current root candidate has a structurally resolvable declared resource path
```

Do not print module source values or resource instance names. A local-module relationship may be projected only after safely resolving a source path inside the bounded repository. Keep live resource coverage, Terraform state coverage, drift, plan/apply status, and provider reachability `UNKNOWN`.
