# ADR 0007 — Use a Dedicated Read-Only Git Observer for Declared Kubernetes Evidence

## Status

Accepted for Milestone 2 implementation.

## Context

Milestone 2 can evaluate normalized Git-declared evidence against live Kubernetes observations, but the management host needs an autonomous declared-state source.

The real private repository `ben-edu/api-cluster-infra` contains multiple declaration styles under `kubernetes/`:

- direct multi-document Kubernetes manifests;
- Kustomize bases and environment overlays;
- Helm values and example files that are not final Kubernetes declarations by themselves.

A broad recursive YAML scan is therefore unsafe semantically. It can treat Kustomize bases and patches as independent declarations, invent default namespaces, and produce false duplicate identities.

The platform must not:

- reuse a personal SSH key or administrator credential for unattended collection;
- clone private infrastructure repositories with a writable identity;
- serialize Kubernetes Secret payloads, secret-bearing environment values, arbitrary ConfigMap payloads, credentials, private keys, or complete sensitive connection strings;
- depend on live Kubernetes API discovery to parse the Git plane;
- treat bases, patches, Helm values, or examples as final declarations unless an explicit renderer says they are;
- treat a failed Git refresh as successful current declared evidence;
- merge declared and observed evidence into one record.

## Decision

Add a dedicated read-only Git declared-state observer on the management host with an explicit, renderer-aware source map.

### Identity

The bootstrap creates one Ed25519 SSH keypair dedicated to:

```text
github.com/ben-edu/api-cluster-infra
```

The public key is registered on that repository as a read-only deploy key.

The private key is owned by the `infra-assurance` service user with mode `0600`.

The runtime does not use the operator's personal SSH key.

### SSH host verification

The bootstrap obtains GitHub's currently published SSH host public keys from the GitHub metadata API over HTTPS and writes a dedicated `known_hosts` file.

The Git runtime uses:

```text
StrictHostKeyChecking=yes
IdentitiesOnly=yes
BatchMode=yes
```

A host-key verification failure becomes failed observation.

### Repository cache and rendering workspace

The observer uses a bare Git repository under:

```text
/var/lib/infra-assurance/git/repos/
```

Each refresh fetches the configured branch with depth 1 and records the exact commit revision.

For Kustomize only, the exact fetched revision is materialized into a short-lived detached Git worktree under the observer state directory. The worktree exists only while local rendering runs and is removed afterward. Raw repository files and rendered manifests are not persisted as evidence artifacts.

### Explicit source scope

The first source mapping is intentionally narrower than the repository's entire `kubernetes/` tree.

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

The FastAPI base and patch files are not ingested independently. They contribute only through the rendered dev or prod target.

Helm values, example Secrets, example registry credentials, and other unconfigured repository content are outside the declared scope for this slice.

### Local parsing and rendering boundary

Direct supported manifests are parsed locally with `kubectl patch --local` using an empty merge patch. The Git observer explicitly removes `KUBECONFIG` and `KUBERNETES_MASTER` from this parser environment so Git observation cannot silently depend on live cluster discovery.

Kustomize targets are rendered locally with `kubectl kustomize` from the transient worktree at the exact observed Git revision.

Before a direct or rendered Kubernetes document is parsed into normalized evidence, the observer identifies its top-level `kind`.

These kinds can become declared evidence:

```text
Namespace
Deployment
StatefulSet
DaemonSet
Service
Ingress
PersistentVolumeClaim
```

`Secret`, `ConfigMap`, and unsupported kinds are skipped before the object parser and never become declared evidence.

### Manifest safety boundary

Supported documents are projected immediately into a narrow allowlisted structure. Raw document contents are never written to the evidence store or logs.

The normalized fields include only data already modeled in observed evidence and needed for drift:

- Kubernetes identity;
- replicas;
- image references;
- selectors;
- Service type and ports;
- Ingress class, backend references, and TLS Secret names;
- PVC storage class, access modes, and requested storage.

Environment values, Secret payloads, ConfigMap payloads, credentials, connection strings, and arbitrary annotations are excluded.

### Provenance

Every normalized declared record retains:

- Git source ID;
- direct manifest path or Kustomize target;
- document index;
- collector version;
- exact Git revision;
- observation timestamps and expiry.

Evidence IDs are deterministic for a source revision, source reference, document, and Kubernetes identity.

### Source observation status

Git source status is independent from individual declared records:

```text
COMPLETE
PARTIAL
FAILED_TO_OBSERVE
```

`FAILED_TO_OBSERVE` includes authentication, host verification, network, fetch, and source-read failures. Its `revision` and `observed_at` are null even if an earlier step saw a candidate SHA.

`PARTIAL` means the Git revision was observed but at least one configured declaration target could not be rendered or normalized safely.

On a failed refresh the last successful declared bundle remains on disk for forensic continuity, but the source status prevents it from being promoted to current evidence.

### Drift semantics

The drift loader distinguishes:

```text
DECLARED_STATE_UNAVAILABLE
DECLARED_STATE_OBSERVATION_FAILED
DECLARED_STATE_ERRORS
EVALUATED
EVALUATED_PARTIAL
```

A declared record whose cluster identity does not match the current observed cluster is `UNKNOWN`, not drift.

Declared nested structures are compared as declared subsets where the Kubernetes API may add non-declared fields.

## Evidence from first live diagnostics

The first live source tests established two useful constraints:

1. The dedicated deploy key successfully authenticated to `ben-edu/api-cluster-infra` and resolved revision `5767e0a4c583d0a0e8c87b2e24c42eaeb822a3b4`.
2. The original `kubectl create --dry-run=client` parser normalized zero supported records without a kubeconfig but normalized records when a kubeconfig was supplied, proving an unwanted Git-to-live-cluster dependency.
3. A broad recursive scan then produced duplicate FastAPI identities from raw base/overlay/patch material, proving the need for explicit Kustomize targets.

The implementation was revised before acceptance rather than treating these diagnostics as acceptable partial operation.

## Security consequences

- Git access is read-only and separate from personal operator credentials.
- No private key is committed to Git or emitted into evidence, AI context, or reports.
- Raw sensitive Kubernetes documents are not persisted by the observer.
- Sensitive kinds are gated before object parsing.
- Local Git parsing does not use live Kubernetes credentials.
- A Git observation failure is visible instead of silently reusing old declarations.
- Kubernetes RBAC does not change.

## Operational consequences

The existing five-minute Kubernetes service performs a Git declared-state refresh before each Kubernetes observation.

A failed Git refresh does not block Kubernetes evidence collection.

The operator can inspect the source independently with:

```bash
iia-git-source status
iia-git-source public-key
iia-git-source sync
```

## Deferred

This ADR does not implement:

- writable Git operations;
- automatic repository changes;
- Helm template rendering;
- arbitrary CRD normalization;
- Terraform state ingestion;
- multiple Git repositories in one collector process;
- automatic deploy-key registration through a personal account.

Those capabilities require separate evidence and security decisions.
