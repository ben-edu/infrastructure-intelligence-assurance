# Milestone 8 — Runtime Hardening Baseline

Date: 2026-08-30
Status: PREPARED — FRESH LIVE READ-ONLY GATE PENDING
Branch: `agent/m8-runtime-hardening-baseline`
Branch point: `b63bed9704832d1e3701ea87dea50e135f2b1f64`

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

## Classification before the live gate

| Classification | Current baseline statement |
|---|---|
| `DECLARED` | Identity, sandbox, writable paths, five-minute timer, oneshot boundary, sequential runtime chain, and atomic-write implementation are present in current Git. |
| `OBSERVED` | Repository base and deterministic probe behavior are validated; installed-host state has not yet been freshly observed in this slice. |
| `UNKNOWN` | Effective installed unit/timer state, current ownership/modes, historical overlap or missed activations, external failure visibility, ACL/capability effects, and platform evidence/history backup status remain unknown pending the live probe. |
| `FAILED_TO_OBSERVE` | None recorded yet; the fresh management-host observation has not been attempted. |
| `INFERENCE` | A timer targeting one oneshot unit serializes same-unit activation, but does not prove that triggers were never missed/coalesced or that an out-of-unit writer never ran. Individual atomic files do not make the whole multi-file artifact set one transaction. |
| `REQUIRES_CHANGE` | Provisional smallest candidate: after observing the effective service start timeout, pin it in the repository unit, but only if live evidence shows no higher-priority identity, sandbox, unit-fragment, installed-code, or permission drift. Nothing is implemented in this baseline. |

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

Focused tests:

```text
10 passed in 0.12s
```

Full repository suite:

```text
462 passed in 1.61s
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

## Acceptance pending

Do not mark this report accepted and do not implement the proposed timeout or any other control until the fresh probe output is reviewed and the single smallest justified next change is confirmed from observed state.
