# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #71: b8e962b8895bde867a425b5161aea07e938ea97f
active branch: agent/m6-jenkins-api-metadata-probe
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

Preserve Terraform state-backed coverage, live resource coverage, execution outcome, plan/apply result, drift, and destructive-change status as `UNKNOWN` unless stronger authoritative evidence is added. Do not reuse the rejected first Terraform execution scan containing the gate-only false positive.

## Accepted Milestone 6 — Ansible declared/source path

Accepted reports:

```text
docs/reports/2026-08-29-m6-ansible-declared-state-inventory.md
docs/reports/2026-08-29-m6-ansible-playbook-role-declared-coverage.md
docs/reports/2026-08-29-m6-ansible-execution-declaration-discovery.md
docs/reports/2026-08-29-m6-ansible-execution-outcome-source-discovery.md
docs/reports/2026-08-29-m6-jenkins-ansible-outcome-capability.md
```

Accepted bounded state:

```text
inventory files: 5
playbooks: 10
role directories: 7
inventory group declarations: 6
inventory host declarations: 8
referenced local role directories: 7/7
bounded workflow/script files scanned for Ansible execution declarations: 156
accepted Ansible execution declaration files: 0
preferred runtime outcome source candidate: JENKINS_READ_ONLY_SOURCE_CANDIDATE
Jenkins integration source capability: JOB_AND_BUILD_METADATA_CAPABILITY_SIGNAL_OBSERVED
latest accepted full suite before PR #71: 376 passed in 1.63s
```

Preserve:

```text
live managed host coverage: UNKNOWN
Ansible execution outcome: UNKNOWN
Ansible execution success: UNKNOWN
idempotence: UNKNOWN
configuration drift: UNKNOWN
```

## Active Milestone 6 — Jenkins API metadata-only probe

Implementation:

```text
scripts/discovery/m6_jenkins_api_metadata_probe.py
tests/test_jenkins_api_metadata_probe.py
```

Report recorded on this branch:

```text
docs/reports/2026-08-29-m6-jenkins-api-metadata-probe.md
```

### First attempt — failed observation, not negative evidence

```text
focused tests: 4 passed in 0.08s
connection_config_status: CONNECTION_CONFIG_UNAVAILABLE
env_files_observed: 1
env_files_read_for_approved_keys: 0
jenkins_api_invoked: False
api_observation_status: NOT_ATTEMPTED
jobs_total: 0
discovery_rc: 2
```

Do not interpret the first attempt's `jobs_total: 0` as Jenkins having zero jobs. No API call occurred.

### Retry fix

The parser now:

```text
accepts only explicit JENKINS_-scoped connection keys
supports URL/ENDPOINT, USER/USERNAME, TOKEN/PASSWORD/API_KEY roles
supports `export KEY=value`
rejects generic URL/TOKEN/PASSWORD variables
fails closed on multiple distinct values for one role
never projects connection key names or values
```

### Successful live retry — accepted Jenkins runtime metadata

```text
focused tests: 5 passed in 0.06s
discovery_rc: 0
connection_config_status: CONNECTION_CONFIG_READY
env_files_observed: 1
env_files_read_for_approved_keys: 1
credential_material_loaded_locally: True
credential_values_projected: False
endpoint_value_projected: False
jenkins_api_invoked: True
api_observation_status: COMPLETE
jobs_total: 25
jobs_with_last_build_metadata: 11
ansible_name_signal_jobs: 0
ansible_name_signal_jobs_with_last_build_metadata: 0
last_build_result_counts: SUCCESS=11
ansible_name_signal_last_build_result_counts: NONE_OBSERVED
```

Interpretation boundary:

```text
This is accepted Jenkins runtime metadata evidence.
It is NOT accepted Ansible execution-outcome evidence.
The 11 SUCCESS values are Jenkins last-build result categories only.
No weak `ansible` token was observed in in-memory job names; this is bounded weak-name absence only.
Job names and build numbers were not projected.
```

Preserve:

```text
Ansible execution_outcome_status: UNKNOWN
Ansible execution_success_status: UNKNOWN
idempotence_status: UNKNOWN
configuration_drift_status: UNKNOWN
successful_execution_claims: 0
idempotence_claims: 0
drift_claims: 0
```

## Runtime trust boundary

```text
mutation_allowed: False
HTTP method: GET only
permitted endpoint class: root /api/json only
restricted tree: jobs[name,color,lastBuild[number,result,timestamp,building]]
console logs inspected: False
job config bodies inspected: False
build parameters inspected: False
credential values projected: False
endpoint value projected: False
Ansible CLI invoked: False
SSH performed: False
```

No console log, `config.xml`, build parameter, environment value, raw command, inventory argument, host target, Vault material, job name, build number, endpoint value, or credential value entered evidence output.

## Merge gate — PENDING

Focused tests and live retry passed. Because reusable implementation/tests changed, run the full repository suite before PR/merge.

## Exact next step

On `mgmt-automation` run only:

```bash
cd ~/projects/infrastructure-intelligence-assurance
python3 -m pytest -q
```

Do not use strict interactive shell mode.

If the full suite passes:

1. record the exact pass count in this handoff/report/PR;
2. inspect changed-file scope and ensure no temporary/debug/placeholder files exist;
3. create/inspect a non-draft PR and squash-merge when clean;
4. carry the new accepted `main` SHA into the next branch handoff;
5. start a bounded **Ansible-to-Jenkins relationship source discovery**.

The next slice must determine whether any safe authoritative metadata source can relate a Jenkins job/build to Ansible execution without reading console logs, job configuration bodies, build parameters, raw command bodies, credentials, or sensitive host/inventory data.

If no safe relationship source exists, preserve Ansible execution outcome as `UNKNOWN` and stop widening this evidence path merely to eliminate the unknown.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- Jenkins integration capability is not Jenkins runtime evidence;
- Jenkins runtime metadata is not automatically Ansible execution evidence;
- bounded absence is not universal absence;
- `FAILED_TO_OBSERVE`/`INCOMPLETE` is not negative evidence;
- Terraform state/real tfvars and Ansible Vault/credential material do not enter evidence/AI context;
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
