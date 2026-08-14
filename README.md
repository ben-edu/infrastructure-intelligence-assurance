# Infrastructure Intelligence & Assurance Platform

Evidence-first infrastructure context and assurance platform.

## Current status

Milestone 0 — Evidence Contract is complete.

Milestone 1 implements a durable read-only Kubernetes evidence and planning loop for:

- namespaces;
- nodes;
- deployments;
- statefulsets;
- daemonsets;
- services;
- ingresses;
- persistent volume claims;
- compact operational context;
- evidence-linked topology;
- task-scoped deployment planning preflight.

The live observer runs on the management host with dedicated read-only Kubernetes credentials and a five-minute systemd timer.

## Runtime model

```text
Kubernetes API
  -> dedicated read-only observer identity
  -> complete normalized evidence
  -> freshness and trust evaluation
  -> compact operational context
  -> derived topology relationships
  -> task-scoped planning preflight
  -> AI consumption
```

Runtime artifacts are deliberately separated by trust role:

```text
kubernetes.json  complete normalized evidence
context.json     compact AI operational context
context.md       operator operational summary
topology.json    structured derived relationships
topology.md      operator relationship summary
preflight.json   task-scoped machine-readable planning input
preflight.md     task-scoped operator/AI planning summary
```

`kubernetes.json` remains the evidence source. Context, topology, and preflight files are derived projections and must never replace source evidence.

The topology slice derives only relationships currently supported by observed evidence:

- Ingress -> Service from backend references;
- Service -> workload-controller candidates from selector matching;
- workload -> PVC from explicit PVC references in pod templates.

Service-to-controller relationships are explicitly marked as inference because Kubernetes Services select Pods/Endpoints rather than Deployment, StatefulSet, or DaemonSet objects directly.

The deployment preflight consumes current evidence and a strict hypothetical deployment request. It separates evidence-backed facts, observed conflicts, inferences, unknowns, and selective live verification requirements before producing a non-executable candidate plan. `mutation_allowed` remains `false` throughout Milestone 1.

A failed or stale collection is never used to claim that a requested resource name is available.

A workload observed with desired replicas equal to zero is retained as an observed condition and is not automatically classified as degraded.

Raw Secret values are never collected and the observer RBAC has no Secret access or mutating verbs.

## Install or refresh on the management host

```bash
sudo CLUSTER_ID=k3s-main ./scripts/bootstrap-observer.sh
```

The bootstrap verifies that the observer can read required inventory and cannot read Secrets or create Deployments. It also installs the read-only planning CLI and an example hypothetical deployment request.

## Run the Milestone 1 planning preflight

```bash
sudo -u infra-assurance iia-k8s-preflight \
  --request /etc/infra-assurance/examples/hypothetical-app-deployment.json
```

Default preflight outputs:

```text
/var/lib/infra-assurance/evidence/preflight.json
/var/lib/infra-assurance/evidence/preflight.md
```

## Validate locally

```bash
python3 -m pytest -q
```

See:

- `docs/milestone-1-first-slice.md` for the collector trust boundary;
- `docs/decisions/0002-compact-operational-context.md` for context compaction;
- `docs/decisions/0003-kubernetes-topology-projection.md` for relationship trust semantics;
- `docs/decisions/0004-task-scoped-planning-preflight.md` for planning trust semantics;
- `docs/milestone-1-ai-consumption-test.md` for the Milestone 1 acceptance test.
