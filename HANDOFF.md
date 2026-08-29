# Project Handoff

Project Sources remain authoritative for durable goals, roadmap, architecture/trust principles, and operating rules.

For context-window-independent continuation, read `docs/PROJECT_CONTINUITY.md`, then this file, then only the report/ADR for the active slice.

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

Preserve Terraform state-backed coverage, live resource coverage, execution outcome, plan/apply result, drift, and destructive-change status as `UNKNOWN` unless stronger authoritative evidence is added.

Do not reuse the rejected first Terraform execution scan that contained a gate-only false positive.

## Accepted Milestone 6 — Ansible declared structure

Reports:

```text
docs/reports/2026-08-29-m6-ansible-declared-state-inventory.md
docs/reports/2026-08-29-m6-ansible-playbook-role-declared-coverage.md
docs/reports/2026-08-29-m6-ansible-execution-declaration-discovery.md
```

Accepted bounded state:

```text
inventory files: 5
playbooks: 10
role directories: 7
inventory group declarations: 6
inventory host declarations: 8
referenced local role directories: 7/7
playbooks with resolved local role: 8
playbooks with no direct role reference: 2
bounded safe workflow/script files scanned for Ansible execution declarations: 156
accepted Ansible execution declaration files: 0
managed host coverage: DECLARED_CONFIGURATION_ONLY
live managed host coverage: UNKNOWN
execution outcome/success/idempotence/drift: UNKNOWN
```

Bounded declaration absence does not prove Ansible is never executed elsewhere.

## Accepted Milestone 6 — Ansible execution outcome source path

Reports:

```text
docs/reports/2026-08-29-m6-ansible-execution-outcome-source-discovery.md
docs/reports/2026-08-29-m6-jenkins-ansible-outcome-capability.md
```

Accepted source selection and capability:

```text
preferred source candidate: JENKINS_READ_ONLY_SOURCE_CANDIDATE
management-host Ansible-named unit/timer/cron signals: NONE_OBSERVED
Jenkins integration source capability: JOB_AND_BUILD_METADATA_CAPABILITY_SIGNAL_OBSERVED
console capability signal files: 1 — explicitly outside permitted evidence path
config-body capability signal files: 0
latest focused tests: 4 passed in 0.05s
latest full suite before PR #71: 376 passed in 1.63s
```

Interpretation boundary:

```text
Jenkins source-code capability is not Jenkins runtime evidence.
Jenkins runtime metadata is not automatically Ansible execution evidence.
Console logs and job config bodies remain outside the permitted evidence path.
```

Preserve:

```text
execution_outcome_status: UNKNOWN
execution_success_status: UNKNOWN
idempotence_status: UNKNOWN
configuration_drift_status: UNKNOWN
successful_execution_claims: 0
idempotence_claims: 0
drift_claims: 0
```

## Active Milestone 6 — Jenkins API metadata-only probe

Implementation prepared on this branch:

```text
scripts/discovery/m6_jenkins_api_metadata_probe.py
tests/test_jenkins_api_metadata_probe.py
```

Goal:

```text
Establish whether the accepted read-only Jenkins integration can safely enumerate runtime job/build metadata through a GET-only Jenkins JSON API request.
```

Local authentication boundary:

```text
Only approved Jenkins URL/user/token/password keys may be loaded locally from process environment or the bounded Jenkins integration .env file.
Credential and endpoint values must never be printed or persisted.
```

Permitted Jenkins API surface:

```text
GET root /api/json with restricted tree:
jobs[name,color,lastBuild[number,result,timestamp,building]]
```

Names and build numbers may be used only in memory. They must not be projected. Job names are inspected only for a weak `ansible` token count.

Permitted projection:

```text
connection config status
API observation status
aggregate job count
aggregate jobs with last-build metadata
aggregate weak ansible-name-signal job count
aggregate safe last-build result categories/counts
```

Explicitly prohibited:

```text
consoleText / console logs
config.xml / job configuration bodies
build parameters
environment values
credential/token values
raw commands or arguments
inventory arguments
host targets
Vault material
job names
build numbers
endpoint URL value
```

Even if Jenkins build result metadata is observed, preserve Ansible outcome/success/idempotence/drift as `UNKNOWN` until stronger safe relationship evidence exists.

## Exact next step

On `mgmt-automation`:

```bash
cd ~/projects/infrastructure-intelligence-assurance

git fetch origin

git switch --track origin/agent/m6-jenkins-api-metadata-probe

python3 -m pytest -q \
  tests/test_jenkins_api_metadata_probe.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_jenkins_api_metadata_probe.py

echo "discovery_rc=$?"
```

Acceptance rules:

- focused tests must pass;
- only GET metadata endpoint may be invoked;
- authentication values may be loaded locally but must never be projected;
- endpoint URL value must not be projected;
- no console/config/parameters/environment/command/host-target surfaces may be requested;
- job names/build numbers must not be printed or persisted;
- API observation failure is `FAILED_TO_OBSERVE`, not negative evidence;
- Jenkins build outcome metadata must not be promoted to Ansible execution success/idempotence/drift claims.

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
