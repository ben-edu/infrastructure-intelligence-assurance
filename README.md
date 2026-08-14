# Infrastructure Intelligence & Assurance Platform

Evidence-first infrastructure context and assurance platform.

## Current status

Milestone 0 — Evidence Contract is complete.

Milestone 1 implements a durable read-only Kubernetes inventory slice for:

- namespaces;
- nodes;
- deployments;
- statefulsets;
- daemonsets;
- services;
- ingresses;
- persistent volume claims.

The live observer runs on the management host with dedicated read-only Kubernetes credentials and a five-minute systemd timer.

## Runtime model

```text
Kubernetes API
  -> dedicated read-only observer identity
  -> complete normalized evidence
  -> freshness and trust evaluation
  -> compact operational projection
       -> context.json for AI reasoning
       -> context.md for operator review
```

Raw normalized evidence is retained separately from the compact context. Healthy resources are not repeated individually in the AI context. The projection keeps collection coverage, explicit failures, stale evidence requiring verification, observed exceptional conditions, and deterministic operational inferences such as ready replicas below desired replicas.

A workload observed with desired replicas equal to zero is retained as an observed condition and is not automatically classified as degraded.

Raw Secret values are never collected and the observer RBAC has no Secret access or mutating verbs.

## Install or refresh on the management host

```bash
sudo CLUSTER_ID=k3s-main ./scripts/bootstrap-observer.sh
```

The bootstrap verifies that the observer can read required inventory and cannot read Secrets or create Deployments.

Runtime outputs:

```text
/var/lib/infra-assurance/evidence/kubernetes.json
/var/lib/infra-assurance/evidence/context.json
/var/lib/infra-assurance/evidence/context.md
```

`kubernetes.json` is the evidence source. `context.json` and `context.md` are derived operational projections and must never be treated as a replacement for the source evidence.

## Validate locally

```bash
PYTHONPATH=src pytest
```

See `docs/milestone-1-first-slice.md` for the collector trust boundary and `docs/decisions/0002-compact-operational-context.md` for the context-compaction decision.
