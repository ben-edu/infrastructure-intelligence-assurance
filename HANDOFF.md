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
accepted main after PR #69: 7990345f42b3df0655d1e0a789e33f6a87ebe5d2
active branch: agent/m6-ansible-execution-outcome-source-discovery
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

Preserve:

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

## Accepted Milestone 6 — Ansible execution-declaration discovery

Report:

```text
docs/reports/2026-08-29-m6-ansible-execution-declaration-discovery.md
```

Accepted validation:

```text
focused tests: 4 passed in 0.09s
full repository suite: 368 passed in 1.59s
discovery_rc: 0
source_status: COMPLETE
candidate_files_selected: 156
candidate_files_scanned: 156
```

Accepted result:

```text
ansible_execution_signal_files: 0
ansible_playbook_declaration_status: NONE_OBSERVED_IN_BOUNDED_SOURCE
ansible_runner_run_declaration_status: NONE_OBSERVED_IN_BOUNDED_SOURCE
ansible_navigator_run_declaration_status: NONE_OBSERVED_IN_BOUNDED_SOURCE
execution_outcome_status: UNKNOWN
execution_success_status: UNKNOWN
idempotence_status: UNKNOWN
live_managed_host_coverage_status: UNKNOWN
configuration_drift_status: UNKNOWN
```

No accepted Ansible execution declaration was observed in the bounded safe Git source. This does not prove that Ansible is never executed manually, through Jenkins, another repository, an operator workstation, or another automation system.

## Active Milestone 6 — Ansible execution-outcome source discovery

Implementation prepared on this branch:

```text
scripts/discovery/m6_ansible_execution_outcome_source_discovery.py
tests/test_ansible_execution_outcome_source_discovery.py
```

Goal:

```text
Identify the safest authoritative source candidate for future Ansible execution-outcome evidence without yet reading build/console logs or executing Ansible.
```

Bounded source order:

```text
1. Jenkins read-only integration capability metadata under the known infrastructure MCP paths
2. management-host systemd unit/timer names with explicit Ansible naming
3. management-host cron filenames with explicit Ansible naming
```

Jenkins capability discovery is filesystem-metadata-only in this slice:

```text
candidate directory count
candidate file count
env-like file count
metadata failures
```

Jenkins file contents, environment values, credential values, API responses, job names, build metadata, and console logs are NOT read in this slice.

Management-host scheduler discovery projects only:

```text
safe systemd unit names containing `ansible`
safe timer names containing `ansible`
safe cron filenames containing `ansible`
```

Unit bodies, timer command bodies, cron contents, journals, raw commands, environment values, host targets, credentials, and Vault material are not read.

Source candidate result vocabulary:

```text
JENKINS_READ_ONLY_SOURCE_CANDIDATE
MANAGEMENT_HOST_SCHEDULER_SOURCE_CANDIDATE
NO_AUTHORITATIVE_OUTCOME_SOURCE_OBSERVED_IN_BOUNDED_DISCOVERY
SOURCE_DISCOVERY_INCOMPLETE
```

These are source-candidate classifications only. Preserve:

```text
execution_outcome_status: UNKNOWN
execution_success_status: UNKNOWN
idempotence_status: UNKNOWN
configuration_drift_status: UNKNOWN
successful_execution_claims: 0
idempotence_claims: 0
drift_claims: 0
```

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m6-ansible-execution-outcome-source-discovery

python3 -m pytest -q \
  tests/test_ansible_execution_outcome_source_discovery.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_ansible_execution_outcome_source_discovery.py

echo "discovery_rc=$?"
```

Acceptance rules:

- focused tests must pass;
- Jenkins candidate files must be inspected by metadata only, never content;
- no Jenkins API call or console-log access is allowed;
- scheduler projection is limited to unit/timer names and cron filenames with explicit Ansible naming;
- no unit body, cron body, journal, raw command, environment value, host target, credential, or Vault material may be read or projected;
- source discovery may select a candidate but must keep execution outcome/success/idempotence/drift `UNKNOWN`;
- if either metadata source is incomplete, do not promote bounded absence to a source conclusion.

## Trust invariants

- infrastructure interaction remains read-only;
- source-candidate discovery is not execution-outcome evidence;
- declared state is not observed state;
- absence of an execution source in bounded discovery is not proof that execution never occurs;
- source artifacts and derived assurance remain separate;
- Terraform state/real tfvars and Ansible Vault/credential material do not enter evidence/AI context;
- host identifiers and sensitive inventory values are not projected;
- `NONE_OBSERVED_IN_BOUNDED_SOURCE` is not universal absence;
- `FAILED_TO_OBSERVE`/`INCOMPLETE` is not negative evidence;
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
