# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read:

```text
docs/PROJECT_CONTINUITY.md
```

## Resume protocol

1. Read Project Sources.
2. Read `docs/PROJECT_CONTINUITY.md`.
3. Read `HANDOFF.md` from `main`.
4. Check active branches/PRs; prefer a newer branch `HANDOFF.md` for in-flight state.
5. Read only reports/ADRs relevant to the active slice.
6. Prefer repository state and fresh evidence over chat reconstruction.
7. Continue the `Exact next step` unless new evidence invalidates it.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #68: aca9eb51913a319a1b0945d491a0e4d28b265a3b
active branch: agent/m6-ansible-execution-declaration-discovery
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6: ACTIVE
mutation_allowed: false
management host: mgmt-automation
bounded infrastructure repository: /home/ben/projects/afpa-infra-rebuild
```

Closed/unmerged PRs that are not accepted checkpoints:

```text
#65 — closed unmerged; superseded by #66
#67 — accidental temporary PR; closed unmerged
```

## Milestone 5 boundary

Accepted closure report:

```text
docs/reports/2026-08-23-m5-read-only-discovery-closure.md
```

Controlled restore/integrity work remains deferred until explicitly authorized. Do not add M5 probes merely to force preserved unknowns closed.

## Accepted Milestone 6 — Terraform

Reports:

```text
docs/reports/2026-08-29-m6-terraform-declared-state-inventory.md
docs/reports/2026-08-29-m6-terraform-root-module-declared-coverage.md
docs/reports/2026-08-29-m6-terraform-execution-declaration-discovery.md
```

Preserved unknowns:

```text
Terraform state-backed coverage: UNKNOWN
live resource coverage: UNKNOWN
execution outcome: UNKNOWN
plan/apply result: UNKNOWN
drift: UNKNOWN
destructive-change status: UNKNOWN
```

Do not reuse the rejected first Terraform execution scan that contained a gate-only false positive.

## Accepted Milestone 6 — Ansible declared inventory

Report:

```text
docs/reports/2026-08-29-m6-ansible-declared-state-inventory.md
```

Accepted state:

```text
focused tests: 3 passed in 0.09s
full suite before PR #66: 360 passed in 3.52s
inventory files: 5
playbooks: 10
role directories: 7
inventory group declarations: 6
inventory host declarations: 8
managed_host_coverage_status: DECLARED_CONFIGURATION_ONLY
live_managed_host_coverage_status: UNKNOWN
execution_outcome_status: UNKNOWN
configuration_drift_status: UNKNOWN
```

The 8 host declarations are not verified/reachable managed hosts.

## Accepted Milestone 6 — Ansible playbook-to-role declared coverage

Report:

```text
docs/reports/2026-08-29-m6-ansible-playbook-role-declared-coverage.md
```

Accepted validation:

```text
focused tests: 4 passed in 0.10s
full repository suite: 364 passed in 1.51s
discovery_rc: 0
source_status: COMPLETE
playbook_files_scanned: 10
```

Accepted summary:

```text
declared_role_directories_total: 7
referenced_role_directories_total: 7
unreferenced_in_direct_playbook_scope_total: 0
playbooks_with_resolved_local_role: 8
playbooks_with_no_role_reference: 2
playbooks_with_unknown_role_reference: 0
resolved_role_reference_signals: 9
unresolved_role_reference_signals: 0
unparsed_role_structures: 0
declared_role_coverage_status: STRUCTURAL_CONFIGURATION_ONLY
execution_outcome_status: UNKNOWN
idempotence_status: UNKNOWN
configuration_drift_status: UNKNOWN
```

No supported direct role reference was observed in `ansible/playbooks/ping.yml` or `ansible/playbooks/vault-check.yml`. This is bounded direct-reference absence only.

## Active Milestone 6 — Ansible execution-declaration discovery

Implementation prepared on this branch:

```text
scripts/discovery/m6_ansible_execution_declaration_discovery.py
tests/test_ansible_execution_declaration_discovery.py
```

Goal:

```text
Determine whether safe Git-tracked workflow/script text explicitly declares tightly bounded Ansible execution entry points without executing Ansible or exposing raw commands/arguments.
```

Accepted entry-point categories for this slice:

```text
ansible_playbook       -> ansible-playbook
ansible_runner_run     -> ansible-runner run
ansible_navigator_run  -> ansible-navigator run
```

The generic `ansible` command and tooling such as `ansible-lint` are intentionally excluded to reduce ambiguity and false positives.

Safe projection:

```text
safe relative file identifier
execution entry-point category only
gate_signal true/false only on files that also contain an accepted execution entry point
aggregate file/signal counts
```

Do not print or persist:

```text
raw command lines or arguments
playbook/inventory argument values
host targets/IPs
runtime facts
environment values
credentials, keys, tokens, Vault password material
connection strings
```

Preserve:

```text
execution_outcome_status: UNKNOWN
execution_success_status: UNKNOWN
idempotence_status: UNKNOWN
live_managed_host_coverage_status: UNKNOWN
configuration_drift_status: UNKNOWN
```

Gate-only files must not enter Ansible execution evidence. `NONE_OBSERVED_IN_BOUNDED_SOURCE` is bounded absence only.

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m6-ansible-execution-declaration-discovery

python3 -m pytest -q \
  tests/test_ansible_execution_declaration_discovery.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_ansible_execution_declaration_discovery.py

echo "discovery_rc=$?"
```

Acceptance rules:

- focused tests must pass;
- source status must be `COMPLETE`;
- raw commands/arguments or sensitive values must not appear in evidence;
- gate-only files must be excluded;
- generic `ansible`/`ansible-lint` must not be promoted to accepted execution entry points;
- no Ansible, Jenkins, GitHub Actions, SSH, or managed-host connection may be invoked;
- no execution success, idempotence, reachability, runtime fact, or drift result may be inferred.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- declared execution entry point is not execution outcome evidence;
- source artifacts and derived assurance remain separate;
- Terraform state/real tfvars and Ansible Vault/credential material do not enter evidence/AI context;
- host identifiers and sensitive inventory values are not projected;
- `NONE_OBSERVED_IN_BOUNDED_SOURCE` is not universal absence;
- `FAILED_TO_OBSERVE` is not negative evidence;
- no drift, execution success, idempotence, compliance, or destructive-change result is inferred without authoritative evidence;
- unknowns are not forced closed;
- no secrets, credentials, private keys, raw sensitive configuration, or sensitive connection strings enter evidence/AI context;
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
