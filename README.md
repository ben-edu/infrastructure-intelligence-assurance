# Infrastructure Intelligence & Assurance Platform

Evidence-first infrastructure context and assurance platform.

## Current status

Milestone 0 — Evidence Contract is complete.

Milestone 1 now implements a durable read-only Kubernetes inventory slice for:

- namespaces;
- nodes;
- deployments;
- statefulsets;
- daemonsets;
- services;
- ingresses;
- persistent volume claims.

Each collection is normalized into `ObservationEnvelope` evidence with provenance, expiry, explicit collection failures, and compact AI context. Raw Secret values are never collected and the observer RBAC has no Secret access or mutating verbs.

## Runtime model

The initial collector runs on the management host, not inside Kubernetes:

```text
Kubernetes API
  -> dedicated read-only observer identity
  -> Kubernetes inventory collector
  -> normalized evidence
  -> freshness evaluation
  -> context.json
```

A systemd timer refreshes the snapshot every five minutes. The bootstrap creates a dedicated OS service account, restricted kubeconfig, output directory, and Kubernetes RBAC identity.

## Install on the management host

From the Milestone 1 branch/repository checkout:

```bash
sudo CLUSTER_ID=k3s-main ./scripts/bootstrap-observer.sh
```

The bootstrap verifies that the observer can read required inventory and cannot read Secrets or create Deployments.

Outputs:

```text
/var/lib/infra-assurance/evidence/kubernetes.json
/var/lib/infra-assurance/evidence/context.json
```

## Validate locally

```bash
PYTHONPATH=src pytest
```

See `docs/milestone-1-first-slice.md` for scope, trust boundaries, credential rationale, and deferred items.
