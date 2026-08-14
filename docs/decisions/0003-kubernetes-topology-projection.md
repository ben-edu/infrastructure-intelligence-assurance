# ADR 0003 — Derive Kubernetes Topology Without Creating a New Source of Truth

## Status

Accepted for Milestone 1 implementation.

## Context

The live Kubernetes inventory and compact operational context established reliable resource evidence, but a flat resource list is insufficient for many planning and troubleshooting tasks.

The platform needs to understand useful relationships without inventing a full CMDB or treating derived relationships as authoritative source data.

## Decision

Add a derived Kubernetes topology projection alongside the raw evidence and compact operational context.

The first relationship set is intentionally narrow:

- Ingress -> Service from observed Ingress backend references;
- Service -> workload-controller candidate from Service selector matching against observed workload pod-template labels;
- workload -> PVC from observed persistentVolumeClaim references in workload pod templates.

Relationship confidence is explicit:

- `OBSERVED_REFERENCE` for direct object references found in Kubernetes resource specs;
- `SELECTOR_MATCH_INFERENCE` for Service-to-controller relationships because Services select Pods/Endpoints rather than controllers directly.

Every relationship and topology issue retains evidence IDs.

A missing Ingress Service or directly referenced PVC is reported as requiring verification when the corresponding resource collection completed successfully.

A Service selector with no Deployment, StatefulSet, or DaemonSet match is not classified as broken. The selected Pods may be standalone, Job-managed, or outside the current controller scope. This remains unknown until EndpointSlice or Pod evidence is available.

The topology projection is written separately from raw evidence:

```text
kubernetes.json  -> complete normalized evidence
context.json     -> compact AI operational context
context.md       -> operator operational summary
topology.json    -> structured derived relationships
topology.md      -> operator relationship summary
```

## Security boundary

No additional Kubernetes RBAC permissions are introduced.

The collector adds only workload labels/selectors and PVC claim names required for relationship derivation. It does not collect Secret payloads, environment-variable values, ConfigMap values, credentials, or complete sensitive connection strings.

## Consequences

- AI and operators can reason about application paths without reading hundreds of raw resource records.
- Direct references and inferred selector matches remain distinguishable.
- Relationship gaps become explicit verification questions rather than unsupported conclusions.
- The topology can later be refined with EndpointSlice, Pod, Git, observability, or CMDB evidence without changing the raw evidence contract.

## Deferred

- EndpointSlice and Pod-level traffic confirmation;
- network policy relationships;
- ConfigMap and Secret dependency graphs;
- StatefulSet volume-claim-template to generated PVC mapping;
- repository-to-workload ownership;
- persistence/history and topology diffs;
- mutating automation.
