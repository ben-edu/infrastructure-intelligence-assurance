# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only reports/ADRs relevant to the active slice.

## Active checkpoint

```text
repository: ben-edu/infrastructure-intelligence-assurance
accepted main after PR #72: 2ca3faeae0ad29c142ee7c24a019b43e61f84971
active branch: agent/m6-ansible-jenkins-relationship-source
package on accepted main: 0.27.0
Milestone 5 overall: NOT COMPLETE
Milestone 5 read-only source discovery: COMPLETE FOR CURRENT AUTHORITATIVE SOURCES
Milestone 6: ACTIVE
mutation_allowed: false
management host: mgmt-automation
bounded infrastructure repository: /home/ben/projects/afpa-infra-rebuild
```

## Accepted Milestone 6 reports

```text
docs/reports/2026-08-29-m6-terraform-declared-state-inventory.md
docs/reports/2026-08-29-m6-terraform-root-module-declared-coverage.md
docs/reports/2026-08-29-m6-terraform-execution-declaration-discovery.md
docs/reports/2026-08-29-m6-ansible-declared-state-inventory.md
docs/reports/2026-08-29-m6-ansible-playbook-role-declared-coverage.md
docs/reports/2026-08-29-m6-ansible-execution-declaration-discovery.md
docs/reports/2026-08-29-m6-ansible-execution-outcome-source-discovery.md
docs/reports/2026-08-29-m6-jenkins-ansible-outcome-capability.md
docs/reports/2026-08-29-m6-jenkins-api-metadata-probe.md
```

Accepted bounded state before this active slice:

```text
Ansible declared inventory files: 5
Ansible playbooks: 10
Ansible role directories: 7
referenced local role directories: 7/7
accepted Ansible execution declaration files in bounded safe Git source: 0
Jenkins API observation: COMPLETE
Jenkins jobs observed: 25
jobs with last-build metadata: 11
Jenkins last-build categories: SUCCESS=11
weak in-memory ansible-name-signal jobs: 0
latest accepted full suite before PR #72: 381 passed in 1.72s
```

Rejected Jenkins API observation that must not be reused:

```text
first connection attempt: CONNECTION_CONFIG_UNAVAILABLE
jenkins_api_invoked: False
api_observation_status: NOT_ATTEMPTED
zero job values from that attempt are FAILED_TO_OBSERVE, not negative evidence
```

Preserve:

```text
Terraform live/state-backed coverage: UNKNOWN
Terraform execution outcome/plan/apply/drift/destructive status: UNKNOWN
live Ansible managed-host coverage: UNKNOWN
Ansible execution outcome: UNKNOWN
Ansible execution success: UNKNOWN
idempotence: UNKNOWN
configuration drift: UNKNOWN
```

The eleven Jenkins `SUCCESS` values are Jenkins last-build metadata only and are not Ansible success evidence.

## Active Milestone 6 — Ansible-to-Jenkins relationship source discovery

Implementation:

```text
scripts/discovery/m6_ansible_jenkins_relationship_source_discovery.py
tests/test_ansible_jenkins_relationship_source_discovery.py
```

Report recorded on this branch:

```text
docs/reports/2026-08-29-m6-ansible-jenkins-relationship-source-discovery.md
```

Relationship acceptance rule:

```text
explicit Jenkins context
AND one accepted Ansible execution entry point in the same safe tracked text file:
  ansible-playbook
  ansible-runner run
  ansible-navigator run
```

Generic `jenkins` / `ansible` token co-occurrence does not count.

### First live attempt — rejected for bounded absence

```text
focused tests: 4 passed in 0.06s
source_status: INCOMPLETE
candidate_files_selected: 158
candidate_files_scanned: 157
read_or_decode_skips: 0
oversize_skips: 1
explicit_relationship_signal_files: 0
relationship_source_status: SOURCE_INCOMPLETE
discovery_rc: 2
```

This is `FAILED_TO_OBSERVE / INCOMPLETE`. Do not reuse its zero relationship count as negative evidence.

### Retry fix

The old `512 KiB` whole-file ceiling was replaced by bounded streaming with an `8 MiB` hard ceiling. Raw source content is neither retained as evidence nor printed. Files above the hard ceiling or read/decode failures still fail closed.

Additional guards verify safe streaming above the old ceiling and fail-closed behavior above the hard ceiling.

### Successful retry — accepted bounded relationship absence

```text
focused tests: 6 passed in 0.14s
discovery_rc: 0
source_mode: GIT_TRACKED_SAFE_JENKINS_ANSIBLE_RELATIONSHIP_TEXT_ONLY
source_status: COMPLETE
tracked_files_returned: 400
candidate_files_selected: 158
candidate_files_scanned: 158
excluded_or_unsafe_paths: 242
read_or_decode_skips: 0
oversize_skips: 0
jenkins_context_files: 11
ansible_entrypoint_signal_files: 0
explicit_relationship_signal_files: 0
relationship_source_status: NONE_OBSERVED_IN_BOUNDED_SOURCE
```

Interpretation:

```text
No explicit declared Jenkins-to-Ansible relationship was observed in the complete bounded safe Git source.
This is bounded declared-source absence only, not proof that Jenkins can never invoke Ansible elsewhere.
Previously accepted Jenkins build SUCCESS metadata cannot be promoted to Ansible execution-success evidence.
```

## Jenkins-to-Ansible evidence-path closure

Do not add more Jenkins-to-Ansible relationship probes merely to eliminate the unknown.

Within the current accepted read-only evidence boundary, no safe authoritative source was found that relates accepted Jenkins job/build metadata to Ansible execution.

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

This question may be reopened only if a materially stronger safe authoritative source becomes available.

## Trust boundary

```text
mutation_allowed: False
jenkins_api_invoked: False
jenkins_console_logs_inspected: False
jenkins_job_config_bodies_inspected: False
jenkins_build_parameters_inspected: False
ansible_cli_invoked: False
ssh_connections_performed: False
```

Only safe Git-tracked workflow/script-like text was inspected. Sensitive paths, `.env`, Ansible variable directories, Terraform state/tfvars, credentials, tokens, private keys, and Vault material were excluded.

No raw source lines, commands, arguments, credentials, host/inventory values, job names, build numbers, endpoints, console logs, config bodies, or build parameters entered evidence output.

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
5. do not continue the Jenkins-to-Ansible relationship path without new evidence;
6. return to remaining Milestone 6 gaps and choose the smallest independent read-only slice that can add authoritative evidence.

## Trust invariants

- infrastructure interaction remains read-only;
- declared state is not observed state;
- Jenkins runtime metadata is not automatically Ansible execution evidence;
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
