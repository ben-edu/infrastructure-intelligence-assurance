# Project Continuity and Resume Protocol

This document exists to make project continuation independent of any single chat context window.

## Source precedence

When resuming work, use this order of authority:

1. Project Sources for durable goals, roadmap, architecture/trust principles, and operating model.
2. `HANDOFF.md` on `main` for the latest accepted execution checkpoint.
3. If an active project branch/PR contains a newer `HANDOFF.md`, prefer that branch version for in-flight execution state.
4. The report/ADR/milestone document referenced by the active handoff.
5. Repository implementation and tests.
6. Fresh live read-only evidence collected according to the active slice.
7. Chat reconstruction only when repository/source evidence is insufficient.

Repository and live evidence take precedence over remembered chat state.

## Mandatory checkpoint contents

Before an accepted slice is merged, `HANDOFF.md` must contain enough information for a new session to continue without prior conversation history:

```text
accepted main SHA
active branch or next branch
current milestone status
mutation boundary
management/cluster/source identifiers needed for the active slice
accepted evidence summary
failed/rejected/ambiguous evidence that must not be reused as accepted fact
preserved UNKNOWN states
trust/safety boundary
implementation and test paths
exact next step
pasteable commands when a live gate is pending
```

If a live run reveals an implementation defect or false positive, record only the corrected accepted result. The rejected result may be mentioned as implementation history, but it must not be promoted to infrastructure evidence.

## Documentation update policy

Use the smallest durable artifact that prevents ambiguity:

- `HANDOFF.md`: update at every accepted slice and whenever the exact next step changes materially.
- `docs/reports/...`: create for accepted live/discovery checkpoints that establish reusable evidence.
- ADRs: create only for durable architectural/trust decisions.
- milestone/roadmap/current-state documents: update when milestone scope/status, architecture, or durable delivery direction changes.
- `README.md`: update when the user-facing project status/runtime model becomes materially stale; do not churn it for every small discovery slice.

Avoid redundant documentation that can diverge.

## Trust semantics that survive context changes

Always preserve these distinctions:

```text
DECLARED state != OBSERVED state
NONE_OBSERVED_IN_BOUNDED_SOURCE != universal absence
FAILED_TO_OBSERVE != negative evidence
UNKNOWN != false
infrastructure recovery != application/database-consistent backup
successful task/result != restore verification
logical topology/coupling != physical failure-domain proof
configuration declaration != execution outcome
```

Never promote absence of a bounded signal into `UNPROTECTED`, drift, failure, compliance, RPO/RTO violation, or successful execution without the required authoritative evidence.

## Safety invariants

Unless explicitly authorized otherwise:

```text
mutation_allowed=false
```

Do not expose or persist:

```text
secrets, tokens, passwords
private keys
raw Kubernetes Secret values
sensitive Terraform state or real tfvars
complete sensitive connection strings
Ansible Vault contents
raw database rows/dumps/WAL contents
raw backup contents
unnecessary raw VM/storage configuration
```

Do not run restore, apply, destroy, import, state mutation, configuration changes, or other infrastructure mutation without explicit authorization and a reviewed mutation plan.

## Shell safety

Do not use interactive-shell-wide `set -e` or `set -euo pipefail` in commands given to the operator. Prefer short commands, explicit return-code checks, Python `SystemExit`, or committed scripts/tests.

Do not run an entire live gate with `sudo` when user-context behavior matters. Scope privilege narrowly.

## Merge discipline

For an accepted repository slice:

1. record the accepted report/evidence;
2. update `HANDOFF.md` with the exact next step;
3. ensure no temporary/debug/placeholder files remain;
4. inspect the PR changed-file list/diff as needed;
5. verify mergeability;
6. squash-merge when clean;
7. record the new accepted `main` SHA in the next active handoff.

## New-session bootstrap

A new session should be able to begin with:

```text
Read Project Sources.
Read docs/PROJECT_CONTINUITY.md.
Read HANDOFF.md from main.
Check for an active project PR/branch with a newer HANDOFF.md.
Continue only the Exact next step unless new evidence justifies changing it.
```

Do not repeat completed discovery merely because previous chat context is unavailable.
