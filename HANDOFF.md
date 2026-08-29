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

Preserve Terraform state-backed coverage, live resource coverage, execution outcome, plan/apply result, drift, and destructive-change status as `UNKNOWN` unless stronger authoritative evidence is added.

Do not reuse the rejected first Terraform execution scan that contained a gate-only false positive.

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

Jenkins integration capability is not Jenkins runtime evidence. Jenkins runtime metadata is not automatically Ansible execution evidence.

## Active Milestone 6 — Jenkins API metadata-only probe

Implementation:

```text
scripts/discovery/m6_jenkins_api_metadata_probe.py
tests/test_jenkins_api_metadata_probe.py
```

### First live attempt — NOT ACCEPTED AS OUTCOME EVIDENCE

Validation before attempt:

```text
focused tests: 4 passed in 0.08s
```

Observed attempt:

```text
connection_config_status: CONNECTION_CONFIG_UNAVAILABLE
env_files_observed: 1
env_files_read_for_approved_keys: 0
credential_material_loaded_locally: False
jenkins_api_invoked: False
api_observation_status: NOT_ATTEMPTED
jobs_total: 0
jobs_with_last_build_metadata: 0
discovery_rc: 2
```

Interpretation:

```text
This is FAILED_TO_OBSERVE / NOT_ATTEMPTED, not negative Jenkins evidence.
`jobs_total: 0` from this attempt MUST NOT be interpreted as Jenkins having zero jobs.
No Jenkins API call occurred.
No credential value or endpoint value was projected.
```

Likely issue: the first parser accepted only a short fixed list of Jenkins connection-key aliases while the bounded integration `.env` uses another Jenkins-scoped naming/format convention.

### Retry fix prepared on active branch

The connection parser now:

```text
accepts only keys with explicit JENKINS_ scope
classifies URL/ENDPOINT, USER/USERNAME, TOKEN/PASSWORD/API_KEY roles
supports `export KEY=value`
rejects generic URL/TOKEN/PASSWORD variables
fails closed if multiple distinct values map to the same connection role
never projects key names or values
```

The permitted Jenkins runtime surface remains unchanged:

```text
HTTP method: GET only
endpoint class: root /api/json only
restricted tree: jobs[name,color,lastBuild[number,result,timestamp,building]]
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

git pull --ff-only origin agent/m6-jenkins-api-metadata-probe

python3 -m pytest -q \
  tests/test_jenkins_api_metadata_probe.py

PYTHONPATH=src python3 \
  scripts/discovery/m6_jenkins_api_metadata_probe.py

echo "discovery_rc=$?"
```

Acceptance rules:

- focused tests must pass;
- connection material must resolve without projecting key names or values;
- only a GET metadata endpoint may be invoked;
- no console/config/parameters/environment/command/host-target surfaces may be requested;
- job names/build numbers must not be printed or persisted;
- connection/API observation failure remains `FAILED_TO_OBSERVE`, never negative evidence;
- Jenkins build metadata must not be promoted to Ansible execution success/idempotence/drift claims;
- if retry succeeds, run the full repository suite before PR/merge.

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
