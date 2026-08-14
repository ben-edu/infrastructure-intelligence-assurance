# ADR 0002 — Keep Full Evidence and Compact the Operational Context

## Status

Accepted for Milestone 1 implementation.

## Context

The first live Kubernetes observer produced hundreds of valid evidence records in a single cluster snapshot. Feeding every healthy resource record directly into AI context would preserve detail but would also recreate the operator cognitive-load problem inside the reasoning layer.

The evidence contract already separates evidence from task-oriented AI context, so the platform does not need to choose between full fidelity and concise reasoning input.

## Decision

Keep the complete normalized Kubernetes snapshot as source evidence in `kubernetes.json`.

Generate a separate compact `context.json` that contains only:

- successful collection coverage and resource counts;
- explicit collection failures and unknown state;
- stale collection evidence that requires live verification;
- observed exceptional conditions such as a workload scaled to zero;
- deterministic operational inferences such as a Node not Ready, ready replicas below desired replicas, or a PVC not Bound.

Generate `context.md` from the same compact projection for operator review.

Healthy individual resources are omitted from the compact context but remain available in the raw evidence snapshot.

A workload with desired replicas equal to zero is not classified as degraded solely because it has zero ready replicas. The zero desired state is retained as an observed condition.

## Consequences

- AI context becomes substantially smaller without deleting evidence.
- Evidence lineage remains available through `evidence_ids`.
- Operational summaries can evolve without changing the collector or losing source data.
- Context is explicitly a derived projection and must not be treated as authoritative source evidence.
- Additional health semantics may be added only when their required evidence is actually collected.

## Deferred

This decision does not add Prometheus metrics, logs, events, EndpointSlice health, backup state, declared Git state, drift classification, or mutating automation.
