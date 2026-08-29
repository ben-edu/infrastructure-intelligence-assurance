# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only the report/ADR for the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #70: 1f672b56f807cceba5469f63644fde6eac3811f8
active branch: agent/m6-jenkins-ansible-outcome-capability
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

Preserve Terraform state-backed coverage, live resource coverage, execution outcome, plan/apply result, drift, and destructive-change status as `UNKNOWN` unless stronger authoritative evidence is added.

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

## Accepted Milestone 6 — Ansible playbook-to-role declared coverage

Report:

```text
docs/reports/2026-08-29-m6-ansible-playbook-role-declared-coverage.md
```

Accepted summary:

```text
focused tests: 4 passed in 0.10s
full suite: 364 passed in 1.51s
playbooks scanned: 10
declared role directories: 7
referenced role directories: 7
playbooks with resolved local role: 8
playbooks with no direct role reference: 2
unresolved role references: 0
unparsed role structures: 0
execution_outcome_status: UNKNOWN
idempotence_status: UNKNOWN
configuration_drift_status: UNKNOWN
```

## Accepted Milestone 6 — Ansible execution-declaration discovery

Report:

```text
docs/reports/2026-08-29-m6-ansible-execution-declaration-discovery.md
```

Accepted result:

```text
focused tests: 4 passed in 0.09s
full suite: 368 passed in 1.59s
candidate files scanned: 156
ansible execution signal files: 0
ansible-playbook: NONE_OBSERVED_IN_BOUNDED_SOURCE
ansible-runner run: NONE_OBSERVED_IN_BOUNDED_SOURCE
ansible-navigator run: NONE_OBSERVED_IN_BOUNDED_SOURCE
execution outcome/success/idempotence/drift: UNKNOWN
```

Bounded declaration absence does not prove Ansible is never executed elsewhere.

## Accepted Milestone 6 — Ansible execution-outcome source discovery

Report:

```text
docs/reports/2026-08-29-m6-ansible-execution-outcome-source-discovery.md
```

Accepted validation and source selection:

```text
focused tests: 4 passed in 0.06s
full suite: 372 passed in 1.66s
discovery_rc: 0
jenkins_source_candidate_status: CONFIG_CANDIDATE_OBSERVED
candidate_directories_observed: 1
candidate_files_observed: 4
env_like_files_observed: 1
metadata_failures: 0
management-host scheduler source_status: COMPLETE
ansible unit/timer/cron names: NONE_OBSERVED
preferred_source_candidate: JENKINS_READ_ONLY_SOURCE_CANDIDATE
execution outcome/success/idempotence/drift: UNKNOWN
```

A Jenkins configuration candidate is not evidence that Jenkins orchestrates Ansible or that any build ran.

## Active Milestone 6 — Jenkins read-only Ansible outcome capability probe

Implementation prepared on this branch:

```text
scripts/discovery/m6_jenkins_ansible_outcome_capability_probe.py
tests/test_jenkins_ansible_outcome_capability_probe.py
```

Goal:

```text
Determine whether the bounded Jenkins read-only integration source appears capable of enumerating safe job/build metadata, without invoking Jenkins and without reading sensitive integration data.
```

The probe reads only non-sensitive source-code files under the bounded Jenkins integration roots and classifies identifier-level signals. It excludes `.env` and secret/credential/password/token/private-key-like filenames before content reads.

Safe capability vocabulary:

```text
JOB_AND_BUILD_METADATA_CAPABILITY_SIGNAL_OBSERVED
PARTIAL_METADATA_CAPABILITY_SIGNAL_OBSERVED
NONE_OBSERVED_IN_BOUNDED_INTEGRATION_SOURCE
NO_INTEGRATION_SOURCE_OBSERVED
SOURCE_INCOMPLETE
```

Console/config capability signals, if present, are counted only to keep them explicitly outside the permitted evidence path. Their contents are not accessed through Jenkins.

Preserve regardless of source-code capability result:

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

git switch --track origin/agent/m6-jenkins-ansible-outcome-capability

python3 -m pytest -q \
  tests/test_jenkins_ansible_outcome_capability_probe.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_jenkins_ansible_outcome_capability_probe.py

echo "discovery_rc=$?"
```

Acceptance rules:

- focused tests must pass;
- source status must not be `INCOMPLETE`;
- `.env` and sensitive-named files must be excluded before reads;
- no raw source lines, URL/endpoint values, command arguments, environment values, credentials, console logs, job config bodies, build parameters, inventory arguments, or host targets may be projected;
- no Jenkins API, Ansible CLI, or SSH invocation is allowed;
- capability signals must not be promoted to execution outcome/success/idempotence/drift evidence.

## Trust invariants

- infrastructure interaction remains read-only;
- integration source-code capability is not observed Jenkins runtime capability;
- Jenkins runtime capability is not execution-outcome evidence;
- declared state is not observed state;
- bounded absence is not universal absence;
- `FAILED_TO_OBSERVE`/`INCOMPLETE` is not negative evidence;
- Terraform state/real tfvars and Ansible Vault/credential material do not enter evidence/AI context;
- no raw commands, arguments, environment values, credentials, host targets, or sensitive connection strings enter evidence/AI context;
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
