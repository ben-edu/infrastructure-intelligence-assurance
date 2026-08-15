# Milestone 2 — Dedicated Git Declared-State Observer

## Goal

Turn the existing declared-vs-observed drift engine into an autonomous evidence loop for a real private infrastructure repository.

## Source

The first source is intentionally explicit:

```text
repository: github.com/ben-edu/api-cluster-infra
branch: main
cluster identity: k3s-main
```

Direct manifest targets:

```text
kubernetes/bookstack/01-pvc.yaml
kubernetes/bookstack/02-mariadb.yaml
kubernetes/bookstack/03-bookstack.yaml
kubernetes/validation/nginx/nginx-validation.yaml
```

Kustomize targets:

```text
kubernetes/fastapi-platform/overlays/dev
kubernetes/fastapi-platform/overlays/prod
```

The observer does not discover arbitrary repositories, scan the operator's home directory, or recursively treat every YAML file as an independent declaration.

## Runtime flow

```text
GitHub private repository
  -> dedicated read-only deploy key
  -> verified SSH host identity
  -> shallow fetch into bare repository cache
  -> explicit direct-manifest targets
  -> explicit Kustomize render targets at exact revision
  -> top-level kind safety gate
  -> local parse of supported kinds only
  -> narrow normalization
  -> declared ObservationEnvelope records
  -> source-status evidence
  -> declared-vs-observed drift
  -> compact change context
```

## Authentication

The bootstrap generates a dedicated Ed25519 keypair on the management host.

The private key is readable only by `infra-assurance`.

The public key is registered on the source repository as a deploy key without write access.

The runtime does not reuse `/home/ben/.ssh` or another personal credential.

## Source observation semantics

The source status is independent from normalized records.

`COMPLETE` means the configured Git revision was fetched and all supported configured declarations were normalized.

`PARTIAL` means the revision was fetched but at least one supported configured document or render target could not be normalized safely.

`FAILED_TO_OBSERVE` means the latest source attempt failed before a trustworthy current declared view could be produced.

A failed refresh leaves the prior bundle on disk but blocks it from being treated as current.

## Safe normalization

Only the following kinds can become declared evidence:

```text
Namespace
Deployment
StatefulSet
DaemonSet
Service
Ingress
PersistentVolumeClaim
```

Sensitive and unmodeled documents are skipped.

The normalized data projection deliberately omits arbitrary metadata, annotations, environment values, ConfigMap payloads, Secret payloads, and connection strings.

Git paths and exact revisions remain as provenance.

Direct manifests are parsed locally. FastAPI dev/prod are rendered from configured Kustomize targets at the exact fetched revision using a transient detached worktree. The worktree is removed after rendering and is not evidence storage.

Helm values and example directories remain outside this declared-state contract.

## Drift behavior

The drift engine remains declaration-driven.

It compares each current declared identity with matching current observed evidence.

A failed Git source, stale declared envelope, failed Kubernetes collection, unsupported observed field, or cluster mismatch produces unknown state rather than invented drift.

A real field mismatch remains drift and is not repaired automatically.

## Operational cadence

The existing Kubernetes systemd service invokes the Git observer before each five-minute Kubernetes collection.

Git refresh failure is fail-open for Kubernetes observation: Kubernetes evidence and history continue even if Git is temporarily unavailable.

The drift report still records the declared source failure explicitly.

## Live validation

The management-host acceptance passed on 2026-08-15.

The final local test run reported:

```text
64 passed in 0.71s
```

A Git sync as `infra-assurance`, with `KUBECONFIG` explicitly removed, reported:

```text
status: COMPLETE
revision: 5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4
normalized_records: 27
skipped_documents: 3
errors: []
```

The transient Kustomize worktree check left no residual paths.

The subsequent drift evaluation reported:

```text
declared_records: 27
in_sync: 26
drift: 1
unknown: 0
loader_errors: 0
```

The single drift is evidence-backed: the Git revision declares `k3s-master.soria-academie.fr` for `Ingress/validation/nginx-validation`, while observed Kubernetes evidence reports `k3s-master.behnam.fr`.

No mutation is attempted. The platform remains read-only.

## Current limitations

The observer currently supports one explicitly configured Git source.

It supports direct manifests and explicit Kustomize targets, but not Helm template rendering or arbitrary templates.

It does not normalize CRDs.

Those are deliberate deferred capabilities, not silent assumptions.
