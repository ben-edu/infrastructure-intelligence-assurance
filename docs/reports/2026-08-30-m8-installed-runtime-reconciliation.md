# Milestone 8 — Installed Runtime Module Reconciliation

Date: 2026-08-30
Accepted: 2026-09-22
Status: ACCEPTED — LIVE RECONCILIATION PASSED
Branch: `agent/m8-installed-runtime-reconciliation`
Branch point: `9ef418b9af6fcdd42a82c2b936a40c4428394924`
Accepted live-gate commit: `f0a3b0a06bf39d96a08e737cee576550a9222026`

## Goal

Reconcile the one accepted installed-runtime mismatch, `src/infra_assurance/__init__.py`, using the smallest bounded management-host mutation with an exact backup, atomic replacement, rollback token, and post-change verification.

No systemd unit, service state, timer, permission boundary outside the target/backup files, Kubernetes RBAC, scheduler, backup platform, or infrastructure resource is changed by this slice.

## Accepted input evidence

The accepted M8 baseline at `2026-08-30T15:24:44.027806Z` established:

```text
installed Python modules: 35
matching modules: 34
mismatched modules: __init__.py
unexpected modules: 0
missing runtime entrypoint modules: 0
unreadable modules: 0
installed code owner/group: root:root
installed code writable by infra-assurance through POSIX mode: 0
service/timer fragments match repository: true
FAILED_TO_OBSERVE: 0
```

## Deployment-path classification

| Classification | Statement |
|---|---|
| `OBSERVED` | `bootstrap-observer.sh` replaces the full installed `src` tree. The later bounded `deploy-operator-attention-runtime.sh` installs an explicit module list and, before this change, omitted `__init__.py`. The live baseline observed only `__init__.py` differing while all other installed modules matched. |
| `UNKNOWN` | The historical command/execution sequence that produced the currently installed file and the exact prior installed source contents were not observed. |
| `INFERENCE` | Excluding `__init__.py` from the incremental deployment set is sufficient to preserve this exact drift pattern, but it is not promoted to confirmed historical root cause. |
| `REQUIRES_CHANGE` | Reconcile only installed `__init__.py`, and include it in future bounded operator-runtime deployment sets so the omission does not recur. |

## Bounded implementation

The repository adds:

```text
scripts/reconcile-installed-runtime-module.py
tests/test_m8_installed_runtime_reconciliation.py
```

The helper has three explicit modes:

- default plan mode: hash/metadata observation only, `mutation_allowed=false`;
- `--apply`: root-only reconciliation of exactly `/opt/infra-assurance/src/infra_assurance/__init__.py`;
- `--rollback SHA256`: root-only restoration from the exact backup token produced by apply.

Apply behavior:

1. Reject a missing, symlinked, or non-regular source/target.
2. Compare repository and installed SHA-256 values without projecting either file's contents.
3. Compile-check the repository payload before mutation.
4. Preserve the previous installed bytes in `/var/lib/infra-assurance/runtime-reconciliation/` as a root-owned mode `0600` hash-addressed backup.
5. Write a same-directory mode `0644`, root-owned temporary file; `fsync` it; atomically replace the installed target; and `fsync` the parent directory.
6. Verify exact hash, owner, group, and mode after replacement.
7. Automatically restore the previous bytes if post-install verification fails.

The helper is idempotent. If the hashes already match, `--apply` returns `ALREADY_RECONCILED` and performs no mutation.

The existing operator-runtime deployment list now includes `__init__.py` for future explicitly authorized full deployments. The dedicated reconciliation helper remains the current live path because it avoids reinstalling matching modules, reinstalling the unit, reloading systemd, or starting the service.

## Mutation boundary

Allowed by this reviewed slice after explicit authorization:

```text
create/normalize: /var/lib/infra-assurance/runtime-reconciliation (root:root 0700)
create/reuse:      hash-addressed __init__.py backup (root:root 0600)
replace if needed: /opt/infra-assurance/src/infra_assurance/__init__.py (root:root 0644)
```

Explicitly not performed:

```text
systemctl action
service start/restart
unit or timer change
permission broadening
artifact/evidence rewrite by this helper
Kubernetes or RBAC change
scheduler or platform-backup change
Terraform, Ansible, or infrastructure mutation
```

## Repository validation

Focused reconciliation and existing deployment-integration tests:

```text
15 passed in 0.09s
```

Full repository suite:

```text
471 passed in 1.42s
```

The reconciliation script also passes Python byte-compilation and `git diff --check` is clean.

Management-host validation at the accepted live-gate commit:

```text
focused suite: 15 passed in 1.58s
full repository suite: 471 passed in 4.90s
```

## Reviewed live gate

Run from the branch checkout on `mgmt-automation` after the branch/PR is current.

### 1. Focused validation

