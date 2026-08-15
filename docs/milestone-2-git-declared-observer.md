# Milestone 2 — Dedicated Git Declared-State Observer

## Goal

Turn the declared-vs-observed drift engine into an autonomous evidence loop for a real private infrastructure repository while preserving a strict boundary between Git declarations and live Kubernetes observation.

## Source

The first source is intentionally explicit:

```text
repository: github.com/ben-edu/api-cluster-infra
branch: main
cluster identity: k3s-main
```

Declared targets are renderer-aware rather than a recursive scan of every YAML file.

Direct manifests:

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

The observer does not discover arbitrary repositories, scan the operator's home directory, treat Kustomize bases/patches as final declarations, or interpret Helm values without a Helm renderer.

## Runtime flow

```text
GitHub private repository
  -> dedicated read-only deploy key
  -> verified SSH host identity
  -> shallow fetch into bare repository cache
  -> exact Git revision
  -> direct manifest reads + rendered Kustomize targets
  -> top-level kind safety gate
  -> local parser with no kubeconfig dependency
  -> narrow normalization
  -> declared ObservationEnvelope records
  -> source-status evidence
  -> declared-vs-observed drift
  -> compact change context
```

## Authentication

The bootstrap generates a dedicated Ed25519 keypair on the management host.

The private key is readable only by `infra-assurance`.

The public key is registered on `ben-edu/api-cluster-infra` as a deploy key without write access.

The runtime does not reuse `/home/ben/.ssh` or another personal credential.

## Parsing and rendering

Direct supported manifests are parsed with `kubectl patch --local` using an empty merge patch. The parser environment removes `KUBECONFIG` and `KUBERNETES_MASTER`; Git-plane normalization therefore does not depend on Kubernetes API discovery.

Kustomize targets are rendered with `kubectl kustomize` from a transient detached worktree at the exact fetched Git revision. The worktree is removed after rendering.

This matters for FastAPI because the dev and prod overlays assign different namespaces and image tags. Raw base and patch files are not independent declarations.

## Source observation semantics

The source status is independent from normalized records.

`COMPLETE` means the configured Git revision was fetched and every configured declaration target was rendered/read and normalized without an error.

`PARTIAL` means the revision was fetched but at least one configured target could not be rendered or normalized safely.

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

`Secret`, `ConfigMap`, and unmodeled kinds are gated before object parsing and skipped.

The normalized projection omits arbitrary metadata, annotations, environment values, ConfigMap payloads, Secret payloads, and connection strings.

Git source references and exact revisions remain as provenance.

## Drift behavior

The drift engine remains declaration-driven.

It compares each current declared identity with matching current observed evidence.

A failed Git source, partial source, stale declared envelope, failed Kubernetes collection, unsupported observed field, or cluster mismatch stays explicit and is not converted into a confident drift claim.

## Operational cadence

The existing Kubernetes systemd service invokes the Git observer before each five-minute Kubernetes collection.

Git refresh failure is fail-open for Kubernetes observation: Kubernetes evidence and history continue even if Git is temporarily unavailable.

The drift report records the declared-source state explicitly.

## Current limitations

The observer supports one explicitly configured Git source.

It supports direct manifests plus explicitly configured Kustomize targets. It does not yet render Helm values or normalize arbitrary CRDs.

Those are deliberate deferred capabilities, not silent assumptions.
