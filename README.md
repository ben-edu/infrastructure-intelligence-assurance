# Infrastructure Intelligence & Assurance Platform

Evidence-first infrastructure context and assurance platform.

## Current status

Milestone 0 — Evidence Contract is complete.

Milestone 1 implements a durable read-only Kubernetes evidence loop for:

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
  -> compact operational context
  -> derived topology relationships
```

Runtime artifacts are deliberately separated by trust role:

```text
kubernetes.json  complete normalized evidence
context.json     compact AI operational context
context.md       operator operational summary
topology.json    structured derived relationships
topology.md      operator relationship summary
```

`kubernetes.json` remains the evidence source. The context and topology files are derived projections and must never replace source evidence.

The topology slice derives only relationships currently supported by observed evidence:

- Ingress -> Service from backend references;
- Service -> workload-controller candidates from selector matching;
- workload -> PVC from explicit PVC references in pod templates.

Service-to-controller relationships are explicitly marked as inference because Kubernetes Services select Pods/Endpoints rather than Deployment, StatefulSet, or DaemonSet objects directly.

A Service selector with no observed controller match remains unknown with the current scope; it is not automatically classified as broken.

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
/var/lib/infra-assurance/evidence/topology.json
/var/lib/infra-assurance/evidence/topology.md
```

## Validate locally

```bash
PYTHONPATH=src pytest
```

See:

- `docs/milestone-1-first-slice.md` for the collector trust boundary;
- `docs/decisions/0002-compact-operational-context.md` for context compaction;
- `docs/decisions/0003-kubernetes-topology-projection.md` for relationship trust semantics.
