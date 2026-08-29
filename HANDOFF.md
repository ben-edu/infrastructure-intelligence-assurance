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

## Accepted Milestone 6 — prior evidence

Accepted reports:

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

Accepted bounded state:

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

Relationship rule:

```text
A positive signal requires explicit Jenkins context
AND one accepted Ansible execution entry point in the same safe tracked text file:
  ansible-playbook
  ansible-runner run
  ansible-navigator run
```

Generic words such as `ansible` or `jenkins` alone do not count.

### First live attempt — INCOMPLETE, not bounded absence

Focused tests:

```text
4 passed in 0.06s
```

Observed discovery:

```text
source_status: INCOMPLETE
tracked_files_returned: 400
candidate_files_selected: 158
candidate_files_scanned: 157
excluded_or_unsafe_paths: 242
read_or_decode_skips: 0
oversize_skips: 1
jenkins_context_files: 11
ansible_entrypoint_signal_files: 0
explicit_relationship_signal_files: 0
relationship_source_status: SOURCE_INCOMPLETE
discovery_rc: 2
```

Interpretation:

```text
This result is FAILED_TO_OBSERVE / INCOMPLETE for bounded absence.
The zero relationship signals MUST NOT yet be accepted as NONE_OBSERVED_IN_BOUNDED_SOURCE because one selected safe candidate was skipped by the old size ceiling.
Ansible execution outcome/success/idempotence/drift remain UNKNOWN.
```

### Retry fix prepared on active branch

The old fixed `512 KiB` candidate read ceiling was too restrictive for token-level relationship scanning.

The scanner now:

```text
streams safe candidate text instead of loading the whole file
uses an 8 MiB hard ceiling
keeps a bounded carry window so tokens split across read chunks are still detectable
never prints or persists raw source content
retains fail-closed SOURCE_INCOMPLETE behavior for files above the hard ceiling or read/decode failures
```

Two additional guards verify:

```text
a safe candidate larger than the old 512 KiB ceiling is streamed successfully
a candidate above the hard ceiling still fails closed as OVERSIZE
```

Safe source scope remains unchanged: sensitive paths, `.env`, Ansible variable directories, Terraform state/tfvars, credential/token/private-key-like paths are excluded before reads.

No Jenkins API, Ansible CLI, SSH, console/config/parameter access, or infrastructure mutation is performed by this discovery.

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git pull --ff-only origin agent/m6-ansible-jenkins-relationship-source

python3 -m pytest -q \
  tests/test_ansible_jenkins_relationship_source_discovery.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_ansible_jenkins_relationship_source_discovery.py

echo "discovery_rc=$?"
```

Acceptance rules:

- focused tests must pass;
- source must be `COMPLETE` for bounded absence to be accepted;
- generic token co-occurrence is not relationship evidence;
- raw source content, commands, arguments, credentials, host/inventory values, job names, and build identifiers must not be projected;
- relationship discovery must keep Ansible outcome/success/idempotence/drift `UNKNOWN`;
- if retry returns `COMPLETE` plus `NONE_OBSERVED_IN_BOUNDED_SOURCE`, record bounded absence and stop widening the Jenkins→Ansible outcome path merely to eliminate the unknown;
- if source remains incomplete, preserve `FAILED_TO_OBSERVE` and stop rather than weaken the trust boundary.

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
