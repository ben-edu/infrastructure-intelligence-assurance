# Milestone 3 — Workload Operational Inventory

## Goal

Reduce operator and AI join work by presenting a traceable workload-centric operational view over evidence already collected by the platform.

This is the first Dynamic Operational Inventory / CMDB slice. It is intentionally derived and read-only.

## Inputs

```text
Kubernetes observed evidence
Kubernetes topology
previous/current snapshot diff
Git declared evidence
Git-vs-live drift
```

No additional live query is performed by the inventory builder.

## Output

```text
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/inventory.md
```

The JSON artifact contains one entity for each currently observed Deployment, StatefulSet, and DaemonSet.

The Markdown artifact is compact and attention-oriented rather than a full duplicate of the JSON catalog.

## Workload view

For each workload the inventory projects:

- current observed state and freshness;
- safe replica/scheduling fields and image references;
- direct Git declared coverage for the workload;
- workload-level declared-vs-observed comparison where available;
- Services whose selectors match the workload pod-template labels;
- Ingress route candidates composed through those Services;
- directly referenced PVCs;
- latest related snapshot changes;
- related topology ambiguity and drift attention;
- evidence IDs for traceability.

## Query CLI

```bash
iia-inventory summary
iia-inventory list
iia-inventory list --namespace validation
iia-inventory list --attention-only
iia-inventory show --namespace validation --kind Deployment --name nginx-validation
```

The CLI reads the generated artifact only. It does not query Kubernetes or Git.

## Trust behavior

A Service selector match is an inference about controller candidacy, not proof of live routing.

An Ingress route candidate composes an observed Ingress-to-Service reference with that selector inference. It therefore remains inferred.

Related drift remains attributed to the actual drifted resource. Surfacing Ingress drift on a workload entity does not mean the workload itself is drifted.

A live workload outside the configured Git declared scope is not automatically considered unmanaged or drifted.

A namespace is not automatically interpreted as an application or ownership boundary.

## Expected first live value

The current cluster already contains two useful acceptance cases:

1. `validation/nginx-validation` has a related Ingress whose Git-declared host differs from the observed host. The workload inventory should surface that related drift without changing the workload's own direct comparison.
2. `monitoring/loki-headless` currently has a selector matching two workload controllers. Workloads related to that Service should preserve topology ambiguity rather than choosing one owner.

## Deferred

Later Milestone 3 slices can add additional entity types and evidence attachments, including infrastructure hosts/VMs, observability signals, backup/recovery assurance, IaC ownership, and explicit application/service ownership mappings.
