# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #73: ad652d64d6206b0e4ff33ea511f0499447d8c45f
active branch: agent/m6-terraform-runtime-artifact-source
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6: ACTIVE
mutation_allowed: false
management host: mgmt-automation
bounded infrastructure repository: /home/ben/projects/afpa-infra-rebuild
```

## Accepted Milestone 6 — Terraform

Reports:

```text
docs/reports/2026-08-29-m6-terraform-declared-state-inventory.md
docs/reports/2026-08-29-m6-terraform-root-module-declared-coverage.md
docs/reports/2026-08-29-m6-terraform-execution-declaration-discovery.md
```

Accepted bounded Terraform structure:

```text
root candidates: terraform/environments/bm1, terraform/environments/bm2
module directory: terraform/modules/proxmox_vm
backend blocks observed in Git-tracked .tf: 0
provider type: proxmox
resource type: proxmox_vm_qemu
execution declaration files in bounded workflow/script source: 0
managed_resource_coverage_status: DECLARED_CONFIGURATION_ONLY
```

Preserve:

```text
Terraform state-backed coverage: UNKNOWN
Terraform live resource coverage: UNKNOWN
Terraform plan result: UNKNOWN
Terraform apply result: UNKNOWN
Terraform drift: UNKNOWN
Terraform destructive-change status: UNKNOWN
```

No Terraform state or real tfvars content has entered evidence/AI context.

## Accepted Milestone 6 — Ansible/Jenkins path

Accepted reports include:

```text
docs/reports/2026-08-29-m6-ansible-declared-state-inventory.md
docs/reports/2026-08-29-m6-ansible-playbook-role-declared-coverage.md
docs/reports/2026-08-29-m6-ansible-execution-declaration-discovery.md
docs/reports/2026-08-29-m6-ansible-execution-outcome-source-discovery.md
docs/reports/2026-08-29-m6-jenkins-ansible-outcome-capability.md
docs/reports/2026-08-29-m6-jenkins-api-metadata-probe.md
docs/reports/2026-08-29-m6-ansible-jenkins-relationship-source-discovery.md
```

Latest accepted full suite before PR #73:

```text
387 passed in 1.76s
```

Jenkins-to-Ansible relationship path is closed within the current evidence boundary:

```text
relationship_source_status: NONE_OBSERVED_IN_BOUNDED_SOURCE
Ansible execution outcome/success/idempotence/drift: UNKNOWN
```

Do not add more Jenkins-to-Ansible relationship probes without materially stronger safe evidence.

Rejected observations that must not be reused:

```text
Jenkins API first connection attempt: NOT_ATTEMPTED / FAILED_TO_OBSERVE
Ansible-to-Jenkins first relationship scan: SOURCE_INCOMPLETE due one skipped candidate
```

## Active Milestone 6 — Terraform runtime-artifact source discovery

Implementation prepared on this branch:

```text
scripts/discovery/m6_terraform_runtime_artifact_source_discovery.py
tests/test_terraform_runtime_artifact_source_discovery.py
```

Goal:

```text
Determine whether the two previously accepted Terraform root candidates expose local runtime-artifact metadata that could qualify a later safe state/workspace/plan evidence source.
```

This slice is filesystem-metadata-only. It does not open Terraform runtime artifacts and does not invoke Terraform.

Bounded roots:

```text
terraform/environments/bm1
terraform/environments/bm2
```

Generic metadata classes only:

```text
.terraform working directory existence
terraform.tfstate existence
terraform.tfstate.backup existence
terraform.tfstate.d existence
aggregate workspace-directory count without workspace names
.terraform/terraform.tfstate backend-metadata candidate existence
.terraform/environment workspace-selection metadata candidate existence
narrow top-level saved-plan candidates: tfplan / *.tfplan
```

Explicitly prohibited:

```text
opening or parsing state/state-backup/backend/workspace/plan files
reading real tfvars
printing workspace names
printing artifact-specific filenames beyond generic Terraform conventions
printing resource addresses, provider values, endpoints, credentials, commands, or connection strings
Terraform CLI/provider API invocation
```

Interpretation boundary:

```text
runtime artifact metadata != state-backed coverage
runtime artifact metadata != current/authoritative Terraform state
saved plan metadata != plan outcome
working directory metadata != successful init/apply
filesystem absence != absence of remote state or external CI execution
```

Preserve regardless of result:

```text
state_backed_coverage_status: UNKNOWN
live_resource_coverage_status: UNKNOWN
plan_result_status: UNKNOWN
apply_result_status: UNKNOWN
drift_status: UNKNOWN
destructive_change_status: UNKNOWN
```

Fail closed:

```text
missing expected root => SOURCE_INCOMPLETE
metadata lookup failure => SOURCE_INCOMPLETE
relevant symlink => SOURCE_INCOMPLETE
```

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m6-terraform-runtime-artifact-source

python3 -m pytest -q \
  tests/test_terraform_runtime_artifact_source_discovery.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_terraform_runtime_artifact_source_discovery.py

echo "discovery_rc=$?"
```

Acceptance rules:

- focused tests must pass;
- bounded roots must be observed completely for bounded absence to be accepted;
- no Terraform artifact contents may be opened;
- no Terraform CLI/provider API may be invoked;
- symlink/metadata failures remain incomplete observation, not negative evidence;
- runtime artifact metadata must not be promoted to state-backed coverage, plan/apply result, drift, or destructive-change evidence.

If a safe local runtime-artifact candidate is observed, use the result only to decide whether a later aggregate read-only verification is justified. If none is observed in a complete scan, record bounded local-artifact absence and do not infer that remote/external Terraform state does not exist.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- bounded absence is not universal absence;
- `FAILED_TO_OBSERVE`/`INCOMPLETE` is not negative evidence;
- Terraform state/real tfvars and Ansible variable/Vault/credential material do not enter evidence/AI context;
- no raw commands, arguments, environment values, credentials, host targets, console logs, job configuration bodies, build parameters, or sensitive connection strings enter evidence/AI context;
- no drift, execution success, idempotence, compliance, or destructive-change result is inferred without authoritative evidence;
- unknowns are not forced closed;
- generated operational artifacts keep `mutation_allowed=false`.

## Continuity rule

At every accepted slice before merge:

1. create/update the accepted report when reusable evidence changed;
2. update `HANDOFF.md` with accepted SHA context, evidence, preserved unknowns, trust boundary, merge gate, and exact next step;
3. update roadmap/current-state/README only when milestone status, architecture, or user-facing project status materially changes;
4. ensure no temporary/debug/placeholder files remain;
5. run focused tests and a full repository suite when reusable implementation/contracts change materially;
6. inspect PR scope and mergeability and squash-merge when clean;
7. carry the new accepted `main` SHA into the next branch handoff.
