# Milestone 8 — Runtime Hardening Baseline

Date: 2026-08-30
Status: ACCEPTED — LIVE READ-ONLY GATE PASSED
Branch: `agent/m8-runtime-hardening-baseline`
Branch point: `b63bed9704832d1e3701ea87dea50e135f2b1f64`
Accepted live-gate commit: `42c3dcfbb6f07f206073a22f086cb8df1bdd74a9`

## Goal

Establish an evidence-backed reliability and least-privilege baseline for the existing `infra-assurance` collector runtime before changing any hardening control.

This slice does not modify systemd units, permissions, scheduling, backup, Kubernetes RBAC, installed code, or infrastructure.

## Repository-declared baseline

The current accepted declarations establish:

```text
service: infra-assurance-kubernetes.service
timer: infra-assurance-kubernetes.timer
service type: oneshot
runtime identity: infra-assurance:infra-assurance
timer cadence: OnUnitActiveSec=5min
timer persistence: true
runtime module entrypoints: 12
```

Declared sandbox boundary:

```text
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadOnlyPaths=/etc/infra-assurance
ReadWritePaths=/var/lib/infra-assurance/evidence
               /var/lib/infra-assurance/history
               /var/lib/infra-assurance/git
               /var/lib/infra-assurance/declared
```

Repository source inspection also establishes:

- all 12 service entrypoints use the shared atomic-write path;
- the helper uses a same-directory temporary file, file `fsync`, atomic replace, and parent-directory `fsync`;
- the history index is atomically replaced;
- no explicit service process lock or history-writer lock is declared;
- no explicit `TimeoutStartSec`, `RuntimeMaxSec`, `Restart`, or `OnFailure` policy is declared, so effective manager defaults must be observed live rather than inferred.

## Accepted classification

| Classification | Accepted baseline statement |
|---|---|
| `DECLARED` | Identity, sandbox, writable paths, five-minute timer, oneshot boundary, sequential runtime chain, and atomic-write implementation are present in current Git. |
| `OBSERVED` | Installed service/timer fragments match the repository. Effective identity and sandbox controls match their declarations. The timer is enabled, active/waiting, persistent, and targets the oneshot service. All bounded state entries have the expected owner/group and none are world-writable. Installed code is root-owned and not POSIX-writable by the runtime identity. Of 35 installed Python modules, 34 match; only `__init__.py` differs, with no unexpected, unreadable, or missing entrypoint modules. No explicit platform-backup scheduler filename was observed in the eight bounded directories. |
| `UNKNOWN` | Platform evidence/history backup status, external failure visibility, historical overlap or missed activations, and ACL/capability/MAC effects on writability remain unknown. No bounded backup scheduler filename does not prove absence of protection. |
| `FAILED_TO_OBSERVE` | None. All required bounded observations completed. |
| `INFERENCE` | A timer targeting one oneshot unit serializes same-unit activation, but does not prove that triggers were never missed/coalesced or that an out-of-unit writer never ran. Individual atomic files do not make the whole multi-file artifact set one transaction. |
| `REQUIRES_CHANGE` | `RECONCILE_INSTALLED_RUNTIME_MODULES`: reconcile the installed `__init__.py` with the accepted repository source. This higher-priority installed-code mismatch preempts the provisional explicit-timeout candidate. Implementation status remains `NOT_IMPLEMENTED`. |

## Probe

Implementation:

```text
scripts/discovery/m8_runtime_hardening_baseline_probe.py
tests/test_m8_runtime_hardening_baseline.py
```

The probe reads only:

- allowlisted `systemctl show` properties for the exact service and timer;
- repository service/timer declarations and project Python source required for static contract checks;
- hashes of the installed systemd fragments and installed Python module set, with required service entrypoints checked explicitly;
- owner/group/mode/type metadata for bounded state and installed-code paths;
- bounded systemd/cron filenames for an explicit platform-backup signal.

The probe does not read environment-file contents, artifact contents, journal messages, raw commands, credentials, tokens, Secret values, Terraform state, backup contents, or sensitive connection strings.

It does not call any mutating systemd, permission, scheduler, backup, Kubernetes, or infrastructure command.

## Repository validation

Focused tests after the recommendation-evidence correction:

```text
11 passed in 0.09s
```

