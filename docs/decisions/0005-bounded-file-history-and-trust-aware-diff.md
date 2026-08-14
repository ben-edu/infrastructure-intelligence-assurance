# ADR 0005 — Start Milestone 2 With Bounded File History and Trust-Aware Diff

## Status

Accepted for Milestone 2 implementation.

## Context

Milestone 1 established a reliable current-state evidence loop. Milestone 2 must answer a different operational question: what changed between trustworthy observations?

A database, event bus, or time-series platform is not yet justified by an observed requirement. The project contract explicitly favors simple replaceable storage until scale or query needs demonstrate otherwise.

History must also preserve the Milestone 0 failure semantics. A failed or stale current collection must never turn a previously observed resource into a false `REMOVED` event.

## Decision

Persist normalized Kubernetes snapshots as immutable JSON files under a bounded local history store.

The default retention is 288 snapshots. With the current five-minute collector cadence this is approximately 24 hours of history. Retention is configurable.

The history store maintains a small atomic index containing:

- snapshot ID;
- generation timestamp;
- relative snapshot file;
- evidence record count;
- failed collection count.

Snapshot files and live projection artifacts use atomic replace semantics so readers do not observe partially written JSON or Markdown.

The first diff classifications are:

- `ADDED` — current resource exists and the previous collection completed, proving it was not observed previously;
- `REMOVED` — previous resource existed and the current collection is complete and fresh, proving it is not present now;
- `MODIFIED` — the same evidence identity exists in both snapshots and normalized data changed;
- `NEWLY_OBSERVED` — current resource exists but previous collection completeness is insufficient to claim it was newly added.

Kubernetes identity continues to include:

```text
system, cluster, api_group, kind, namespace, name
```

If the current collection is failed, partial, stale, missing, or lacks a valid expiry, membership comparison for that resource kind becomes unknown and requires live verification.

## Migration

When Milestone 2 is first installed on a host that already has the Milestone 1 `kubernetes.json` artifact but no history index, the existing latest evidence is imported as the first immutable baseline before collecting the next snapshot.

This preserves continuity without inventing historical state that was never recorded.

## Security

History stores only the normalized evidence already permitted by the collector contract. It does not retain raw Kubernetes API payloads, Secret values, credential material, or secret-bearing environment values.

## Consequences

- The operator can see actual changes instead of comparing current dumps manually.
- Collection failure is itself visible historical evidence.
- The storage implementation remains replaceable by PostgreSQL or another backend later.
- File history is intentionally bounded and is not a long-term audit archive.

## Deferred

- long-term historical storage;
- distributed locking;
- multi-host writer coordination;
- query indexes beyond the small metadata index;
- event streaming;
- database-backed retention policies.
