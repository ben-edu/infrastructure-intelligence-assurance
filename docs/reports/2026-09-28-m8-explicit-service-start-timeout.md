# Milestone 8 — Explicit Service Start Timeout

Date: 2026-09-28
Status: PREPARED — REPOSITORY VALIDATED; LIVE GATE PENDING
Branch: `agent/m8-explicit-service-start-timeout`
Branch point: `0bb944037ae6ba70c9f7077fea16031effd79af1`
Pull request: `#93`
Initial implementation commit: `5bd8f7e58765e96d3d4dd35ebd6bfa182b2958af`

## Goal

Replace the effective infinite start timeout of
`infra-assurance-kubernetes.service` with one explicit bounded value, without
starting or restarting the service and without changing its timer, sandbox,
identity, writable paths, runtime modules, Kubernetes access, backup behavior,
or infrastructure.

## Accepted input evidence

The accepted post-reconciliation M8 baseline established:

```text
service type: oneshot
timer cadence: OnUnitActiveSec=5min
last observed successful service duration: 6.629s
repository TimeoutStartSec: MANAGER_DEFAULT
effective TimeoutStartUSec: infinity
installed service/timer fragments match repository: true
installed Python modules matching repository: 35/35
FAILED_TO_OBSERVE: 0
```

The four preserved `UNKNOWN` categories remain platform evidence/history
backup status, external failure visibility, historical overlap and missed
activations, and ACL/capability/MAC writability. This slice does not promote any
of them to a stronger claim.

## Selected timeout

The repository unit declares:

```ini
TimeoutStartSec=4min
```

This value is below the five-minute timer cadence, so a hung start operation is
bounded before another full cadence interval elapses. It is approximately 36
times the last observed successful duration of 6.629 seconds, leaving material
headroom for normal variation. The value is a reliability bound, not an SLA or
a claim about worst-case source latency.

This slice does not add `RuntimeMaxSec`, `Restart`, `OnFailure`, a process lock,
or a history-writer lock. Those are not bundled into this smallest change.

## Bounded implementation

Repository changes:

```text
systemd/infra-assurance-kubernetes.service
scripts/reconcile-service-start-timeout.py
scripts/discovery/m8_runtime_hardening_baseline_probe.py
tests/test_m8_service_start_timeout.py
tests/test_m8_runtime_hardening_baseline.py
```

The reconciliation helper has three modes:

- default plan mode: read-only unit hash/metadata and allowlisted systemd
  properties, with `mutation_allowed=false`;
- `--apply`: install only the reviewed service unit and run only
  `systemctl daemon-reload`;
- `--rollback SHA256`: restore the exact root-only backup and run only
  `systemctl daemon-reload`.

Apply is fail-closed. It requires:

- the repository unit to match the reviewed SHA-256
  `a2f0c9a489d87d99c5edcf4de097ab45580a41f8877fd6a9afc53a73e64e8558`;
- the installed unit to match the accepted predecessor SHA-256
  `5bb777fdef10a3a38756924042ad9408134cbf01df034f6542ae053d55f90e0c`;
- the exact expected fragment path;
- zero drop-ins;
- effective predecessor timeout `infinity`;
- service state `inactive/dead`;
- installed owner/group/mode `root:root 0644`.

The helper validates the repository timeout contract, keeps a root-only mode
`0600` hash-addressed backup under the existing mode `0700` reconciliation
directory, uses same-directory atomic replacement with file and directory
`fsync`, reloads the systemd manager, and verifies the exact installed hash,
metadata, fragment path, drop-in count, and effective timeout. It automatically
restores the predecessor unit and reloads the manager if post-change
verification fails.

Explicitly not performed:

```text
service start/restart/stop
timer change/start/restart/stop/enable
runtime module installation
permission broadening
artifact or history rewrite by the helper
Kubernetes or RBAC change
backup or scheduler change
Terraform, Ansible, or infrastructure mutation
```

The M8 baseline probe advances to version `0.3`. It now:

- preserves `PIN_EXPLICIT_SERVICE_START_TIMEOUT` when the declaration remains
  the manager default;
- emits `ALIGN_EFFECTIVE_SERVICE_START_TIMEOUT` when the declared explicit
  timeout is not effective;
- emits no `REQUIRES_CHANGE` item when the accepted priority chain is aligned
  and the explicit timeout is effective.

