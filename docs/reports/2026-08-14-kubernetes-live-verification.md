# Kubernetes Live Verification — 2026-08-14

## Scope

First live acceptance run of the Milestone 1 read-only Kubernetes inventory observer on the management host.

## Observed runtime state

- Management host: `mgmt-automation`
- Evidence cluster identity: `k3s-main`
- Collector service type: systemd oneshot
- Last collector execution: successful (`status=0/SUCCESS`)
- Collection timer: enabled and active
- Timer cadence: five minutes

The collector service being inactive after completion is expected for a successful oneshot service. The active timer schedules subsequent executions.

## Snapshot result

The accepted live snapshot reported:

- normalized evidence records: 240
- AI-context facts before compaction: 240
- unknowns: 0
- observation failures: 0
- required live verification items: 0

This establishes that the initial inventory scope was observable with the dedicated read-only identity at the time of verification.

## Trust statement

This report records the observed acceptance result only. It does not contain the observer token, kubeconfig content, Kubernetes Secret values, or other credentials.

The live result motivated ADR 0002: retain the complete 240-record evidence snapshot while producing a smaller task-oriented operational projection for AI and operator consumption.
