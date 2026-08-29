# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #76: 88c4458b59a9e24d92cd6d7671be15d6525d7120
active branch: agent/m6-terraform-readonly-plan-evidence
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6: ACTIVE
mutation_allowed: false
management host: mgmt-automation
bounded infrastructure repository: /home/ben/projects/afpa-infra-rebuild
```

## Accepted Milestone 6 — Terraform evidence

Accepted reports:

```text
docs/reports/2026-08-29-m6-terraform-declared-state-inventory.md
docs/reports/2026-08-29-m6-terraform-root-module-declared-coverage.md
docs/reports/2026-08-29-m6-terraform-execution-declaration-discovery.md
docs/reports/2026-08-29-m6-terraform-runtime-artifact-source-discovery.md
docs/reports/2026-08-29-m6-terraform-local-state-safe-structure.md
docs/reports/2026-08-29-m6-terraform-declared-to-local-state-structural-coverage.md
```

Accepted bounded Terraform state:

```text
root candidates: terraform/environments/bm1, terraform/environments/bm2
provider type: proxmox
declared resource type: proxmox_vm_qemu
local states parsed complete: 2/2 roots
local-state managed resource blocks: 2
local-state managed instances: 6
declared-to-local-state structural relationship: DECLARED_TO_LOCAL_STATE_STRUCTURAL_MATCH
matched declared/state resource-type blocks: 2/2
latest accepted full suite: 399 passed in 2.11s
```

Preserve from prior slices:

```text
Terraform state-backed coverage: UNKNOWN
Terraform live resource coverage: UNKNOWN
Terraform apply result: UNKNOWN
```

The declared-to-local-state structural match is not state freshness, live coverage, drift, or authoritative-state evidence.

## Accepted Milestone 6 — Ansible/Jenkins path

```text
relationship_source_status: NONE_OBSERVED_IN_BOUNDED_SOURCE
Ansible execution outcome: UNKNOWN
Ansible execution success: UNKNOWN
Ansible idempotence: UNKNOWN
Ansible configuration drift: UNKNOWN
```

Do not add more Jenkins-to-Ansible relationship probes without materially stronger safe evidence.

Rejected/failed observations that must not be reused as negative evidence:

```text
Jenkins API first connection attempt: NOT_ATTEMPTED / FAILED_TO_OBSERVE
Ansible-to-Jenkins first relationship scan: SOURCE_INCOMPLETE due one skipped candidate
GitHub connector lookup of ben-edu/afpa-infra-rebuild during M6 gap reassessment returned 404; local /home/ben/projects/afpa-infra-rebuild remains the accepted bounded source and the connector result is not source-absence evidence
```

## Milestone 6 gap reassessment after PR #76

Roadmap gaps still materially open:

Terraform:

```text
plan metadata
drift
destructive-change detection
apply metadata
live-resource coverage
```

Ansible:

```text
live managed-host coverage
execution outcomes
configuration drift where measurable
```

The next slice is selected because it can add materially stronger read-only evidence for three Terraform gaps without apply or infrastructure mutation.

## Active slice — Terraform read-only plan evidence

Implementation:

```text
scripts/discovery/m6_terraform_readonly_plan_evidence.py
tests/test_terraform_readonly_plan_evidence.py
```

Bounded roots:

```text
/home/ben/projects/afpa-infra-rebuild/terraform/environments/bm1
/home/ben/projects/afpa-infra-rebuild/terraform/environments/bm2
```

Two plan modes are executed per root:

```text
configuration_vs_state: terraform plan with refresh=false
refresh_only: terraform plan with refresh-only provider observation
```

Common safety flags/behavior:

```text
-input=false
-lock=false
-detailed-exitcode
-json
no -out
no apply/import/state mutation command
stdout/stderr captured process-locally only
```

Permitted projection:

```text
per-root plan observation status
Terraform exit code 0/2 when complete
aggregate allowlisted action-category counts
configuration plan complete/incomplete status
bounded state-tracked refresh drift signal status
destructive-change status from recognized configuration-plan actions only
```

Explicitly prohibited projection:

```text
raw Terraform plan JSON or diagnostics
resource names or addresses
instance identities
state/tfvars values
provider configuration values
endpoints or credentials
sensitive connection strings
```

Interpretation rules:

```text
configuration_vs_state plan != live drift check
refresh-only change signal = bounded state-tracked provider difference signal, not universal live-resource drift
refresh-only no-change result = bounded alignment for state-tracked resources only
configuration plan delete/replace action = destructive proposal evidence within bounded roots
rc=2 with unclassified actions => destructive_change_status remains UNKNOWN
plan result != apply result
plan/refresh evidence != full live-resource coverage
```

Preserve regardless of result:

```text
apply_result_status: UNKNOWN
live_resource_coverage_status: UNKNOWN
state_backed_coverage_status: UNKNOWN
```

If either mode fails for any root, observation is incomplete and no bounded absence/no-drift conclusion may be made for the failed scope.

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m6-terraform-readonly-plan-evidence

python3 -m pytest -q \
  tests/test_terraform_readonly_plan_evidence.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_terraform_readonly_plan_evidence.py

echo "discovery_rc=$?"
```

Do not use strict interactive shell mode.

Acceptance rules:

- focused tests must pass;
- no Terraform apply/import/state mutation command may run;
- no saved plan may be written and state locking must remain disabled;
- raw stdout/stderr, resource identity, state/tfvars values, provider values, endpoints, and credentials must not enter evidence output;
- `configuration_vs_state` and `refresh_only` must both complete for both roots before source status is COMPLETE;
- provider reads in refresh-only mode are observation-only;
- failed/unclassified observation must preserve UNKNOWN rather than infer absence;
- a complete result may establish only bounded plan/destructive/state-tracked drift evidence, never universal live-resource coverage or apply success.

If live acceptance succeeds, create an accepted report, run the full repository suite, inspect exact four-file scope, then PR/squash-merge. Reassess M6 again after that slice rather than automatically adding another probe.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed/live state;
- local state structure is not live resource evidence;
- provider reads are observation only;
- bounded absence is not universal absence;
- `FAILED_TO_OBSERVE`/`INCOMPLETE` is not negative evidence;
- raw Terraform state/plan/real tfvars and Ansible Vault/credential material do not enter evidence/AI context;
- only explicitly safe aggregate structure/status data may enter evidence;
- no apply success or universal drift/coverage claim is inferred without authoritative evidence;
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
7. carry the new accepted `main` SHA into the next checkpoint.