An empty `REQUIRES_CHANGE` list does not erase preserved `UNKNOWN` findings.

## Repository validation

Focused M8 timeout, baseline, and prior reconciliation tests:

```text
31 passed in 0.13s
```

Additional tests not importing the unavailable local compiled `rpds`
dependency:

```text
292 passed in 1.06s
```

Both changed Python files pass byte-compilation. The complete repository suite
remains mandatory on `mgmt-automation`, whose project environment previously
ran all 471 accepted tests successfully.

Static systemd validation also passes:

```text
systemd-analyze timespan 4min: 240000000 microseconds / 4min
systemd-analyze verify service+timer: PASS
```

## Reviewed live gate

Run from the branch checkout on `mgmt-automation` after the branch and pull
request are current.

### 1. Confirm branch and run repository validation

```bash
git fetch origin
git switch agent/m8-explicit-service-start-timeout
git pull --ff-only
git rev-parse HEAD

systemd-analyze verify \
  systemd/infra-assurance-kubernetes.service \
  systemd/infra-assurance-kubernetes.timer

python3 -m pytest -q \
  tests/test_m8_service_start_timeout.py \
  tests/test_m8_runtime_hardening_baseline.py \
  tests/test_m8_installed_runtime_reconciliation.py

python3 -m pytest -q
```

### 2. Read-only plan

```bash
python3 scripts/reconcile-service-start-timeout.py \
  | tee /tmp/m8-service-start-timeout-plan.json

plan_rc=${PIPESTATUS[0]}
printf 'plan_rc=%s\n' "$plan_rc"
```

Expected before apply:

```text
status: CHANGE_REQUIRED
mutation_allowed: false
mutation_performed: false
installed_sha256: 5bb777fdef10a3a38756924042ad9408134cbf01df034f6542ae053d55f90e0c
declared_timeout_start_sec: 4min
effective_timeout_start_usec: infinity
active_state: inactive
sub_state: dead
dropin_count: 0
source_contents_projected: false
installed_contents_projected: false
```

Do not apply if the plan reports an unexpected unit hash, fragment path,
drop-in, effective timeout, metadata boundary, or active service.

### 3. Bounded apply

```bash
sudo /usr/bin/python3 scripts/reconcile-service-start-timeout.py --apply \
  | tee /tmp/m8-service-start-timeout-apply.json

apply_rc=${PIPESTATUS[0]}
printf 'apply_rc=%s\n' "$apply_rc"
```

Expected:

```text
status: RECONCILED or ALREADY_RECONCILED
mutation_allowed: true
systemd_unit_mutation_performed: true only when the predecessor was installed
daemon_reload_performed: true only when reconciliation was needed
effective_timeout_start_usec: 4min
service_start_performed: false
service_restart_performed: false
timer_mutation_performed: false
infrastructure_mutation_performed: false
```

Retain the emitted `rollback_token`. Do not run rollback unless apply or
post-change verification fails.

### 4. Post-change read-only baseline

```bash
sudo /usr/bin/python3 scripts/discovery/m8_runtime_hardening_baseline_probe.py \
  --repo-root "$PWD" \
  | tee /tmp/m8-runtime-hardening-post-timeout.json

probe_rc=${PIPESTATUS[0]}
printf 'probe_rc=%s\n' "$probe_rc"
```

Acceptance requires:

```text
baseline_version: 0.3
baseline_status: COMPLETE
FAILED_TO_OBSERVE: 0
REQUIRES_CHANGE: 0
declared timeout_start_sec: 4min
observed timeout_start_usec: 4min
service/timer fragments match repository: true
installed runtime matches repository: true
mutation_allowed: false
```

All baseline safety flags must remain false. The four accepted `UNKNOWN`
categories must remain explicit.

### 5. Rollback only on failed verification

Use only the exact token emitted by apply:

```bash
sudo /usr/bin/python3 scripts/reconcile-service-start-timeout.py \
  --rollback '<rollback_token>'
```

Then rerun the baseline and record the failure. Do not continue toward M8
closure after a failed gate.

## Acceptance pending

Do not accept or merge this slice until the focused tests, full suite, read-only
plan, bounded apply, and post-change baseline are reviewed together. If the gate
passes with zero selected `REQUIRES_CHANGE`, prepare M8 closure within the
accepted bounded scope; do not manufacture additional hardening work merely to
eliminate preserved `UNKNOWN` states.
