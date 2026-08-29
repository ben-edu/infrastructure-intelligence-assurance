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

Preserve Terraform state-backed coverage, live resource coverage, execution outcome, plan/apply result, drift, and destructive-change status as `UNKNOWN`. Do not reuse the rejected first Terraform gate-only false positive.

## Accepted Milestone 6 — Ansible and Jenkins evidence path

Accepted reports:

```text
docs/reports/2026-08-29-m6-ansible-declared-state-inventory.md
docs/reports/2026-08-29-m6-ansible-playbook-role-declared-coverage.md
docs/reports/2026-08-29-m6-ansible-execution-declaration-discovery.md
docs/reports/2026-08-29-m6-ansible-execution-outcome-source-discovery.md
docs/reports/2026-08-29-m6-jenkins-ansible-outcome-capability.md
docs/reports/2026-08-29-m6-jenkins-api-metadata-probe.md
```

Accepted bounded state:

```text
inventory files: 5
playbooks: 10
role directories: 7
referenced local role directories: 7/7
accepted Ansible execution declaration files in bounded safe Git source: 0
preferred runtime outcome source candidate: JENKINS_READ_ONLY_SOURCE_CANDIDATE
Jenkins integration source capability: JOB_AND_BUILD_METADATA_CAPABILITY_SIGNAL_OBSERVED
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
live managed host coverage: UNKNOWN
Ansible execution outcome: UNKNOWN
Ansible execution success: UNKNOWN
idempotence: UNKNOWN
configuration drift: UNKNOWN
```

The eleven Jenkins `SUCCESS` values are Jenkins last-build metadata only and are not Ansible success evidence.

## Active Milestone 6 — Ansible-to-Jenkins relationship source discovery

Implementation prepared on this branch:

```text
scripts/discovery/m6_ansible_jenkins_relationship_source_discovery.py
tests/test_ansible_jenkins_relationship_source_discovery.py
```

Goal:

```text
Determine whether a bounded safe Git-tracked source contains an explicit declared relationship between Jenkins context and an accepted Ansible execution entry point.
```

A positive relationship signal requires both in the same safe tracked text file:

```text
explicit Jenkins context
AND
one accepted Ansible execution entry point:
  ansible-playbook
  ansible-runner run
  ansible-navigator run
```

Generic words such as `ansible` or `jenkins` alone do not count.

Safe source scope:

```text
Git-tracked Jenkins/workflow/script-like text only
sensitive path classes excluded
Ansible group_vars/host_vars/vars excluded
Terraform state/tfvars excluded
.env excluded
credential/token/private-key-like paths excluded
```

Permitted projection:

```text
source completeness
tracked/candidate/scanned counts
Jenkins-context file count
Ansible-entrypoint signal file count
explicit relationship signal file count
relationship source status
```

Raw source lines, commands, arguments, job names, build numbers, inventory values, host targets, credentials, endpoints, console logs, job configuration bodies, build parameters, and Vault material must not be projected.

Even a positive declared relationship signal would not prove a particular Jenkins build executed Ansible or succeeded.

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m6-ansible-jenkins-relationship-source

python3 -m pytest -q \
  tests/test_ansible_jenkins_relationship_source_discovery.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_ansible_jenkins_relationship_source_discovery.py

echo "discovery_rc=$?"
```

Acceptance rules:

- focused tests must pass;
- source must be complete for bounded absence to be accepted;
- generic token co-occurrence is not relationship evidence;
- no Jenkins API, Ansible CLI, SSH, console/config/parameter access, or infrastructure mutation is allowed;
- no raw commands/arguments, credentials, host/inventory values, job names, or build identifiers may be projected;
- relationship discovery must keep Ansible execution outcome/success/idempotence/drift `UNKNOWN`;
- if no safe explicit relationship source is observed, record bounded absence and stop widening the Jenkins→Ansible outcome path merely to eliminate the unknown.

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