```bash
python3 -m pytest -q \
  tests/test_m8_installed_runtime_reconciliation.py \
  tests/test_operator_attention_cross_domain_runtime_integration.py \
  tests/test_operator_attention_incident_runtime_integration.py
```

### 2. Read-only plan

```bash
python3 scripts/reconcile-installed-runtime-module.py \
  | tee /tmp/m8-installed-runtime-reconciliation-plan.json

plan_rc=${PIPESTATUS[0]}
printf 'plan_rc=%s\n' "$plan_rc"
```

Expected before apply:

```text
status: CHANGE_REQUIRED
mutation_allowed: false
mutation_performed: false
module: __init__.py
source_contents_projected: false
installed_contents_projected: false
```

### 3. Authorized bounded apply

```bash
sudo /usr/bin/python3 scripts/reconcile-installed-runtime-module.py --apply \
  | tee /tmp/m8-installed-runtime-reconciliation-apply.json

apply_rc=${PIPESTATUS[0]}
printf 'apply_rc=%s\n' "$apply_rc"
```

Expected:

```text
status: RECONCILED or ALREADY_RECONCILED
mutation_allowed: true
mutation_performed: true only when the hash differed
systemd_mutation_performed: false
service_start_performed: false
infrastructure_mutation_performed: false
```

Retain the emitted `rollback_token`. Do not run rollback unless apply/post-change verification fails.

### 4. Post-change baseline

```bash
sudo /usr/bin/python3 scripts/discovery/m8_runtime_hardening_baseline_probe.py \
  --repo-root "$PWD" \
  | tee /tmp/m8-runtime-hardening-post-reconciliation.json

probe_rc=${PIPESTATUS[0]}
printf 'probe_rc=%s\n' "$probe_rc"
```

Acceptance requires:

```text
baseline_status: COMPLETE
FAILED_TO_OBSERVE: 0
INSTALLED_CODE_REPOSITORY_MATCH.installed_runtime_matches_repository: true
mismatched_modules: []
missing_entrypoint_modules: []
unexpected_modules: []
mutation_allowed: false
```

Once installed code matches, the baseline may select `PIN_EXPLICIT_SERVICE_START_TIMEOUT` as the next `REQUIRES_CHANGE`. That is expected progression, not authorization to change the unit in this slice.

### 5. Rollback only on failed verification

Use the exact token returned by apply:

```bash
sudo /usr/bin/python3 scripts/reconcile-installed-runtime-module.py \
  --rollback '<rollback_token>'
```

Then rerun the post-change baseline and record the failure. Do not delete the backup during this slice.

## Accepted live result

The reviewed gate was executed on `mgmt-automation` from commit
`f0a3b0a06bf39d96a08e737cee576550a9222026` and satisfied the acceptance
contract:

```text
focused validation: 15 passed in 1.58s
plan_rc: 0
plan status: CHANGE_REQUIRED
plan mutation_allowed: false
plan mutation_performed: false
target module: __init__.py
installed before SHA-256: cf4018a1cb490e8dc2e4ae3f74171587db5e467d20b29561a39c5219faa2e89d
repository SHA-256: 5d125e99237f4fdc5098c5897ab6c3359340e44513e38c619898dbde53b0065e
apply_rc: 0
apply status: RECONCILED
apply mutation_allowed: true
apply mutation_performed: true
installed owner/group/mode after apply: root:root 0644
probe_rc: 0
post-change baseline status: COMPLETE
FAILED_TO_OBSERVE: 0
installed modules matching repository: 35/35
full repository suite: 471 passed in 4.90s
```

The apply retained this rollback artifact without exposing file contents:

```text
rollback token: cf4018a1cb490e8dc2e4ae3f74171587db5e467d20b29561a39c5219faa2e89d
backup: /var/lib/infra-assurance/runtime-reconciliation/__init__.py.cf4018a1cb490e8dc2e4ae3f74171587db5e467d20b29561a39c5219faa2e89d.bak
```

Rollback was not required and was not performed. The backup remains retained.
The plan, apply, and post-change baseline all report no systemd, service-start,
or infrastructure mutation. All nine baseline safety flags remain false.

The post-change baseline preserves four `UNKNOWN` categories: platform
evidence/history backup status, external failure visibility, historical overlap
and missed activations, and ACL/capability/MAC writability. The next selected
`REQUIRES_CHANGE` is `PIN_EXPLICIT_SERVICE_START_TIMEOUT`, with repository
declaration `MANAGER_DEFAULT` and observed effective value `infinity`. That
control is `NOT_IMPLEMENTED` and was neither authorized nor changed in this
slice.

## Accepted result

The exact installed `__init__.py` reconciliation is accepted. Installed runtime
code now matches the repository for all 35 modules, with zero observation
failures. This acceptance does not extend authority to the timeout, systemd,
permissions, scheduling, backup, RBAC, or infrastructure. Any timeout change
requires a separate reviewed and explicitly authorized slice.
