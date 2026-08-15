# ADR 0008 — Build a Workload-Centric Operational Inventory as a Derived Projection

## Status

Accepted for Milestone 3 implementation.

## Context

Milestones 1 and 2 now provide current Kubernetes evidence, relationship topology, bounded history, snapshot diff, Git-declared evidence, and declared-vs-observed drift.

Operators and AI should not need to manually join all of those artifacts for routine workload questions such as:

- what is this workload and what is its current observed state?
- which Services select it?
- which Ingress routes may reach it?
- which PVCs does it reference?
- is the workload itself declared in Git and in sync?
- is a related resource currently drifted or topology-ambiguous?
- did this workload or a related resource change in the latest snapshot diff?

A traditional manually maintained CMDB would create another source of truth and would quickly diverge from the evidence systems the platform is intended to integrate.

## Decision

Add a derived workload-centric operational inventory projection.

The first entity type is:

```text
KUBERNETES_WORKLOAD
```

and includes observed:

```text
Deployment
StatefulSet
DaemonSet
```

Each entity uses the existing Kubernetes identity contract:

```text
cluster
api_group
kind
namespace
name
```

The inventory is generated after the current evidence, topology, diff, and drift artifacts are built. It does not perform new infrastructure reads.

## Entity projection

A workload entity contains:

- stable derived entity ID;
- structured Kubernetes subject identity;
- a narrow observed-state projection with evidence ID and freshness;
- Git declared coverage and direct workload comparison where available;
- Service selector-match relationships;
- composed Ingress route candidates through those Services;
- direct workload-to-PVC references;
- latest related changes;
- topology and drift attention;
- source evidence IDs.

The projection keeps only explicitly modeled non-sensitive workload attributes such as replica/scheduling counts and image references.

## Relationship semantics

Service-to-workload relationships remain:

```text
SELECTOR_MATCH_INFERENCE
```

because a Service selects Pods or EndpointSlices, not a controller directly.

Ingress route candidates are a composition of:

```text
Ingress -> Service observed reference
+
Service -> workload selector inference
```

and therefore use:

```text
COMPOSED_INFERENCE
```

They are not proof of current Pod or EndpointSlice routing.

Workload-to-PVC relationships remain direct observed references where the workload pod template explicitly references a PVC claim name.

## Related attention

Drift on a related Service, Ingress, or PVC can be surfaced on a workload entity as related attention.

This does not reclassify that drift as workload drift. The attention item retains the actual related subject and evidence IDs.

Topology ambiguity on a Service related to a workload is surfaced in the same way.

## Declared scope semantics

A live workload that has no matching record in a successfully observed configured Git scope is classified as:

```text
OUTSIDE_DECLARED_SCOPE
```

It is not automatically classified as unmanaged or drift.

If declared-source coverage is partial, a missing declaration becomes:

```text
DECLARED_COVERAGE_INCOMPLETE
```

If the declared source is unavailable or failed, it becomes:

```text
DECLARED_SOURCE_UNAVAILABLE
```

A namespace is not treated as an application or ownership boundary solely because resources share that namespace.

## Operational interface

The runtime emits:

```text
/var/lib/infra-assurance/evidence/inventory.json
/var/lib/infra-assurance/evidence/inventory.md
```

A read-only query CLI is installed as:

```text
iia-inventory
```

It supports summary, filtered list, and exact workload lookup operations.

## Security and trust consequences

- No new Kubernetes RBAC permissions are added.
- No new Git permissions are added.
- The inventory performs no infrastructure mutation.
- `mutation_allowed` is always `false`.
- Raw Secret values, environment values, ConfigMap payloads, and connection strings are not projected.
- The inventory is replaceable derived state, not authoritative evidence.
- Every relationship or attention item preserves its evidence references and inference basis.

## Deferred

This slice does not yet create:

- application or business-service entities;
- owner/team assignments;
- repository-to-application ownership inference;
- node/VM/host inventory;
- observability signal attachment;
- backup/recovery posture attachment;
- Terraform/Ansible ownership mapping;
- writable CMDB fields.

Those require additional evidence sources or explicit mapping contracts rather than guesses.
