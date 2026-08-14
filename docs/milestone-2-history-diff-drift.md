# Milestone 2 — History, Diff, Drift, and Change Context

## Goal

Extend the proven Kubernetes evidence loop from "what is true now?" to:

- what changed since the previous trustworthy observation;
- which current comparison is unsafe because evidence failed or expired;
- where configured Git-declared state differs from live observed state;
- what compact change context should be presented to an operator or AI.

Milestone 2 remains read-only against infrastructure.

## Runtime flow

```text
Kubernetes API
  -> normalized current evidence
  -> immutable bounded snapshot history
  -> trust-aware previous/current diff
  -> declared-vs-observed drift evaluation
  -> compact change-context.json / change-context.md
```

Milestone 1 context, topology, and planning artifacts remain available and are not replaced.

## Runtime artifacts

Current evidence and projections:

```text
/var/lib/infra-assurance/evidence/kubernetes.json
/var/lib/infra-assurance/evidence/context.json
/var/lib/infra-assurance/evidence/context.md
/var/lib/infra-assurance/evidence/topology.json
/var/lib/infra-assurance/evidence/topology.md
```

Milestone 2 artifacts:

```text
/var/lib/infra-assurance/history/kubernetes/index.json
/var/lib/infra-assurance/history/kubernetes/snapshots/*.json
/var/lib/infra-assurance/evidence/diff.json
/var/lib/infra-assurance/evidence/diff.md
/var/lib/infra-assurance/evidence/drift.json
/var/lib/infra-assurance/evidence/drift.md
/var/lib/infra-assurance/evidence/change-context.json
/var/lib/infra-assurance/evidence/change-context.md
```

## History policy

Default retention:

```text
288 snapshots
```

At the current five-minute cadence this is approximately 24 hours.

The policy is intentionally bounded and configurable. It is sufficient to validate operational usefulness before choosing a long-term data store.

Each snapshot is immutable after creation. The history index is atomically replaced.

## Diff trust rules

The diff engine never treats collector failure as resource removal.

For example:

```text
previous: Service/api observed
current:  Service collection FAILED_TO_OBSERVE
```

Result:

```text
UNKNOWN current Service membership
```

not:

```text
REMOVED Service/api
```

Likewise, a stale current collection blocks current membership claims until refreshed.

## Drift trust rules

Drift is evaluated only for configured normalized Git-declared evidence.

No configured declared evidence produces:

```text
DECLARED_STATE_UNAVAILABLE
```

not "zero drift".

A configured declared record and matching current observation remain two separate evidence records. The drift report references both through evidence IDs and Git revision metadata.

## Compact change context

`change-context.json` is a bounded projection. It contains:

- current/previous snapshot identity;
- change counts;
- recent changed subjects only;
- drift attention only;
- unknown/failed evidence;
- required live verification;
- truncation metadata;
- `mutation_allowed=false`.

Unchanged resources are summarized by count rather than repeated individually.

## Operator commands

History status:

```bash
iia-k8s-history status
```

Recent snapshot metadata:

```bash
iia-k8s-history list --limit 10
```

## First live acceptance

The first live acceptance should verify in one run that:

1. the previous Milestone 1 `kubernetes.json` is migrated into history when history is initially empty;
2. the next live collection creates a second immutable snapshot;
3. the diff compares those snapshots without false removals;
4. failed collection count remains visible in history metadata;
5. declared drift reports `DECLARED_STATE_UNAVAILABLE` until a real normalized Git source is connected;
6. the compact change context remains read-only and materially smaller than the raw snapshots;
7. all existing Milestone 0/1 tests continue to pass.

The subsequent Milestone 2 slice can connect the identified `ben-edu/api-cluster-infra` repository through a dedicated safe Git observer boundary.
