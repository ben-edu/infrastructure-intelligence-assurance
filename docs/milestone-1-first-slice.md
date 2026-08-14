# Milestone 1 — Kubernetes Read-Only Inventory Slice

## Goal

Prove the complete Kubernetes evidence loop with a durable collector rather than a one-resource test harness.

## Included inventory

- Namespace
- Node
- Deployment
- StatefulSet
- DaemonSet
- Service
- Ingress
- PersistentVolumeClaim

The observer identity is cluster-wide but read-only. It has `get`, `list`, and `watch` only for these resource classes. The current snapshot collector uses `list`; `watch` is reserved for later incremental collection without changing the security model.

## Evidence behavior

Every resource becomes an observed `ObservationEnvelope`.

Every resource-kind collection also produces a collection envelope such as `DeploymentCollection/*`. A successful collection envelope records complete observation of that resource class at that time. A failed collection becomes `UNKNOWN + FAILED_TO_OBSERVE`; failure is never interpreted as absence.

Raw kubectl output is transient and is not persisted. Only normalized operational fields are written to evidence.

## Security boundary

The observer can read only:

- namespaces;
- nodes;
- services;
- PVCs;
- deployments;
- statefulsets;
- daemonsets;
- ingresses.

It cannot read Kubernetes Secrets and has no create/update/patch/delete verbs. Ingress TLS Secret names may appear because names are operational references; Secret payloads are never requested.

The external management-host collector uses a dedicated observer credential stored only in `/etc/infra-assurance/kubeconfig`, readable by root and the `infra-assurance` service account. The credential must never be committed, copied into evidence, or sent to AI context.

## Runtime on mgmt-automation

`bootstrap-observer.sh` installs:

- dedicated `infra-assurance` OS user;
- Kubernetes ServiceAccount and read-only RBAC;
- restricted observer kubeconfig;
- collector source under `/opt/infra-assurance`;
- hardened systemd oneshot service;
- five-minute systemd timer;
- evidence output under `/var/lib/infra-assurance/evidence`.

## Freshness

The current inventory TTL is five minutes. This is an initial policy for Kubernetes inventory and remains revisable when live collection and task requirements provide evidence for a better value.

## Intentionally deferred

- persistence/history database;
- drift engine;
- CMDB model;
- Prometheus/Loki/OpenTelemetry;
- backup assurance;
- Terraform/Ansible integration;
- mutating automation identities and approval workflows;
- platform deployment into Kubernetes.

## Acceptance check

The slice is accepted when the installed observer continuously produces current evidence/context from the real cluster, collection failures remain explicit, and the observer is verified unable to read Secrets or mutate workloads.