Full repository suite:

```text
463 passed in 1.04s
```

The focused tests cover classification, repeated systemd directives, manager-default preservation, installed-runtime boundary matching, metadata-only artifact inspection, filename-only backup-signal inspection, installed fragment matching, effective timer cadence, higher-priority sandbox/ownership drift, explicit UNKNOWN backup status, and command safety.

## Fresh live read-only gate

Run from the branch checkout on `mgmt-automation`:

```bash
python3 -m pytest -q tests/test_m8_runtime_hardening_baseline.py
sudo /usr/bin/python3 scripts/discovery/m8_runtime_hardening_baseline_probe.py --repo-root "$PWD" | tee /tmp/m8-runtime-hardening-baseline.json
probe_rc=${PIPESTATUS[0]}
printf 'probe_rc=%s\n' "$probe_rc"
```

Exit semantics:

```text
0 = all required bounded observations completed; UNKNOWN findings may still be valid
2 = one or more required observations FAILED_TO_OBSERVE
```

The probe is intentionally run with narrowly scoped read-only privilege because evidence/history directory metadata may not be enumerable by the interactive user. Its conclusions calculate writability for the declared `infra-assurance` identity from owner/group/mode metadata; they do not use root's effective write access as the runtime conclusion.

### First live attempt rejected for acceptance

The first management-host attempt completed at `2026-08-30T15:16:27Z` with focused tests passing, `probe_rc=0`, no `FAILED_TO_OBSERVE` findings, `mutation_allowed=false`, and every safety mutation/secret-inspection flag false.

It preliminarily observed matching installed service/timer fragments, matching identity and sandbox controls, bounded state ownership without owner/group/world-writable drift, root-owned non-runtime-writable installed code, and one installed source mismatch: `__init__.py`. It therefore selected `RECONCILE_INSTALLED_RUNTIME_MODULES` ahead of the provisional timeout candidate.

Probe version `0.1` attached timeout fields to that module-reconciliation identifier. The identifier and evidence were internally inconsistent, so the attempt is not accepted as the M8 live gate. Probe version `0.2` emits candidate-specific evidence and includes a regression test for the module-drift path. No management-host mutation occurred. The corrected accepted rerun is recorded below.

### Corrected live gate accepted

The corrected probe ran from the expected branch commit on `mgmt-automation`:

```text
commit: 42c3dcfbb6f07f206073a22f086cb8df1bdd74a9
probe version: 0.2
generated_at: 2026-08-30T15:24:44.027806Z
focused live validation: 11 passed in 0.22s
probe_rc: 0
baseline_status: COMPLETE
mutation_allowed: false
FAILED_TO_OBSERVE: 0
```

All nine safety flags are false: no systemd, permission, scheduler, backup, or infrastructure mutation occurred, and no environment-file contents, artifact contents, journal messages, or secret values were inspected.

Observed service state was a successful completed oneshot (`inactive/dead` after exit), with a last duration of `6.686` seconds, no restart, no `OnFailure` target, and effective start/runtime limits of `infinity`. The service and timer fragments match the repository, and the effective identity/sandbox match their declarations.

The bounded metadata scan completed without owner/group mismatch, world-writable state, truncation, or metadata failure. Installed code contained 69 root-owned entries and zero entries POSIX-writable by `infra-assurance`. Hash comparison found exactly one mismatch, `__init__.py`; 34 modules matched and no required entrypoint module was missing.

The timer was enabled and active/waiting, with recorded last/next trigger metadata. The repository-declared five-minute cadence is present in the hash-matching installed fragment; the live `TimersMonotonic` projection reported `OnBootUSec=1min`. Historical missed/coalesced activation behavior remains `UNKNOWN` rather than inferred from current state.

The bounded scheduler-name scan observed eight directories and no explicit infra-assurance backup name. Platform evidence/history backup status therefore remains `UNKNOWN`, not unprotected.

## Accepted result

The corrected gate satisfies the first M8 slice. Exactly one smallest justified next change is confirmed: reconcile the installed runtime `__init__.py` with the accepted repository source through a separate reviewed and explicitly authorized change.

This baseline does not implement that reconciliation, pin a timeout, or modify any unit, permission, schedule, backup, RBAC, installed code, or infrastructure.
